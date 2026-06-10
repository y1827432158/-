import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
VENV_DIR = PROJECT_ROOT / ".venv"
STAMP_FILE = VENV_DIR / ".requirements.sha256"
TRAIN_SCRIPT = PROJECT_ROOT / "train.py"
REQUIRED_MODULES = [
    "torch",
    "cv2",
    "pandas",
    "numpy",
    "mediapipe",
    "matplotlib",
    "sklearn",
    "seaborn",
    "tqdm",
]
MIN_PYTHON_VERSION = (3, 10)
MAX_PYTHON_VERSION = (3, 13)
PREFERRED_PYTHON_VERSIONS = ("3.13", "3.12", "3.11", "3.10")
SUPPORTED_PYTHON_LABELS = ("3.10", "3.11", "3.12", "3.13")
DEFAULT_PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
ENV_KEYS_TO_CLEAR_FOR_PIP = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
    "git_http_proxy",
    "git_https_proxy",
    "PIP_NO_INDEX",
    "pip_no_index",
    "PIP_CONFIG_FILE",
]


def log(message):
    print(f"[连续手语识别模型训练] {message}")


def format_command(parts):
    return " ".join(f'"{part}"' if " " in str(part) else str(part) for part in parts)


def format_python_version(version):
    if version is None:
        return "unknown"
    return f"{version[0]}.{version[1]}"


def supported_python_text():
    versions = [f"Python {version}" for version in SUPPORTED_PYTHON_LABELS]
    return "、".join(versions)


def build_pip_install_env():
    env = os.environ.copy()
    cleared = [key for key in ENV_KEYS_TO_CLEAR_FOR_PIP if key in env]
    for key in ENV_KEYS_TO_CLEAR_FOR_PIP:
        env.pop(key, None)

    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PIP_NO_INPUT", "1")
    env.setdefault("PIP_INDEX_URL", os.environ.get("SL_PIP_INDEX_URL", DEFAULT_PIP_INDEX_URL))
    return env, cleared


def run_command(parts, *, cwd=PROJECT_ROOT, env=None, dry_run=False):
    command = [str(part) for part in parts]
    log(f"执行命令: {format_command(command)}")
    if dry_run:
        return None
    return subprocess.run(command, cwd=str(cwd), env=env, check=True)


def command_exists(command):
    command = str(command)
    path = Path(command)
    return path.exists() if path.is_absolute() else shutil.which(command) is not None


