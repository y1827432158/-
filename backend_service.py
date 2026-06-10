import json
import os
import random
import shutil
import socket
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug import serving as werkzeug_serving
from werkzeug.utils import secure_filename


PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_TYPE = "cnn_lstm"
APP_STORAGE_DIR = PROJECT_ROOT / "app_storage"
CONTRIBUTION_DIR = APP_STORAGE_DIR / "contributions"
USERS_FILE = APP_STORAGE_DIR / "users.json"
USAGE_LOGS_FILE = APP_STORAGE_DIR / "usage_logs.json"
CONTRIBUTIONS_FILE = APP_STORAGE_DIR / "contributions.json"
DATASET_DIR = PROJECT_ROOT / "dataset"
CORPUS_FILE = DATASET_DIR / "corpus.txt"
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".webm"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from inference.predictor import HandSignPredictor

    PREDICTOR_AVAILABLE = True
    PREDICTOR_IMPORT_ERROR = ""
except ImportError as exc:
    HandSignPredictor = None  # type: ignore[assignment]
    PREDICTOR_AVAILABLE = False
    PREDICTOR_IMPORT_ERROR = str(exc)


app = Flask(__name__)
CORS(app)

global_predictor = None


def suppress_dev_server_warning():
    def quiet_log_startup(self):
        messages = []

        if self.address_family == werkzeug_serving.af_unix:
            messages.append(f" * Running on {self.host}")
        else:
            scheme = "http" if self.ssl_context is None else "https"
            display_hostname = self.host

            if self.host in {"0.0.0.0", "::"}:
                messages.append(f" * Running on all addresses ({self.host})")

                if self.host == "0.0.0.0":
                    localhost = "127.0.0.1"
                    display_hostname = werkzeug_serving.get_interface_ip(socket.AF_INET)
                else:
                    localhost = "[::1]"
                    display_hostname = werkzeug_serving.get_interface_ip(socket.AF_INET6)

                messages.append(f" * Running on {scheme}://{localhost}:{self.port}")

            if ":" in display_hostname:
                display_hostname = f"[{display_hostname}]"

            messages.append(f" * Running on {scheme}://{display_hostname}:{self.port}")

        werkzeug_serving._log("info", "\n".join(messages))

    werkzeug_serving.BaseWSGIServer.log_startup = quiet_log_startup


def iso_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_storage():
    APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    CONTRIBUTION_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        write_json(
            USERS_FILE,
            [
                {
                    "id": 1,
                    "username": "admin",
                    "password": "admin123",
                    "role": "admin",
                    "display_name": "系统管理员",
                    "created_at": iso_now(),
                },
                {
                    "id": 2,
                    "username": "user1",
                    "password": "user123",
                    "role": "user",
                    "display_name": "默认用户",
                    "created_at": iso_now(),
                },
            ],
        )

    if not USAGE_LOGS_FILE.exists():
        write_json(USAGE_LOGS_FILE, [])

    if not CONTRIBUTIONS_FILE.exists():
        write_json(CONTRIBUTIONS_FILE, [])


def read_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def next_id(items):
    if not items:
        return 1
    return max(int(item.get("id", 0)) for item in items) + 1


def rename_user_references(old_username, new_username):
    if not old_username or old_username == new_username:
        return

    logs = read_json(USAGE_LOGS_FILE, [])
    changed_logs = False
    for item in logs:
        if item.get("username") == old_username:
            item["username"] = new_username
            changed_logs = True
    if changed_logs:
        write_json(USAGE_LOGS_FILE, logs)

    contributions = read_json(CONTRIBUTIONS_FILE, [])
    changed_contributions = False
    for item in contributions:
        if item.get("username") == old_username:
            item["username"] = new_username
            changed_contributions = True
    if changed_contributions:
        write_json(CONTRIBUTIONS_FILE, contributions)

    old_dir = CONTRIBUTION_DIR / old_username
    new_dir = CONTRIBUTION_DIR / new_username
    if old_dir.exists() and old_dir.is_dir():
        new_dir.mkdir(parents=True, exist_ok=True)
        for child in old_dir.iterdir():
            target = new_dir / child.name
            if target.exists():
                target = new_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{child.name}"
            shutil.move(str(child), str(target))
        try:
            old_dir.rmdir()
        except OSError:
            pass


