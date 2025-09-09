"""
基本的なモジュールインポートテスト

このファイルは、カバレッジ測定が正しく動作することを確認するための
基本的なテストです。詳細なテストは各モジュール専用のテストファイルで実施されます。
"""

import pytest


@pytest.mark.unit
def test_all_modules_import() -> None:
    """すべての主要モジュールのインポートテスト"""
    modules_to_test = [
        "config",
        "utils",
        "platform_detector",
        "cli",
        "git_operations",
        "github_api",
        "setup",
        "sync",
    ]

    for module_name in modules_to_test:
        try:
            module = __import__(f"src.setup_repo.{module_name}", fromlist=[module_name])
            assert module is not None, f"{module_name}モジュールがNoneです"
        except ImportError as e:
            pytest.fail(f"{module_name}.pyのインポートに失敗しました: {e}")


@pytest.mark.unit
def test_package_structure() -> None:
    """パッケージ構造の基本テスト"""
    try:
        import src.setup_repo

        assert hasattr(
            src.setup_repo, "__path__"
        ), "setup_repoパッケージが正しく構成されていません"
    except ImportError as e:
        pytest.fail(f"setup_repoパッケージのインポートに失敗しました: {e}")


@pytest.mark.unit
def test_main_entry_point() -> None:
    """メインエントリーポイントのインポートテスト"""
    try:
        # main.pyが存在し、インポート可能であることを確認
        import main

        assert main is not None
    except ImportError as e:
        pytest.fail(f"main.pyのインポートに失敗しました: {e}")
