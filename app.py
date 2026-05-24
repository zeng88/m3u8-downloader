import re
import shutil
import subprocess
import threading
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

import requests as http_requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# ── Globals ───────────────────────────────────────────────────────────────────
ffmpeg_process: Optional[subprocess.Popen] = None
ffmpeg_lock = threading.Lock()
FFMPEG_AVAILABLE = False

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def extract_m3u8_links(html: str) -> list[str]:
    # First normalize escaped slashes in the HTML
    normalized_html = html.replace("\\u002F", "/").replace("\\/", "/")

    patterns = [
        r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*',
        r'"(?:url|src|hls|stream|playUrl|hlsUrl|m3u8Url)"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"',
        r"'(https?://[^']+\.m3u8[^']*)'",
    ]
    found = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, normalized_html, re.IGNORECASE):
            url = match.group(1) if match.lastindex else match.group(0)
            if url not in seen:
                seen.add(url)
                found.append(url)
    return found


def build_ffmpeg_cmd(m3u8: str, output_path: str) -> str:
    return (
        f'ffmpeg -threads 0 '
        f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
        f'-user_agent "{USER_AGENT}" '
        f'-i "{m3u8}" '
        f'-c copy -bsf:a aac_adtstoasc -y '
        f'"{output_path}"'
    )


HTML_CONTENT = "<html><body><h1>Coming soon</h1></body></html>"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global FFMPEG_AVAILABLE
    FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
    yield


app = FastAPI(lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    url: str


class ExecuteRequest(BaseModel):
    m3u8: str
    output: str
    filename: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT


@app.get("/status")
async def status():
    return {"ffmpeg": FFMPEG_AVAILABLE}


@app.post("/analyze")
async def analyze(body: AnalyzeRequest):
    url = body.url.strip()
    if not url.startswith("http"):
        return JSONResponse({"error": "请输入有效的 http/https 网址"}, status_code=400)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        resp = http_requests.get(url, timeout=15, headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer,
        })
        resp.raise_for_status()
        links = extract_m3u8_links(resp.text)
        return {"links": links}
    except http_requests.exceptions.Timeout:
        return JSONResponse({"error": "请求超时，请检查网址或网络连接"}, status_code=504)
    except http_requests.exceptions.HTTPError as e:
        return JSONResponse(
            {"error": f"页面请求失败：HTTP {e.response.status_code}"},
            status_code=502,
        )
    except Exception as e:
        return JSONResponse({"error": f"分析失败：{str(e)}"}, status_code=500)


@app.post("/pick-dir")
async def pick_dir():
    result = {"path": ""}
    event = threading.Event()

    def _open_dialog():
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择下载目录")
        root.destroy()
        result["path"] = path or ""
        event.set()

    t = threading.Thread(target=_open_dialog, daemon=True)
    t.start()
    event.wait(timeout=120)
    return result


@app.post("/execute")
async def execute(body: ExecuteRequest):
    global ffmpeg_process
    with ffmpeg_lock:
        if ffmpeg_process and ffmpeg_process.poll() is None:
            return JSONResponse(
                {"error": "已有下载任务在运行，请先停止"},
                status_code=409,
            )
        import os
        output_path = os.path.join(body.output, body.filename + ".mp4")
        cmd = build_ffmpeg_cmd(body.m3u8, output_path)
        ffmpeg_process = subprocess.Popen(
            cmd,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    return {"pid": ffmpeg_process.pid, "cmd": cmd}


@app.post("/stop")
async def stop():
    global ffmpeg_process
    with ffmpeg_lock:
        if ffmpeg_process and ffmpeg_process.poll() is None:
            ffmpeg_process.terminate()
            return {"ok": True}
    return {"ok": False, "reason": "无活跃进程"}


@app.get("/progress")
async def progress():
    import json

    async def generate() -> AsyncGenerator[str, None]:
        global ffmpeg_process
        if ffmpeg_process is None:
            yield 'data: {"error": "无活跃的下载任务"}\n\n'
            return
        for line in ffmpeg_process.stderr:
            line = line.strip()
            if not line:
                continue
            yield f"data: {json.dumps({'line': line})}\n\n"
        rc = ffmpeg_process.wait()
        if rc == 0:
            yield f"event: done\ndata: {json.dumps({'success': True})}\n\n"
        else:
            yield f"event: done\ndata: {json.dumps({'success': False, 'code': rc})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888)
