import pytest
from app import extract_m3u8_links, build_ffmpeg_cmd, should_open_browser


def test_extract_direct_url():
    html = '<source src="https://cdn.example.com/video/master.m3u8?token=abc">'
    links = extract_m3u8_links(html)
    assert "https://cdn.example.com/video/master.m3u8?token=abc" in links


def test_extract_json_field():
    html = '{"playUrl":"https://cdn.example.com/hls/index.m3u8","poster":"img.jpg"}'
    links = extract_m3u8_links(html)
    assert "https://cdn.example.com/hls/index.m3u8" in links


def test_extract_deduplication():
    url = "https://cdn.example.com/video/master.m3u8"
    html = f'src="{url}" data-url="{url}"'
    links = extract_m3u8_links(html)
    assert links.count(url) == 1


def test_extract_escaped_slashes():
    html = r'"hlsUrl":"https:\/\/cdn.example.com\/hls\/stream.m3u8"'
    links = extract_m3u8_links(html)
    assert "https://cdn.example.com/hls/stream.m3u8" in links


def test_extract_empty():
    links = extract_m3u8_links("<html><body>no links here</body></html>")
    assert links == []


def test_build_ffmpeg_cmd_flags():
    cmd = build_ffmpeg_cmd("https://cdn.example.com/video.m3u8", "/tmp/output.mp4")
    assert isinstance(cmd, list)
    assert "-threads" in cmd and "0" in cmd
    assert "-c" in cmd and "copy" in cmd
    assert "-bsf:a" in cmd and "aac_adtstoasc" in cmd
    assert "-y" in cmd
    assert "-reconnect" in cmd
    assert "-reconnect_streamed" in cmd
    assert "-reconnect_delay_max" in cmd
    assert "https://cdn.example.com/video.m3u8" in cmd
    assert "/tmp/output.mp4" in cmd


def test_should_open_browser_can_be_disabled(monkeypatch):
    monkeypatch.setenv("M3U8_DOWNLOADER_NO_BROWSER", "1")
    assert should_open_browser() is False


def test_should_open_browser_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("M3U8_DOWNLOADER_NO_BROWSER", raising=False)
    assert should_open_browser() is True
