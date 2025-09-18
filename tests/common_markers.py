"""テスト用共通マーカーとスキップ条件の定義"""

import platform

import pytest


def _is_wsl() -> bool:
    """WSL環境かどうかを判定"""
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except (FileNotFoundError, PermissionError):
        return False


# プラットフォーム別スキップ条件
skip_on_windows = pytest.mark.skipif(platform.system() == "Windows", reason="Windows環境では実行しない")

skip_on_unix = pytest.mark.skipif(platform.system() != "Windows", reason="Unix系環境では実行しない")

skip_on_linux = pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")

skip_on_macos = pytest.mark.skipif(platform.system() != "Darwin", reason="macOS環境でのみ実行")

skip_on_wsl = pytest.mark.skipif(not _is_wsl(), reason="WSL環境でのみ実行")

# プラットフォーム固有実行条件
windows_only = pytest.mark.skipif(platform.system() != "Windows", reason="Windows環境でのみ実行")

linux_only = pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")

macos_only = pytest.mark.skipif(platform.system() != "Darwin", reason="macOS環境でのみ実行")

unix_only = pytest.mark.skipif(platform.system() == "Windows", reason="Unix系環境でのみ実行")


def get_current_platform() -> str:
    """現在のプラットフォームを取得"""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Linux":
        return "wsl" if _is_wsl() else "linux"
    elif system == "Darwin":
        return "macos"
    else:
        return "unknown"


def requires_platform(platform_name: str):
    """指定されたプラットフォームでのみ実行するデコレータ"""
    current = get_current_platform()
    return pytest.mark.skipif(current != platform_name, reason=f"{platform_name}環境でのみ実行（現在: {current}）")


def skip_if_no_command(command: str):
    """指定されたコマンドが利用できない場合にスキップするデコレータ"""
    import shutil

    return pytest.mark.skipif(shutil.which(command) is None, reason=f"{command}コマンドが利用できません")