def predictor_impl_name(predictor):
    predictor_module = getattr(predictor.__class__, "__module__", "")
    if PREDICTOR_AVAILABLE and predictor_module.startswith("inference."):
        return "real", predictor_module
    return "mock", predictor_module


def build_model_path(model_type):
    return MODELS_DIR / f"best_{model_type}_model.pth"


def load_corpus_dict():
    corpus = {}
    if not CORPUS_FILE.exists():
        return corpus

    with CORPUS_FILE.open("r", encoding="utf-8", errors="ignore") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            index, text = parts
            corpus[index.zfill(6)] = text.strip()
    return corpus


def learning_label_text(label, corpus_dict):
    normalized = str(label).zfill(6)
    return corpus_dict.get(normalized, f"手语类别 {label}")


def build_learning_material(label, video_name, corpus_dict):
    label_text = learning_label_text(label, corpus_dict)
    return {
        "id": str(label),
        "name": label_text,
        "label": str(label),
        "description": f"类别 {label} 的学习示例视频，标签为“{label_text}”",
        "video_name": video_name,
        "video_url": f"/api/learning-video/{label}/{video_name}",
    }


def list_learning_videos(label):
    class_dir = DATASET_DIR / str(label)
    if not class_dir.exists() or not class_dir.is_dir():
        return []
    return [
        file
        for file in sorted(class_dir.iterdir())
        if file.is_file() and file.suffix.lower() in VIDEO_SUFFIXES
    ]


def build_learning_video_entries(label):
    return [
        {
            "name": video.name,
            "url": f"/api/learning-video/{label}/{video.name}",
        }
        for video in list_learning_videos(label)
    ]


def list_learning_materials(limit=None):
    materials = []
    if not DATASET_DIR.exists():
        return materials
    corpus_dict = load_corpus_dict()
    class_dirs = [path for path in DATASET_DIR.iterdir() if path.is_dir()]

    def sort_key(item):
        try:
            return int(item.name)
        except ValueError:
            return item.name

    for class_dir in sorted(class_dirs, key=sort_key):
        video = next((file for file in sorted(class_dir.iterdir()) if file.is_file() and file.suffix.lower() in VIDEO_SUFFIXES), None)
        if not video:
            continue
        materials.append(build_learning_material(class_dir.name, video.name, corpus_dict))
        if limit is not None and len(materials) >= limit:
            break
    return materials


def sanitize_user(user):
    return {
        key: value
        for key, value in user.items()
        if key != "password"
    }


def get_actor():
    return {
        "username": request.headers.get("X-User-Name", "anonymous"),
        "role": request.headers.get("X-User-Role", "guest"),
    }


def require_admin():
    actor = get_actor()
    if actor["role"] != "admin":
        return None, (
            jsonify({"success": False, "message": "Admin permission required."}),
            403,
        )
    return actor, None


def append_usage_log(username, role, action, content, source, file_name="--", confidence="--"):
    logs = read_json(USAGE_LOGS_FILE, [])
    logs.insert(
        0,
        {
            "id": next_id(logs),
            "username": username,
            "role": role,
            "action": action,
            "content": content,
            "source": source,
            "file_name": file_name,
            "confidence": confidence,
            "timestamp": iso_now(),
        },
    )
    write_json(USAGE_LOGS_FILE, logs[:500])


ensure_storage()


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "success": True,
            "service": "sign-language-backend",
            "status": "running",
            "predictor_initialized": global_predictor is not None,
        }
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "success": True,
            "service": "sign-language-backend",
            "predictor_available": PREDICTOR_AVAILABLE,
            "predictor_initialized": global_predictor is not None,
            "import_error": PREDICTOR_IMPORT_ERROR,
        }
    )


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or ""

    users = read_json(USERS_FILE, [])
    matched_user = next((item for item in users if item["username"] == username), None)
    if not matched_user or matched_user["role"] != role:
        return jsonify({"success": False, "message": "没有此用户或者角色选择错误"}), 401
    if matched_user["password"] != password:
        return jsonify({"success": False, "message": "用户名或者密码不正确"}), 401

    append_usage_log(matched_user["username"], matched_user["role"], "login", "User logged into the system", "system")
    return jsonify({"success": True, "user": sanitize_user(matched_user)})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or username).strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    users = read_json(USERS_FILE, [])
    if any(item["username"] == username for item in users):
        return jsonify({"success": False, "message": "该用户名已存在"}), 400

    new_user = {
        "id": next_id(users),
        "username": username,
        "password": password,
        "role": "user",
        "display_name": display_name,
        "created_at": iso_now(),
    }
    users.append(new_user)
    write_json(USERS_FILE, users)
    append_usage_log(new_user["username"], new_user["role"], "register", "User registered a new account", "system")
    return jsonify({"success": True, "user": sanitize_user(new_user)})


