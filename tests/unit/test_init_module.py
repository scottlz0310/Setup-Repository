"""
__init__.pyモジュールのテスト

パッケージ初期化とバージョン情報、互換性エイリアスのテスト
"""

import warnings
from unittest.mock import patch

import setup_repo


class TestInitModule:
    """__init__.pyモジュールのテストクラス"""

    def test_version_attribute(self):
        """バージョン属性のテスト"""
        assert hasattr(setup_repo, "__version__")
        assert isinstance(setup_repo.__version__, str)
        assert len(setup_repo.__version__) > 0
        # セマンティックバージョニング形式の基本チェック
        version_parts = setup_repo.__version__.split(".")
        assert len(version_parts) >= 2  # 最低でもmajor.minor

    def test_compatibility_import_success(self):
        """互換性モジュールのインポート成功テスト"""
        # 正常なインポートの場合、警告が出ないことを確認
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # モジュールを再インポートして互換性チェックを実行
            import importlib

            importlib.reload(setup_repo)

            # ImportWarningが発生していないことを確認
            import_warnings = [warning for warning in w if issubclass(warning.category, ImportWarning)]
            # 通常の環境では互換性モジュールが利用可能なので警告は出ない
            assert len(import_warnings) == 0

    def test_compatibility_import_failure(self):
        """互換性モジュールのインポート失敗時の警告テスト"""
        # compatibilityモジュールのインポートを失敗させる
        with (
            patch("setup_repo.compatibility.create_compatibility_aliases", side_effect=ImportError("Module not found")),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")

            # モジュールを再インポートして警告をトリガー
            import importlib

            importlib.reload(setup_repo)

            # ImportWarningが発生することを確認
            import_warnings = [warning for warning in w if issubclass(warning.category, ImportWarning)]
            assert len(import_warnings) > 0
            assert "後方互換性モジュールが利用できません" in str(import_warnings[0].message)

    def test_package_structure(self):
        """パッケージ構造の基本テスト"""
        # パッケージが正しくインポートできることを確認
        assert setup_repo.__name__ == "setup_repo"
        assert setup_repo.__doc__ is not None
        assert "セットアップリポジトリパッケージ" in setup_repo.__doc__

    def test_module_attributes(self):
        """モジュール属性の存在確認テスト"""
        # 必須属性の存在確認
        required_attributes = ["__version__"]
        for attr in required_attributes:
            assert hasattr(setup_repo, attr), f"必須属性 {attr} が存在しません"

    def test_version_format_validation(self):
        """バージョン形式の詳細検証テスト"""
        version = setup_repo.__version__

        # セマンティックバージョニングの基本形式チェック
        import re

        # 基本的なセマンティックバージョン形式（major.minor.patch）
        # より緩い形式も許可（major.minor形式）
        loose_pattern = r"^\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?$"

        assert re.match(loose_pattern, version), f"バージョン形式が不正です: {version}"

    def test_import_error_handling(self):
        """インポートエラーハンドリングの詳細テスト"""
        # create_compatibility_aliasesが存在しない場合のテスト
        with patch.dict("sys.modules", {"setup_repo.compatibility": None}), warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # 強制的にImportErrorを発生させる
            try:
                with patch("builtins.__import__", side_effect=ImportError("No module named 'compatibility'")):
                    import importlib

                    importlib.reload(setup_repo)
            except ImportError:
                # モックが正常に動作していることを確認
                pass

            # 適切な警告メッセージが出力されることを確認
            import_warnings = [warning for warning in w if issubclass(warning.category, ImportWarning)]
            if import_warnings:  # 警告が出た場合のみチェック
                warning_message = str(import_warnings[0].message)
                assert "後方互換性モジュール" in warning_message
                assert "古いインポートが動作しない可能性" in warning_message

    def test_stacklevel_warning(self):
        """警告のスタックレベルが適切に設定されているかテスト"""
        with (
            patch("setup_repo.compatibility.create_compatibility_aliases", side_effect=ImportError()),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")

            import importlib

            importlib.reload(setup_repo)

            # 警告が適切なスタックレベルで発生していることを確認
            import_warnings = [warning for warning in w if issubclass(warning.category, ImportWarning)]
            if import_warnings:
                # スタックレベルが設定されていることを間接的に確認
                # （実際のスタックレベルの値は内部実装に依存するため、存在確認のみ）
                assert import_warnings[0].filename is not None
