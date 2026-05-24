import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from urllib.parse import urlparse

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


def build_ffmpeg_cmd(m3u8: str, output_path: str, referer: str = "") -> list[str]:
    cmd = [
        "ffmpeg",
        "-threads", "0",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-user_agent", USER_AGENT,
    ]
    if referer:
        cmd += ["-referer", referer, "-headers", f"Origin: {referer.rstrip('/')}\r\n"]
    cmd += [
        "-i", m3u8,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-y",
        output_path,
    ]
    return cmd


HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M3U8 下载助手</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f1117; color: #c9d1d9; min-height: 100vh; padding: 2rem 1rem;
  }
  .container { max-width: 780px; margin: 0 auto; }
  h1 { font-size: 1.6rem; font-weight: 700; color: #f0f6fc; margin-bottom: .4rem; }
  .tagline { font-size: .9rem; color: #6e7681; margin-bottom: 2rem; }
  .warn-banner {
    background: #3d1f00; border: 1px solid #d68910; border-radius: 8px;
    padding: .8rem 1.2rem; margin-bottom: 1.5rem; color: #f0b429;
    font-size: .88rem; display: none;
  }
  .card {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 1.4rem; margin-bottom: 1.2rem;
  }
  .card-label {
    font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
    color: #58a6ff; font-weight: 600; margin-bottom: .9rem;
  }
  .input-row { display: flex; gap: .6rem; }
  input[type="text"] {
    flex: 1; padding: .65rem 1rem; background: #0d1117;
    border: 1px solid #30363d; border-radius: 8px; color: #c9d1d9;
    font-size: .92rem; outline: none; transition: border-color .2s;
  }
  input[type="text"]:focus { border-color: #58a6ff; }
  input[type="text"]::placeholder { color: #484f58; }
  button {
    padding: .65rem 1.2rem; border: none; border-radius: 8px; cursor: pointer;
    font-size: .88rem; font-weight: 600; transition: all .15s; white-space: nowrap;
  }
  .btn-blue { background: #1f6feb; color: #fff; }
  .btn-blue:hover { background: #388bfd; }
  .btn-blue:disabled { background: #1f3a5f; color: #6e7681; cursor: not-allowed; }
  .btn-green { background: #238636; color: #fff; }
  .btn-green:hover { background: #2ea043; }
  .btn-green:disabled { background: #1a3624; color: #6e7681; cursor: not-allowed; }
  .btn-red { background: #b91c1c; color: #fff; }
  .btn-red:hover { background: #dc2626; }
  .btn-ghost { background: transparent; color: #c9d1d9; border: 1px solid #30363d; }
  .btn-ghost:hover { background: #21262d; }
  .links-list { display: flex; flex-direction: column; gap: .5rem; }
  .link-item {
    display: flex; align-items: center; gap: .8rem; padding: .7rem .9rem;
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    cursor: pointer; transition: border-color .15s;
  }
  .link-item:hover { border-color: #58a6ff; }
  .link-item.selected { border-color: #58a6ff; background: #0d2045; }
  .link-item input[type="radio"] { accent-color: #58a6ff; flex-shrink: 0; }
  .link-url { font-size: .82rem; color: #8b949e; word-break: break-all; font-family: monospace; }
  .empty-hint { color: #484f58; font-size: .88rem; text-align: center; padding: 1rem; }
  .config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; }
  @media (max-width: 540px) { .config-grid { grid-template-columns: 1fr; } }
  .config-item label { display: block; font-size: .78rem; color: #8b949e; margin-bottom: .4rem; }
  .cmd-block {
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 1rem; font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: .82rem; color: #7ee787; word-break: break-all;
    white-space: pre-wrap; min-height: 3rem; margin-bottom: .8rem;
  }
  .action-row { display: flex; gap: .6rem; flex-wrap: wrap; }
  .progress-wrap { margin-top: 1rem; display: none; }
  .progress-bar-bg { background: #21262d; border-radius: 4px; height: 6px; overflow: hidden; margin-bottom: .6rem; }
  .progress-bar { height: 100%; background: #1f6feb; width: 0%; transition: width .3s; border-radius: 4px; }
  .progress-log {
    background: #0d1117; border: 1px solid #21262d; border-radius: 6px;
    padding: .6rem .8rem; font-family: monospace; font-size: .78rem;
    color: #6e7681; max-height: 120px; overflow-y: auto;
  }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #30363d; border-top-color: #58a6ff;
    border-radius: 50%; animation: spin .7s linear infinite;
    vertical-align: middle; margin-right: .4rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .toast {
    position: fixed; bottom: 2rem; right: 2rem; background: #238636; color: #fff;
    padding: .8rem 1.4rem; border-radius: 8px; font-size: .9rem; font-weight: 600;
    opacity: 0; transition: opacity .3s; pointer-events: none;
  }
  .toast.error { background: #b91c1c; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<div class="container">
  <h1>M3U8 下载助手</h1>
  <p class="tagline">输入视频网址，自动提取 m3u8 链接并生成 ffmpeg 下载命令</p>
  <div class="warn-banner" id="ffmpegWarn">
    ⚠ 未检测到 ffmpeg，请先安装：<code>brew install ffmpeg</code>
  </div>
  <div class="card">
    <div class="card-label">① 输入视频网址</div>
    <div class="input-row">
      <input type="text" id="urlInput" placeholder="https://example.com/video/12345" />
      <button class="btn-blue" id="analyzeBtn" onclick="doAnalyze()">分析链接</button>
    </div>
  </div>
  <div class="card">
    <div class="card-label">② 发现的 M3U8 链接</div>
    <div id="linksList"><div class="empty-hint">输入网址后点击"分析链接"</div></div>
  </div>
  <div class="card">
    <div class="card-label">③ 下载配置</div>
    <div class="config-grid">
      <div class="config-item">
        <label>保存目录</label>
        <div class="input-row">
          <input type="text" id="dirInput" placeholder="/Users/you/Downloads" oninput="updateCmd()" />
          <button class="btn-ghost" onclick="doPickDir()">选择</button>
        </div>
      </div>
      <div class="config-item">
        <label>文件名（不含扩展名）</label>
        <input type="text" id="filenameInput" placeholder="my-video" oninput="updateCmd()" />
      </div>
    </div>
    <div class="config-item" style="margin-top:.8rem">
      <label>来源网址（Referer，遇到 403 时填写视频所在页面）</label>
      <input type="text" id="refererInput" placeholder="https://www.example.com/video-page" oninput="updateCmd()" />
    </div>
  </div>
  <div class="card">
    <div class="card-label">④ ffmpeg 命令</div>
    <div class="cmd-block" id="cmdBlock">（选择 M3U8 链接并填写配置后自动生成）</div>
    <div class="action-row">
      <button class="btn-ghost" onclick="doCopy()">复制命令</button>
      <button class="btn-green" id="executeBtn" onclick="doExecute()">开始下载</button>
    </div>
    <div class="progress-wrap" id="progressWrap">
      <div class="progress-bar-bg"><div class="progress-bar" id="progressBar"></div></div>
      <div class="progress-log" id="progressLog"></div>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let selectedM3u8 = '';
let eventSource = null;
let totalSeconds = null;

fetch('/status').then(r => r.json()).then(d => {
  if (!d.ffmpeg) document.getElementById('ffmpegWarn').style.display = 'block';
});

function showToast(msg, isError) {
  isError = isError || false;
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast' + (isError ? ' error' : '') + ' show';
  setTimeout(function() { el.className = 'toast'; }, 2500);
}

function setLoading(btnId, loading, text) {
  const btn = document.getElementById(btnId);
  btn.disabled = loading;
  btn.innerHTML = loading ? '<span class="spinner"></span>' + text : text;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function doAnalyze() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { showToast('请输入视频网址', true); return; }
  setLoading('analyzeBtn', true, '分析中...');
  document.getElementById('linksList').innerHTML =
    '<div class="empty-hint"><span class="spinner"></span>正在抓取页面...</div>';
  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, true); renderLinks([]); return; }
    renderLinks(data.links || []);
    if (!document.getElementById('refererInput').value) {
      document.getElementById('refererInput').value = url;
      updateCmd();
    }
  } catch (e) {
    showToast('请求失败：' + e.message, true);
    renderLinks([]);
  } finally {
    setLoading('analyzeBtn', false, '分析链接');
  }
}

function renderLinks(links) {
  const container = document.getElementById('linksList');
  if (!links.length) {
    container.innerHTML =
      '<div class="empty-hint">未找到 M3U8 链接。<br>可用浏览器开发者工具（F12 → Network → 过滤 m3u8）手动查找后粘贴到上方输入框</div>';
    selectedM3u8 = '';
    updateCmd();
    return;
  }
  container.innerHTML = '<div class="links-list">' + links.map(function(url, i) {
    return '<div class="link-item' + (i === 0 ? ' selected' : '') +
    '" data-url="' + escHtml(url) + '" onclick="selectLink(this)">' +
    '<input type="radio" name="m3u8" ' + (i === 0 ? 'checked' : '') + ' />' +
    '<span class="link-url">' + escHtml(url) + '</span></div>';
  }).join('') + '</div>';
  selectedM3u8 = links[0];
  updateCmd();
}

function selectLink(el) {
  document.querySelectorAll('.link-item').forEach(function(e) { e.classList.remove('selected'); });
  el.classList.add('selected');
  el.querySelector('input[type="radio"]').checked = true;
  selectedM3u8 = el.dataset.url;
  updateCmd();
}

async function doPickDir() {
  try {
    const res = await fetch('/pick-dir', { method: 'POST' });
    const data = await res.json();
    if (data.path) {
      document.getElementById('dirInput').value = data.path;
      updateCmd();
    }
  } catch (e) {
    showToast('目录选择失败：' + e.message, true);
  }
}

function updateCmd() {
  const m3u8 = selectedM3u8;
  const dir = document.getElementById('dirInput').value.trim();
  const filename = document.getElementById('filenameInput').value.trim() || 'video';
  const referer = document.getElementById('refererInput').value.trim();
  const cmdBlock = document.getElementById('cmdBlock');
  if (!m3u8) { cmdBlock.textContent = '（请先分析并选择一个 M3U8 链接）'; return; }
  const ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
  const outputPath = (dir ? dir + '/' : '') + filename + '.mp4';
  const parts = [
    'ffmpeg -threads 0',
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    '-user_agent "' + ua + '"',
  ];
  if (referer) {
    parts.push('-referer "' + referer + '"');
    try {
      const origin = new URL(referer).origin;
      parts.push('-headers "Origin: ' + origin + '\\r\\n"');
    } catch (e) {}
  }
  parts.push('-i "' + m3u8 + '"', '-c copy -bsf:a aac_adtstoasc -y', '"' + outputPath + '"');
  cmdBlock.textContent = parts.join(' \\\n  ');
}

async function doCopy() {
  const cmd = document.getElementById('cmdBlock').textContent;
  if (cmd.startsWith('（')) { showToast('请先生成命令', true); return; }
  await navigator.clipboard.writeText(cmd);
  showToast('已复制到剪贴板');
}

async function doExecute() {
  const btn = document.getElementById('executeBtn');
  if (btn.dataset.state === 'running') { doStop(); return; }
  if (!selectedM3u8) { showToast('请先选择 M3U8 链接', true); return; }
  const dir = document.getElementById('dirInput').value.trim();
  const filename = document.getElementById('filenameInput').value.trim() || 'video';
  if (!dir) { showToast('请选择保存目录', true); return; }
  try {
    const res = await fetch('/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ m3u8: selectedM3u8, output: dir, filename: filename, referer: document.getElementById('refererInput').value.trim() })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, true); return; }
    btn.textContent = '停止下载';
    btn.className = 'btn-red';
    btn.dataset.state = 'running';
    const wrap = document.getElementById('progressWrap');
    wrap.style.display = 'block';
    document.getElementById('progressLog').textContent = '';
    document.getElementById('progressBar').style.width = '0%';
    totalSeconds = null;
    startSSE();
  } catch (e) {
    showToast('执行失败：' + e.message, true);
    resetExecuteBtn();
  }
}

async function doStop() {
  await fetch('/stop', { method: 'POST' });
  resetExecuteBtn();
  if (eventSource) { eventSource.close(); eventSource = null; }
  showToast('已停止下载');
}

function resetExecuteBtn() {
  const btn = document.getElementById('executeBtn');
  btn.textContent = '开始下载';
  btn.className = 'btn-green';
  btn.dataset.state = '';
}

function startSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/progress');
  eventSource.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.error) { showToast(data.error, true); return; }
    const line = data.line || '';
    const log = document.getElementById('progressLog');
    log.textContent = line;
    const timeMatch = line.match(/time=(\\d+):(\\d+):(\\d+(?:\\.\\d+)?)/);
    if (timeMatch) {
      const elapsed = parseInt(timeMatch[1]) * 3600 + parseInt(timeMatch[2]) * 60 + parseFloat(timeMatch[3]);
      if (totalSeconds) {
        document.getElementById('progressBar').style.width =
          Math.min(100, (elapsed / totalSeconds) * 100) + '%';
      } else {
        document.getElementById('progressBar').style.width = (elapsed % 30) / 30 * 100 + '%';
      }
    }
    const durMatch = line.match(/Duration:\\s*(\\d+):(\\d+):(\\d+(?:\\.\\d+)?)/);
    if (durMatch) {
      totalSeconds = parseInt(durMatch[1]) * 3600 + parseInt(durMatch[2]) * 60 + parseFloat(durMatch[3]);
    }
  };
  eventSource.addEventListener('done', function(e) {
    eventSource.close(); eventSource = null;
    const data = JSON.parse(e.data);
    resetExecuteBtn();
    document.getElementById('progressBar').style.width = data.success ? '100%' : '0%';
    showToast(data.success ? '下载完成！' : ('下载失败（退出码 ' + data.code + '）'), !data.success);
  });
  eventSource.onerror = function() {
    eventSource.close(); eventSource = null;
    resetExecuteBtn();
    showToast('连接中断', true);
  };
}
</script>
</body>
</html>
"""


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
    referer: str = ""


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
    import asyncio
    script = (
        "import tkinter as tk; from tkinter import filedialog; "
        "root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', True); "
        "path = filedialog.askdirectory(title='选择下载目录'); "
        "root.destroy(); print(path or '', end='')"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {"path": stdout.decode().strip()}
    except asyncio.TimeoutError:
        return {"path": ""}
    except Exception:
        return {"path": ""}


@app.post("/execute")
async def execute(body: ExecuteRequest):
    global ffmpeg_process
    with ffmpeg_lock:
        if ffmpeg_process and ffmpeg_process.poll() is None:
            return JSONResponse(
                {"error": "已有下载任务在运行，请先停止"},
                status_code=409,
            )
        output_path = os.path.join(body.output, body.filename + ".mp4")
        cmd = build_ffmpeg_cmd(body.m3u8, output_path, body.referer)
        ffmpeg_process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    return {"pid": ffmpeg_process.pid, "cmd": " ".join(shlex.quote(a) for a in cmd)}


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
        with ffmpeg_lock:
            ffmpeg_process = None
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
    import webbrowser

    def _open_browser():
        import time
        time.sleep(0.8)
        webbrowser.open("http://localhost:8888")

    threading.Thread(target=_open_browser, daemon=True).start()
    print("M3U8 下载助手已启动：http://localhost:8888")
    uvicorn.run(app, host="127.0.0.1", port=8888)