@app.route("/api/learning-materials", methods=["GET"])
def learning_materials():
    materials = list_learning_materials()
    return jsonify({"success": True, "materials": materials})


@app.route("/api/learning-materials/<label>/videos", methods=["GET"])
def learning_material_videos(label):
    videos = build_learning_video_entries(label)
    if not videos:
        return jsonify({"success": False, "message": "Learning video not found."}), 404
    return jsonify({"success": True, "videos": videos})


@app.route("/api/learning-materials/<label>/random", methods=["GET"])
def random_learning_material(label):
    current_video = (request.args.get("current_video") or "").strip()
    videos = list_learning_videos(label)
    if not videos:
        return jsonify({"success": False, "message": "Learning video not found."}), 404

    selectable = [video for video in videos if video.name != current_video]
    chosen_pool = selectable or videos
    chosen = random.choice(chosen_pool)
    corpus_dict = load_corpus_dict()
    material = build_learning_material(label, chosen.name, corpus_dict)
    material["changed"] = bool(selectable)
    return jsonify({"success": True, "material": material})


@app.route("/api/learning-video/<label>/<filename>", methods=["GET"])
def learning_video(label, filename):
    target = DATASET_DIR / label / filename
    if not target.exists() or not target.is_file():
        return jsonify({"success": False, "message": "Learning video not found."}), 404
    return send_file(target)


@app.route("/api/users", methods=["GET"])
def list_users():
    _, error = require_admin()
    if error:
        return error
    users = read_json(USERS_FILE, [])
    return jsonify({"success": True, "users": [sanitize_user(user) for user in users]})


@app.route("/api/users", methods=["POST"])
def create_user():
    actor, error = require_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "user"
    display_name = (data.get("display_name") or username).strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    users = read_json(USERS_FILE, [])
    if any(item["username"] == username for item in users):
        return jsonify({"success": False, "message": "该用户名已存在"}), 400

    new_user = {
        "id": next_id(users),
        "username": username,
        "password": password,
        "role": role,
        "display_name": display_name,
        "created_at": iso_now(),
    }
    users.append(new_user)
    write_json(USERS_FILE, users)
    append_usage_log(actor["username"], actor["role"], "admin_create_user", f"Created user {username}", "admin")
    return jsonify({"success": True, "user": sanitize_user(new_user)})


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    actor, error = require_admin()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    users = read_json(USERS_FILE, [])
    user = next((item for item in users if int(item["id"]) == user_id), None)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    new_username = (data.get("username") or user["username"]).strip()
    if any(item["username"] == new_username and int(item["id"]) != user_id for item in users):
        return jsonify({"success": False, "message": "该用户名已存在"}), 400

    old_username = user["username"]
    user["username"] = new_username
    user["display_name"] = (data.get("display_name") or user.get("display_name") or new_username).strip()
    user["role"] = data.get("role") or user["role"]
    if data.get("password"):
        user["password"] = data["password"]

    write_json(USERS_FILE, users)
    rename_user_references(old_username, new_username)
    append_usage_log(actor["username"], actor["role"], "admin_update_user", f"Updated user {new_username}", "admin")
    return jsonify({"success": True, "user": sanitize_user(user)})


