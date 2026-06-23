"""Milodi 桌面应用入口：后台启动 Web 服务并打开浏览器。"""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STARTUP_TIMEOUT_S = 300


def _mac_notify(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], check=False)


def _mac_alert(title: str, message: str) -> None:
    if sys.platform != "darwin":
        print(f"{title}: {message}", file=sys.stderr)
        return
    safe = message.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        f'display dialog "{safe}" with title "{title}" '
        'buttons {"OK"} default button "OK" with icon caution'
    )
    subprocess.run(["osascript", "-e", script], check=False)


def _server_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        return exc.code == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _wait_for_server(url: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _server_ready(url):
            return True
        time.sleep(0.25)
    return False


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    from milodi.web.app import serve

    host = DEFAULT_HOST
    port = DEFAULT_PORT
    url = f"http://{host}:{port}/"

    if _server_ready(url):
        webbrowser.open(url)
        return 0

    if _port_open(host, port):
        _mac_alert("Milodi", f"端口 {port} 已被占用，且不是 Milodi 服务。请关闭占用程序后重试。")
        return 1

    _mac_notify("Milodi", "正在启动，首次打开可能需要 1–3 分钟…")

    stop = threading.Event()
    server_error: list[BaseException] = []

    def run_server() -> None:
        try:
            serve(host=host, port=port, open_browser=False, block=True)
        except BaseException as exc:
            server_error.append(exc)
        finally:
            stop.set()

    thread = threading.Thread(target=run_server, name="milodi-web", daemon=False)
    thread.start()

    if not _wait_for_server(url, STARTUP_TIMEOUT_S):
        stop.set()
        if server_error:
            _mac_alert("Milodi 启动失败", str(server_error[0]))
        else:
            _mac_alert("Milodi 启动失败", "服务在预期时间内未能就绪，请稍后重试。")
        return 1

    webbrowser.open(url)

    def _shutdown(_signum=None, _frame=None) -> None:
        stop.set()
        from milodi.web.app import request_shutdown

        request_shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        while thread.is_alive() and not stop.is_set():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        _shutdown()

    from milodi.web.app import request_shutdown

    request_shutdown()
    thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
