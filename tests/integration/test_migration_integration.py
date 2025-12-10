"""migration機能の統合テスト"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.migration_manager import MigrationManager


class TestMigrationIntegration:
    """Migration機能の統合テストクラス"""

    @pytest.fixture
    def integration_project(self):
        """統合テスト用のプロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # 実際のプロジェクト構造を模擬
            (project_root / "config.json.template").write_text(
                json.dumps(
                    {
                        "owner": "test-owner",
                        "dest": "test-dest",
                        "use_https": False,
                        "sync_only": False,
                        "auto_stash": False,
                        "skip_uv_install": False,
                        "new_feature_flag": True,
                        "api_timeout": 30,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            (project_root / "config.local.json").write_text(
                json.dumps(
                    {"owner": "test-owner", "dest": "test-dest", "use_https": False, "sync_only": False}, indent=2
                ),
                encoding="utf-8",
            )

            (project_root / "pyproject.toml").write_text(
                """[project]
name = "setup-repository"
version = "2.0.0"
description = "GitHub repository setup and sync tool"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.pyright]
pythonVersion = "3.11"
strict = true
""",
                encoding="utf-8",
            )

            # 品質トレンドデータ（古い形式）
            output_dir = project_root / "output" / "quality-trends"
            output_dir.mkdir(parents=True)
            (output_dir / "trend-data.json").write_text(
                json.dumps(
                    [
                        {
                            "timestamp": "2025-01-01T00:00:00Z",
                            "score": 85.0,
                            "coverage": 80.0,
                            "ruff_issues": 5,
                            "mypy_errors": 2,
                            "pyright_errors": 2,
                        },
                        {
                            "timestamp": "2025-01-02T00:00:00Z",
                            "score": 87.0,
                            "coverage": 82.0,
                            "ruff_issues": 3,
                            "mypy_errors": 1,
                            "pyright_errors": 1,
                        },
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )

            # バックアップディレクトリ
            backup_dir = project_root / "backups"
            backup_dir.mkdir()

            yield project_root

    @pytest.fixture
    def migration_manager(self, integration_project):
        """統合テスト用MigrationManagerインスタンス"""
        return MigrationManager(integration_project)

    def test_full_migration_workflow(self, migration_manager):
        """完全なマイグレーションワークフローテスト"""
        # 1. マイグレーション必要性チェック
        check_result = migration_manager.check_migration_needed()

        assert check_result["migration_needed"]
        assert check_result["current_version"] == "0.0.0"
        assert check_result["target_version"] == "2.0.0"
        assert len(check_result["changes"]) > 0

        # 設定変更とデータ構造変更の両方が検出される
        change_types = [change["type"] for change in check_result["changes"]]
        assert "config_update" in change_types
        assert "data_structure_update" in change_types

    @patch("setup_repo.migration_manager.datetime")
    def test_migration_execution_with_backup(self, mock_datetime, migration_manager):
        """バックアップ付きマイグレーション実行テスト"""
        mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T12:00:00Z"
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

        # マイグレーション実行
        result = migration_manager.run_migration(backup=True)

        assert result["success"]
        assert "マイグレーションが完了しました" in result["message"]
        assert result["backup_path"] is not None

        # マイグレーション結果の確認
        migrations = result["migration_result"]["migrations"]
        assert len(migrations) == 2  # config + data migrations

        migration_types = [m["type"] for m in migrations]
        assert "config_migration" in migration_types
        assert "data_migration" in migration_types

    def test_config_migration_verification(self, migration_manager):
        """設定ファイルマイグレーションの検証"""
        # マイグレーション前の状態確認
        config_file = migration_manager.project_root / "config.local.json"
        with open(config_file, encoding="utf-8") as f:
            original_config = json.load(f)

        assert "new_feature_flag" not in original_config
        assert "api_timeout" not in original_config

        # マイグレーション実行
        migration_manager.run_migration(backup=False)

        # マイグレーション後の状態確認
        with open(config_file, encoding="utf-8") as f:
            updated_config = json.load(f)

        assert "new_feature_flag" in updated_config
        assert "api_timeout" in updated_config
        assert updated_config["new_feature_flag"] is True
        assert updated_config["api_timeout"] == 30

        # 既存の設定は保持される
        assert updated_config["owner"] == "test-owner"
        assert updated_config["dest"] == "test-dest"

    def test_data_structure_migration_verification(self, migration_manager):
        """データ構造マイグレーションの検証"""
        # マイグレーション前の状態確認
        trend_file = migration_manager.project_root / "output" / "quality-trends" / "trend-data.json"
        with open(trend_file, encoding="utf-8") as f:
            original_data = json.load(f)

        assert "quality_score" not in original_data[0]
        assert "test_coverage" not in original_data[0]
        assert "score" in original_data[0]
        assert "coverage" in original_data[0]

        # マイグレーション実行
        migration_manager.run_migration(backup=False)

        # マイグレーション後の状態確認
        with open(trend_file, encoding="utf-8") as f:
            updated_data = json.load(f)

        for item in updated_data:
            assert "quality_score" in item
            assert "test_coverage" in item
            # 元のデータも保持される
            assert "score" in item
            assert "coverage" in item
            # 値が正しく移行される
            assert item["quality_score"] == item["score"]
            assert item["test_coverage"] == item["coverage"]

    def test_version_tracking(self, migration_manager):
        """バージョン追跡テスト"""
        # 初期状態
        assert migration_manager._get_current_version() == "0.0.0"

        # マイグレーション実行
        migration_manager.run_migration(backup=False)

        # バージョンが更新される
        assert migration_manager._get_current_version() == "2.0.0"

        # バージョンファイルの内容確認
        with open(migration_manager.version_file, encoding="utf-8") as f:
            version_data = json.load(f)

        assert version_data["version"] == "2.0.0"
        assert "updated_at" in version_data
        assert "migration_history" in version_data
        assert len(version_data["migration_history"]) == 1
        assert version_data["migration_history"][0]["version"] == "2.0.0"

    def test_backup_creation_and_restoration(self, migration_manager):
        """バックアップ作成と復元テスト"""
        # 元の設定を記録
        config_file = migration_manager.project_root / "config.local.json"

        # マイグレーション実行（バックアップ付き）
        result = migration_manager.run_migration(backup=True)
        backup_path = Path(result["backup_path"])

        assert backup_path.exists()
        assert backup_path.suffix == ".gz"

        # 設定を変更
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"modified": True}, f)

        # ロールバック実行
        backup_name = backup_path.stem.replace(".tar", "")
        rollback_result = migration_manager.rollback_migration(backup_name)

        assert rollback_result["success"]

        # 元の設定が復元されることを確認
        with open(config_file, encoding="utf-8") as f:
            restored_config = json.load(f)

        # 復元後は新しい設定項目も含まれる（マイグレーション後の状態）
        assert "owner" in restored_config
        assert "dest" in restored_config

    def test_no_migration_needed_scenario(self, migration_manager):
        """マイグレーション不要シナリオテスト"""
        # 最初にマイグレーション実行
        migration_manager.run_migration(backup=False)

        # 再度チェック
        check_result = migration_manager.check_migration_needed()

        assert not check_result["migration_needed"]
        assert check_result["current_version"] == "2.0.0"
        assert check_result["target_version"] == "2.0.0"
        assert len(check_result["changes"]) == 0

        # 再度マイグレーション実行
        result = migration_manager.run_migration()

        assert result["success"]
        assert "マイグレーションは不要です" in result["message"]

    def test_error_recovery_scenario(self, migration_manager):
        """エラー回復シナリオテスト"""
        # 不正な設定ファイルを作成してエラーを発生させる
        config_file = migration_manager.project_root / "config.local.json"
        config_file.write_text("invalid json content", encoding="utf-8")

        # マイグレーション実行（エラーが発生するはず）
        result = migration_manager.run_migration(backup=True)

        # エラーが適切に処理される
        assert not result["success"]
        assert "error" in result
        assert result["backup_path"] is not None  # バックアップは作成される

    def test_multiple_migration_cycles(self, migration_manager):
        """複数回のマイグレーションサイクルテスト"""
        # 1回目のマイグレーション
        result1 = migration_manager.run_migration(backup=False)
        assert result1["success"]

        # バージョンを手動で変更して2回目のマイグレーションをシミュレート
        pyproject_file = migration_manager.project_root / "pyproject.toml"
        content = pyproject_file.read_text(encoding="utf-8")
        updated_content = content.replace('version = "2.0.0"', 'version = "2.1.0"')
        pyproject_file.write_text(updated_content, encoding="utf-8")

        # 新しい設定項目を追加
        template_file = migration_manager.project_root / "config.json.template"
        with open(template_file, encoding="utf-8") as f:
            template_config = json.load(f)
        template_config["another_new_setting"] = "new_value"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template_config, f, indent=2)

        # 2回目のマイグレーション
        check_result = migration_manager.check_migration_needed()
        assert check_result["migration_needed"]
        assert check_result["current_version"] == "2.0.0"
        assert check_result["target_version"] == "2.1.0"

        result2 = migration_manager.run_migration(backup=False)
        assert result2["success"]

        # マイグレーション履歴の確認
        history = migration_manager._get_migration_history()
        assert len(history) == 2
        assert history[0]["version"] == "2.0.0"
        assert history[1]["version"] == "2.1.0"

    def test_backup_metadata_integrity(self, migration_manager):
        """バックアップメタデータの整合性テスト"""
        result = migration_manager.run_migration(backup=True)
        backup_path = Path(result["backup_path"])

        # メタデータファイルの確認
        metadata_file = backup_path.parent / f"{backup_path.stem.replace('.tar', '')}.json"
        assert metadata_file.exists()

        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

        assert "name" in metadata
        assert "timestamp" in metadata
        assert "version" in metadata
        assert "files_backed_up" in metadata
        assert metadata["version"] == "0.0.0"  # マイグレーション前のバージョン

    def test_concurrent_migration_safety(self, migration_manager):
        """並行マイグレーション安全性テスト"""
        # 複数のマイグレーションマネージャーインスタンス
        manager2 = MigrationManager(migration_manager.project_root)

        # 両方でチェック実行
        check1 = migration_manager.check_migration_needed()
        check2 = manager2.check_migration_needed()

        # 同じ結果が得られる
        assert check1["migration_needed"] == check2["migration_needed"]
        assert check1["current_version"] == check2["current_version"]
        assert check1["target_version"] == check2["target_version"]

        # 一方でマイグレーション実行
        result1 = migration_manager.run_migration(backup=False)
        assert result1["success"]

        # もう一方でチェック（マイグレーション不要になる）
        check3 = manager2.check_migration_needed()
        assert not check3["migration_needed"]