@app.route("/api/account", methods=["PUT"])
def update_account():
    actor = get_actor()
    if actor["role"] not in {"user", "admin"}:
        return jsonify({"success": False, "message": "Please login first."}), 401

    data = request.get_json(silent=True) or {}
    users = read_json(USERS_FILE, [])
    user = next((item for item in users if item["username"] == actor["username"]), None)
    if not user:
        return jsonify({"success": False, "message": "Current user not found."}), 404

    current_password = data.get("current_password") or ""
    if user.get("password") != current_password:
        return jsonify({"success": False, "message": "当前密码不正确"}), 400

    new_username = (data.get("username") or user["username"]).strip()
    display_name = (data.get("display_name") or user.get("display_name") or new_username).strip()
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if new_password and new_password != confirm_password:
        return jsonify({"success": False, "message": "新密码与确认新密码不一致"}), 400

    if not new_username:
        return jsonify({"success": False, "message": "用户名不能为空。"}), 400

    if any(item["username"] == new_username and int(item["id"]) != int(user["id"]) for item in users):
        return jsonify({"success": False, "message": "该用户名已存在"}), 400

    old_username = user["username"]
    user["username"] = new_username
    user["display_name"] = display_name
    if new_password:
        user["password"] = new_password

    write_json(USERS_FILE, users)
    rename_user_references(old_username, new_username)
    append_usage_log(new_username, user["role"], "update_account", "用户更新了账号信息", "system")
    return jsonify({"success": True, "user": sanitize_user(user)})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    actor, error = require_admin()
    if error:
        return error

    users = read_json(USERS_FILE, [])
    user = next((item for item in users if int(item["id"]) == user_id), None)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    if user["username"] == "admin":
        return jsonify({"success": False, "message": "Default admin cannot be deleted."}), 400

    filtered = [item for item in users if int(item["id"]) != user_id]
    write_json(USERS_FILE, filtered)
    append_usage_log(actor["username"], actor["role"], "admin_delete_user", f"Deleted user {user['username']}", "admin")
    return jsonify({"success": True})


@app.route("/api/usage-logs", methods=["GET"])
def usage_logs():
    _, error = require_admin()
    if error:
        return error
    logs = read_json(USAGE_LOGS_FILE, [])
    return jsonify({"success": True, "logs": logs})


@app.route("/api/my-usage", methods=["GET"])
def my_usage():
    actor = get_actor()
    if actor["role"] not in {"user", "admin"}:
        return jsonify({"success": False, "message": "Please log in first."}), 401
    logs = read_json(USAGE_LOGS_FILE, [])
    own_logs = [item for item in logs if item["username"] == actor["username"]]
    return jsonify({"success": True, "logs": own_logs})


@app.route("/api/contributions", methods=["GET"])
def list_contributions():
    actor = get_actor()
    contributions = read_json(CONTRIBUTIONS_FILE, [])
    if actor["role"] == "admin":
        return jsonify({"success": True, "contributions": contributions})
    own = [item for item in contributions if item["username"] == actor["username"]]
    return jsonify({"success": True, "contributions": own})


@app.route("/api/contributions", methods=["POST"])
def upload_contribution():
    actor = get_actor()
    if actor["role"] not in {"user", "admin"}:
        return jsonify({"success": False, "message": "请先登录后再上传贡献视频。"}), 401
    if "video" not in request.files:
        return jsonify({"success": False, "message": "请先选择或录制贡献视频。"}), 400

    note = (request.form.get("note") or "").strip()
    if not note:
        return jsonify({"success": False, "message": "请填写这段手语视频表达的意思。"}), 400
    video_file = request.files["video"]
    safe_name = secure_filename(video_file.filename or "contribution.mp4")
    save_dir = CONTRIBUTION_DIR / actor["username"]
    save_dir.mkdir(parents=True, exist_ok=True)

    stamped_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    save_path = save_dir / stamped_name
    video_file.save(save_path)

    contributions = read_json(CONTRIBUTIONS_FILE, [])
    record = {
        "id": next_id(contributions),
        "username": actor["username"],
        "role": actor["role"],
        "file_name": stamped_name,
        "original_name": video_file.filename or safe_name,
        "note": note,
        "saved_path": str(save_path),
        "timestamp": iso_now(),
    }
    contributions.insert(0, record)
    write_json(CONTRIBUTIONS_FILE, contributions[:500])
    append_usage_log(actor["username"], actor["role"], "contribute_video", f"贡献视频含义：{note}", "contribution", stamped_name)
    return jsonify({"success": True, "contribution": record})


