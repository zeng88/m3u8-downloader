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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888)
