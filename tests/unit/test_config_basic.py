"""
config.pyの基本的なテスト

このファイルは、カバレッジ測定が正しく動作することを確認するための
基本的なテストです。
"""

import pytest


@pytest.mark.unit
def test_config_module_import() -> None:
    """config.pyモジュールのインポートテスト"""
    try:
        from src.setup_repo import config
        assert config is not None
    except ImportError as e:
        pytest.fail(f"config.pyのインポートに失敗しました: {e}")


@pytest.mark.unit
def test_utils_module_import() -> None:
    """utils.pyモジュールのインポートテスト"""
    try:
        from src.setup_repo import utils
        assert utils is not None
    except ImportError as e:
        pytest.fail(f"utils.pyのインポートに失敗しました: {e}")


@pytest.mark.unit
def test_platform_detector_module_import() -> None:
    """platform_detector.pyモジュールのインポートテスト"""
    try:
        from src.setup_repo import platform_detector
        assert platform_detector is not None
    except ImportError as e:
        pytest.fail(f"platform_detector.pyのインポートに失敗しました: {e}")