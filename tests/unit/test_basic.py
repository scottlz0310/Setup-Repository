"""
基本的なテスト
"""

import platform

import pytest

from ..multiplatform.helpers import check_platform_modules, verify_current_platform


@pytest.mark.unit
def test_platform_detection():
    """現在のプラットフォームが検出できることをテスト"""
    # ヘルパー関数でプラットフォーム検証
    platform_info = verify_current_platform()  # プラットフォーム検証

    # 従来のテストも維持
    current_platform = platform.system()
    assert current_platform in ["Windows", "Linux", "Darwin"]

    # プラットフォーム情報の検証
    assert platform_info.name in ["windows", "linux", "wsl", "macos"]
    assert platform_info.shell in ["cmd", "sh"]  # セキュリティ修正後の新しい設定
    assert platform_info.python_cmd in ["python", "python3"]


@pytest.mark.unit
def test_basic_import():
    """基本的なインポートが動作することをテスト"""
    import sys

    assert sys.version_info >= (3, 9)


@pytest.mark.unit
def test_platform_modules():
    """プラットフォーム固有モジュールの可用性テスト"""
    # ヘルパー関数でモジュールチェック
    fcntl_info, msvcrt_info = check_platform_modules()

    # プラットフォームに応じたモジュール可用性を検証
    current_system = platform.system()
    if current_system == "Windows":
        assert not fcntl_info["available"]
        assert msvcrt_info["available"]
    else:
        assert fcntl_info["available"]
        assert not msvcrt_info["available"]
