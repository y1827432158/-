from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


HOST = "127.0.0.1"
PORT = 5173
ROOT = Path(__file__).resolve().parent


def main():
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    url = f"http://{HOST}:{PORT}/index.html"
    print(f"[shouyusystem] 前端已启动: {url}")
    print("[shouyusystem] 请保持此窗口开启。")
    webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