def venv_python_path():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def probe_python_version(command_parts):
    command = [str(part) for part in command_parts]
    try:
        result = subprocess.run(
            command + ["-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    version_text = (result.stdout or "").strip()
    try:
        major, minor = version_text.split(".")
        return int(major), int(minor)
    except ValueError:
        return None


def is_supported_python_version(version):
    return version is not None and MIN_PYTHON_VERSION <= version <= MAX_PYTHON_VERSION


def python_version_skip_reason(version):
    if version is None:
        return "无法识别版本"
    if version < MIN_PYTHON_VERSION:
        return "版本过低"
    if version > MAX_PYTHON_VERSION:
        return "当前暂未验证 3.14 及以上"
    return "不在支持范围内"


def requirements_digest():
    return hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()


def dependencies_installed(python_executable):
    code = f"""
import importlib.util
import sys
modules = {REQUIRED_MODULES!r}
missing = [name for name in modules if importlib.util.find_spec(name) is None]
print(",".join(missing))
sys.exit(0 if not missing else 1)
""".strip()
    result = subprocess.run(
        [str(python_executable), "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True

    missing = (result.stdout or result.stderr).strip()
    if missing:
        log(f"发现缺失依赖: {missing}")
    return False


def detect_base_python():
    candidates = []
    env_python = os.environ.get("SL_RUNTIME_PYTHON", "").strip()
    if env_python:
        candidates.append([env_python])
    if os.name == "nt":
        candidates.extend([["py", f"-{version}"] for version in PREFERRED_PYTHON_VERSIONS])
    if sys.executable and Path(sys.executable).exists():
        candidates.append([sys.executable])
    candidates.extend([["python"], ["python3"]])
    if os.name == "nt":
        candidates.append(["py", "-3"])

    for candidate in candidates:
        if command_exists(candidate[0]):
            version = probe_python_version(candidate)
            if is_supported_python_version(version):
                return candidate
            if version is not None:
                log(
                    f"跳过不支持的 Python 版本: {format_command(candidate)} "
                    f"({format_python_version(version)}，{python_version_skip_reason(version)})"
                )

    raise RuntimeError(
        f"没有找到可用的 Python 解释器，请先安装 {supported_python_text()}。"
    )


def find_ready_runtime():
    candidate_paths = []
    env_python = os.environ.get("SL_RUNTIME_PYTHON", "").strip()
    if env_python:
        candidate_paths.append(Path(env_python))
    venv_python = venv_python_path()
    if venv_python.exists():
        candidate_paths.append(venv_python)
    if sys.executable and Path(sys.executable).exists():
        candidate_paths.append(Path(sys.executable))

    for candidate in candidate_paths:
        if (
            candidate.exists()
            and is_supported_python_version(probe_python_version([candidate]))
            and dependencies_installed(candidate)
        ):
            return candidate
    return None


def ensure_venv(base_python, *, dry_run=False):
    python_path = venv_python_path()
    if python_path.exists():
        version = probe_python_version([python_path])
        if is_supported_python_version(version):
            log(f"复用虚拟环境: {VENV_DIR}")
            return python_path

        log("检测到旧虚拟环境版本不受支持，将重新创建 .venv")
        if not dry_run:
            shutil.rmtree(VENV_DIR, ignore_errors=True)

    log("未检测到虚拟环境，开始创建 .venv")
    run_command([*base_python, "-m", "venv", str(VENV_DIR)], dry_run=dry_run)
    return python_path


def ensure_dependencies(venv_python, *, dry_run=False, force_install=False):
    digest = requirements_digest()
    installed_digest = ""
    if STAMP_FILE.exists():
        installed_digest = STAMP_FILE.read_text(encoding="utf-8").strip()

    if (
        not dry_run
        and not force_install
        and installed_digest == digest
        and dependencies_installed(venv_python)
    ):
        log("依赖已经是最新，跳过安装")
        return

    pip_env, cleared = build_pip_install_env()
    if cleared:
        log(f"安装依赖时自动忽略本机代理/索引干扰项: {', '.join(cleared)}")
    log(f"依赖安装源: {pip_env['PIP_INDEX_URL']}")

    run_command(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        env=pip_env,
        dry_run=dry_run,
    )
    run_command(
        [venv_python, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
        env=pip_env,
        dry_run=dry_run,
    )

    if not dry_run:
        STAMP_FILE.write_text(digest, encoding="utf-8")
        log("依赖安装完成")


def validate_training_inputs():
    dataset_dir = PROJECT_ROOT / "dataset"
    corpus_file = dataset_dir / "corpus.txt"

    if not dataset_dir.exists():
        raise FileNotFoundError(f"未找到数据集目录: {dataset_dir}")
    if not corpus_file.exists():
        raise FileNotFoundError(f"未找到词汇文件: {corpus_file}")
    if not TRAIN_SCRIPT.exists():
        raise FileNotFoundError(f"未找到训练脚本: {TRAIN_SCRIPT}")


def parse_args():
    parser = argparse.ArgumentParser(description="连续手语识别模型训练启动器")
    parser.add_argument("--dry-run", action="store_true", help="只打印步骤，不实际执行")
    parser.add_argument("--skip-install", action="store_true", help="跳过依赖安装")
    parser.add_argument("--force-install", action="store_true", help="强制重新安装依赖")
    parser.add_argument(
        "--show-train-help",
        action="store_true",
        help="显示 train.py 的参数帮助",
    )
    return parser.parse_known_args()


def main():
    args, train_args = parse_args()
    validate_training_inputs()

    if args.show_train_help:
        train_args = ["--help"]
    elif train_args and train_args[0] == "--model_type":
        train_args = train_args[2:]

    log(f"项目目录: {PROJECT_ROOT}")
    log(f"推荐 Python 版本: {supported_python_text()}（当前已验证到 3.13）")
    log(f"训练参数: {' '.join(train_args) if train_args else '默认 CNN-LSTM 配置'}")

    ready_runtime = find_ready_runtime()
    if ready_runtime is not None and not args.force_install:
        runtime_python = str(ready_runtime)
        log(f"使用现成运行环境: {ready_runtime}")
    else:
        base_python = detect_base_python()
        log(f"引导 Python: {format_command(base_python)}")
        runtime_python = str(ensure_venv(base_python, dry_run=args.dry_run))
        log(f"虚拟环境 Python: {runtime_python}")

        if not args.skip_install:
            ensure_dependencies(
                runtime_python,
                dry_run=args.dry_run,
                force_install=args.force_install,
            )

    run_command([runtime_python, str(TRAIN_SCRIPT), *train_args], dry_run=args.dry_run)

    log("训练流程结束")
    log("训练完成后，模型权重会输出到 models 目录。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        log(f"命令执行失败，退出码: {exc.returncode}")
        raise SystemExit(exc.returncode)
    except Exception as exc:
        log(f"启动失败: {exc}")
        raise SystemExit(1)

