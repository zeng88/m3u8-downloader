from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
REQUIRED_SCRIPTS = (
    "start.sh",
    "start.command",
    "install.sh",
    "install-mac.command",
    "start.bat",
    "start-windows.ps1",
    "install-windows.bat",
    "install-windows.ps1",
)


def read_utf8(name: str) -> str:
    # 统一以 UTF-8 读取，提前发现中文脚本乱码。
    return (ROOT / name).read_text(encoding="utf-8")


def test_required_scripts_are_utf8_and_have_chinese_maintenance_comments():
    for name in REQUIRED_SCRIPTS:
        content = read_utf8(name)
        assert content.strip()
        assert "中文" in content or "项目" in content or "依赖" in content


def test_shell_scripts_pass_bash_syntax_check():
    for name in ("start.sh", "start.command", "install.sh", "install-mac.command"):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / name)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{name}: {result.stderr}"


def test_entrypoints_delegate_to_platform_implementations():
    assert "start-windows.ps1" in read_utf8("start.bat")
    assert "install-windows.ps1" in read_utf8("install-windows.bat")
    assert "start.sh" in read_utf8("start.command")
    assert "install.sh" in read_utf8("install-mac.command")


def test_scripts_use_project_virtual_environment_and_port():
    unix_start = read_utf8("start.sh")
    windows_start = read_utf8("start-windows.ps1")
    assert ".venv" in unix_start and "8888" in unix_start
    assert ".venv" in windows_start and "8888" in windows_start
