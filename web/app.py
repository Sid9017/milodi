"""Milodi Web UI 服务。"""

from __future__ import annotations

import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Callable

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from milodi.export import to_h300_detail, to_h300_hex
from milodi.extract import (
    INSTRUMENTAL_CONFIG,
    PIANO_CONFIG,
    MelodyNote,
    extract_melody,
)

STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

_uploads: dict[str, Path] = {}
_server = None
_server_lock = threading.Lock()


def request_shutdown() -> None:
    with _server_lock:
        if _server is not None:
            _server.shutdown()


def _config_for_mode(mode: str):
    if mode == "instrumental":
        return INSTRUMENTAL_CONFIG
    if mode == "default":
        return None
    return PIANO_CONFIG


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.post("/api/analyze")
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "文件名为空"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in {".mp3", ".wav", ".m4a", ".flac", ".ogg"}:
        return jsonify({"error": "仅支持 MP3 / WAV / M4A / FLAC / OGG"}), 400

    file_id = uuid.uuid4().hex
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        f.save(tmp.name)
        tmp.close()
        mode = request.form.get("mode", "piano")
        notes = extract_melody(tmp.name, _config_for_mode(mode))
        _uploads[file_id] = Path(tmp.name)
    except Exception as exc:
        os.unlink(tmp.name)
        return jsonify({"error": f"分析失败: {exc}"}), 500

    total_ms = max((n.start_ms + n.duration_ms for n in notes), default=0)
    return jsonify(
        {
            "fileId": file_id,
            "filename": f.filename,
            "durationMs": total_ms,
            "noteCount": len(notes),
            "mode": mode,
            "notes": [n.to_dict() for n in notes],
        }
    )


@app.get("/api/audio/<file_id>")
def get_audio(file_id: str):
    path = _uploads.get(file_id)
    if not path or not path.exists():
        return jsonify({"error": "音频不存在"}), 404
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    mime = mime_map.get(path.suffix.lower(), "application/octet-stream")
    return send_from_directory(path.parent, path.name, mimetype=mime)


@app.post("/api/export")
def export():
    data = request.get_json(silent=True) or {}
    notes_raw = data.get("notes")
    fmt = data.get("format", "h300")
    start_ms = int(data.get("startMs", 0))
    end_ms = data.get("endMs")
    end_ms = int(end_ms) if end_ms is not None else None

    if not notes_raw:
        return jsonify({"error": "无音符数据"}), 400

    notes = [MelodyNote(**n) for n in notes_raw]

    if fmt == "h300-detail":
        content = to_h300_detail(notes, start_ms=start_ms, end_ms=end_ms)
        mime = "text/plain"
        filename = "melody.txt"
    else:
        content = to_h300_hex(notes, start_ms=start_ms, end_ms=end_ms, topic=0x41)
        mime = "text/plain"
        filename = "melody.hex"

    return app.response_class(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="启动 Milodi Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="启动后自动打开浏览器",
    )
    args = parser.parse_args()
    serve(
        host=args.host,
        port=args.port,
        open_browser=args.open_browser,
        block=True,
    )


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    open_browser: bool = False,
    block: bool = True,
    on_ready: Callable[[str], None] | None = None,
) -> None:
    """启动 Web 服务。block=True 时在调用线程阻塞直到服务停止。"""
    global _server
    url = f"http://{host}:{port}"
    print(f"Milodi Web UI: {url}", flush=True)

    with _server_lock:
        _server = make_server(host, port, app, threaded=True)

    if on_ready is not None:
        on_ready(url)
    elif open_browser:
        import webbrowser

        webbrowser.open(url)

    try:
        _server.serve_forever()
    finally:
        with _server_lock:
            _server = None


if __name__ == "__main__":
    main()