@app.route("/api/init-predictor", methods=["POST"])
def init_predictor_api():
    global global_predictor

    if not PREDICTOR_AVAILABLE or HandSignPredictor is None:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Predictor import failed. Check dependencies and restart the backend.",
                    "predictor_available": False,
                    "import_error": PREDICTOR_IMPORT_ERROR,
                }
            ),
            500,
        )

    try:
        data = request.get_json(silent=True) or {}
        requested_model_type = data.get("model_type", DEFAULT_MODEL_TYPE)
        model_type = DEFAULT_MODEL_TYPE
        model_path = build_model_path(model_type)

        if not model_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Model file not found: {model_path}",
                        "model_type": model_type,
                        "models_dir": str(MODELS_DIR),
                        "requested_model_type": requested_model_type,
                    }
                ),
                500,
            )

        global_predictor = HandSignPredictor(model_type=model_type, model_path=str(model_path))
        predictor_impl, predictor_module = predictor_impl_name(global_predictor)

        return jsonify(
            {
                "success": True,
                "message": f"Predictor initialized successfully with model {model_type}.",
                "model_type": model_type,
                "requested_model_type": requested_model_type,
                "predictor_available": True,
                "predictor_impl": predictor_impl,
                "predictor_class": getattr(global_predictor.__class__, "__name__", "HandSignPredictor"),
                "predictor_module": predictor_module,
                "default_model_path": str(model_path.resolve()),
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": f"Predictor initialization failed: {exc}"}), 500


@app.route("/api/predict-video", methods=["POST"])
def predict_video_api():
    global global_predictor

    if global_predictor is None:
        return jsonify({"success": False, "message": "Predictor is not initialized yet."}), 400
    if "video" not in request.files:
        return jsonify({"success": False, "message": "No video file was uploaded."}), 400

    actor = get_actor()
    video_file = request.files["video"]
    temp_path = None

    try:
        suffix = Path(video_file.filename or "upload.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            video_file.save(temp_path)

        result, confidence = global_predictor.predict(temp_path, return_prob=True)
        predictor_impl, predictor_module = predictor_impl_name(global_predictor)

        if predictor_impl != "real":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Current predictor implementation is unavailable. Check dependencies and model loading.",
                        "predictor_available": PREDICTOR_AVAILABLE,
                        "predictor_impl": predictor_impl,
                        "predictor_module": predictor_module,
                    }
                ),
                500,
            )

        confidence_value = float(confidence)
        append_usage_log(
            actor["username"],
            actor["role"],
            "predict_video",
            result,
            "video_prediction",
            video_file.filename or "--",
            f"{confidence_value:.4f}",
        )

        return jsonify(
            {
                "success": True,
                "result": result,
                "confidence": confidence_value,
                "model_type": getattr(global_predictor, "model_type", None),
                "predictor_impl": predictor_impl,
                "predictor_module": predictor_module,
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": f"Prediction failed: {exc}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.route("/api/predict-webcam", methods=["POST"])
def predict_webcam_api():
    global global_predictor

    if global_predictor is None:
        return jsonify({"success": False, "message": "Predictor is not initialized yet."}), 400

    actor = get_actor()
    try:
        data = request.get_json(silent=True) or {}
        duration = int(data.get("duration", 3))
        result, confidence = global_predictor.predict_webcam(duration=duration, return_prob=True)
        predictor_impl, predictor_module = predictor_impl_name(global_predictor)

        if predictor_impl != "real":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Current predictor implementation is unavailable. Check dependencies and model loading.",
                        "predictor_available": PREDICTOR_AVAILABLE,
                        "predictor_impl": predictor_impl,
                        "predictor_module": predictor_module,
                    }
                ),
                500,
            )

        confidence_value = float(confidence)
        append_usage_log(
            actor["username"],
            actor["role"],
            "predict_webcam",
            result,
            "webcam_prediction",
            "--",
            f"{confidence_value:.4f}",
        )

        return jsonify(
            {
                "success": True,
                "result": result,
                "confidence": confidence_value,
                "model_type": getattr(global_predictor, "model_type", None),
                "predictor_impl": predictor_impl,
                "predictor_module": predictor_module,
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": f"Webcam prediction failed: {exc}"}), 500


if __name__ == "__main__":
    print("[backend_service] Flask backend service starting on http://127.0.0.1:5001")
    suppress_dev_server_warning()
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
