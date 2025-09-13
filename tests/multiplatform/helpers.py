"""
マルチプラットフォームテスト共通ヘルパー関数

各テストで再利用可能なプラットフォーム検出・検証ロジックを提供
"""

import platform

import pytest

from setup_repo.platform_detector import detect_platform


def verify_current_platform():
    """現在のプラットフォームを検証し、プラットフォーム情報を返す"""
    platform_info = detect_platform()
    current_system = platform.system()

    if current_system == "Windows":
        assert platform_info.name == "windows"
        assert platform_info.shell == "powershell"
    elif current_system == "Linux":
        assert platform_info.name in ["linux", "wsl"]
        assert platform_info.shell == "bash"
    elif current_system == "Darwin":
        assert platform_info.name == "macos"
        assert platform_info.shell == "zsh"
    else:
        pytest.skip(f"未対応のプラットフォーム: {current_system}")

    return platform_info


def check_platform_modules():
    """プラットフォーム固有モジュールの可用性をチェック"""
    from setup_repo.platform_detector import check_module_availability

    # fcntlモジュール（Unix系のみ）
    fcntl_info = check_module_availability("fcntl")
    if platform.system() == "Windows":
        assert not fcntl_info["available"]

    # msvcrtモジュール（Windowsのみ）
    msvcrt_info = check_module_availability("msvcrt")
    if platform.system() == "Windows":
        assert msvcrt_info["available"]
    else:
        assert not msvcrt_info["available"]

    return fcntl_info, msvcrt_info


def skip_if_not_platform(required_platform: str):
    """指定されたプラットフォームでない場合はスキップ"""
    current = platform.system()

    if required_platform == "windows" and current != "Windows":
        pytest.skip("Windows環境でのみ実行")
    elif required_platform == "unix" and current == "Windows":
        pytest.skip("Unix系環境でのみ実行")
    elif required_platform == "macos" and current != "Darwin":
        pytest.skip("macOS環境でのみ実行")


def get_platform_specific_config():
    """プラットフォーム固有の設定を取得"""
    platform_info = detect_platform()

    if platform_info.name == "windows":
        return {
            "path_separator": "\\",
            "shell": "powershell",
            "python_cmd": "python",
            "concurrent_limit": 4,
            "timeout": 30
        }
    else:
        return {
            "path_separator": "/",
            "shell": platform_info.shell,
            "python_cmd": "python3",
            "concurrent_limit": 8,
            "timeout": 60
        }


def optimize_for_platform():
    """プラットフォーム固有の最適化設定を適用"""
    platform_info = detect_platform()
    config = get_platform_specific_config()
    
    return {
        "platform": platform_info.name,
        "shell": config["shell"],
        "concurrent_limit": config["concurrent_limit"],
        "timeout": config["timeout"],
        "performance_mode": True
    }


def get_test_performance_config():
    """テスト用パフォーマンス設定を取得"""
    platform_config = get_platform_specific_config()
    
    return {
        "small_repo_limit": 5,
        "medium_repo_limit": 20,
        "large_repo_limit": 100,
        "concurrent_workers": platform_config["concurrent_limit"],
        "timeout_per_repo": platform_config["timeout"],
        "memory_limit_mb": 50
    }
