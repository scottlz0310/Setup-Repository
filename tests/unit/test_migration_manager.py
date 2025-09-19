"""migration_manager.py のテスト"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.migration_manager import MigrationManager


class TestMigrationManager:
    """MigrationManagerのテストクラス"""

    @pytest.fixture
    def temp_project(self):
        """テスト用の一時プロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # 基本的なプロジェクト構造を作成
            (project_root / "config.json.template").write_text(
                json.dumps({"owner": "test-owner", "dest": "test-dest", "new_setting": "default_value"}, indent=2),
                encoding="utf-8",
            )

            (project_root / "config.local.json").write_text(
                json.dumps({"owner": "test-owner", "dest": "test-dest"}, indent=2), encoding="utf-8"
            )

            (project_root / "pyproject.toml").write_text(
                '[project]\nname = "test-project"\nversion = "1.2.0"\n', encoding="utf-8"
            )

            # 品質トレンドデータ
            output_dir = project_root / "output" / "quality-trends"
            output_dir.mkdir(parents=True)
            (output_dir / "trend-data.json").write_text(
                json.dumps([{"timestamp": "2025-01-01T00:00:00Z", "score": 85.0, "coverage": 80.0}], indent=2),
                encoding="utf-8",
            )

            yield project_root

    @pytest.fixture
    def migration_manager(self, temp_project):
        """MigrationManagerインスタンス"""
        return MigrationManager(temp_project)

    def test_init(self, temp_project):
        """初期化テスト"""
        manager = MigrationManager(temp_project)

        assert manager.project_root == temp_project
        assert manager.migrations_dir.exists()
        assert manager.version_file.name == "version.json"

    def test_get_current_version_no_file(self, migration_manager):
        """バージョンファイルが存在しない場合のテスト"""
        version = migration_manager._get_current_version()
        assert version == "0.0.0"

    def test_get_current_version_with_file(self, migration_manager):
        """バージョンファイルが存在する場合のテスト"""
        version_data = {"version": "1.1.0", "updated_at": "2025-01-01T00:00:00Z"}

        with open(migration_manager.version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f)

        version = migration_manager._get_current_version()
        assert version == "1.1.0"

    def test_get_target_version(self, migration_manager):
        """ターゲットバージョン取得テスト"""
        version = migration_manager._get_target_version()
        assert version == "1.2.0"

    def test_check_migration_needed_no_migration(self, migration_manager):
        """マイグレーション不要の場合のテスト"""
        # 現在のバージョンをターゲットと同じに設定
        version_data = {"version": "1.2.0", "updated_at": "2025-01-01T00:00:00Z"}

        with open(migration_manager.version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f)

        result = migration_manager.check_migration_needed()

        assert not result["migration_needed"]
        assert result["current_version"] == "1.2.0"
        assert result["target_version"] == "1.2.0"
        assert result["changes"] == []

    def test_check_migration_needed_with_migration(self, migration_manager):
        """マイグレーション必要な場合のテスト"""
        result = migration_manager.check_migration_needed()

        assert result["migration_needed"]
        assert result["current_version"] == "0.0.0"
        assert result["target_version"] == "1.2.0"
        assert len(result["changes"]) > 0

    def test_detect_config_changes(self, migration_manager):
        """設定ファイル変更検出テスト"""
        changes = migration_manager._check_config_changes()

        # new_settingが新しいキーとして検出される
        assert len(changes) == 1
        assert changes[0]["type"] == "config_update"
        assert "new_setting" in changes[0]["description"]

    def test_detect_data_structure_changes(self, migration_manager):
        """データ構造変更検出テスト"""
        changes = migration_manager._check_data_structure_changes()

        # scoreとcoverageフィールドが古い形式として検出される
        assert len(changes) == 1
        assert changes[0]["type"] == "data_structure_update"

    def test_migrate_config_files(self, migration_manager):
        """設定ファイルマイグレーションテスト"""
        result = migration_manager._migrate_config_files()

        assert result is not None
        assert result["type"] == "config_migration"
        assert "backup_file" in result

        # 更新された設定ファイルを確認
        config_file = migration_manager.project_root / "config.local.json"
        with open(config_file, encoding="utf-8") as f:
            updated_config = json.load(f)

        assert "new_setting" in updated_config
        assert updated_config["new_setting"] == "default_value"

    def test_migrate_data_structures(self, migration_manager):
        """データ構造マイグレーションテスト"""
        result = migration_manager._migrate_data_structures()

        assert result is not None
        assert result["type"] == "data_migration"
        assert "backup_file" in result

        # 更新されたデータを確認
        trend_file = migration_manager.project_root / "output" / "quality-trends" / "trend-data.json"
        with open(trend_file, encoding="utf-8") as f:
            updated_data = json.load(f)

        assert "quality_score" in updated_data[0]
        assert "test_coverage" in updated_data[0]
        assert updated_data[0]["quality_score"] == 85.0
        assert updated_data[0]["test_coverage"] == 80.0

    @patch("setup_repo.migration_manager.datetime")
    def test_run_migration_success(self, mock_datetime, migration_manager):
        """マイグレーション実行成功テスト"""
        mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T00:00:00Z"
        mock_datetime.now.return_value.strftime.return_value = "20250101_000000"

        result = migration_manager.run_migration(backup=False)

        assert result["success"]
        assert "マイグレーションが完了しました" in result["message"]
        assert "migration_result" in result

    def test_run_migration_no_migration_needed(self, migration_manager):
        """マイグレーション不要時のテスト"""
        # 現在のバージョンをターゲットと同じに設定
        version_data = {"version": "1.2.0", "updated_at": "2025-01-01T00:00:00Z"}

        with open(migration_manager.version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f)

        result = migration_manager.run_migration()

        assert result["success"]
        assert "マイグレーションは不要です" in result["message"]

    def test_create_migration_backup(self, migration_manager):
        """マイグレーションバックアップ作成テスト"""
        # 実際のバックアップ作成をテスト
        backup_path = migration_manager._create_migration_backup()

        assert backup_path.exists()
        assert backup_path.suffix == ".gz"
        assert "migration_backup_" in backup_path.name

        # メタデータファイルも作成されることを確認
        metadata_file = backup_path.parent / f"{backup_path.stem.replace('.tar', '')}.json"
        assert metadata_file.exists()

    def test_update_version(self, migration_manager):
        """バージョン更新テスト"""
        migration_manager._update_version("1.2.0")

        assert migration_manager.version_file.exists()

        with open(migration_manager.version_file, encoding="utf-8") as f:
            version_data = json.load(f)

        assert version_data["version"] == "1.2.0"
        assert "updated_at" in version_data
        assert "migration_history" in version_data

    def test_get_migration_history_no_file(self, migration_manager):
        """マイグレーション履歴取得（ファイルなし）テスト"""
        history = migration_manager._get_migration_history()
        assert history == []

    def test_get_migration_history_with_file(self, migration_manager):
        """マイグレーション履歴取得（ファイルあり）テスト"""
        version_data = {
            "version": "1.1.0",
            "migration_history": [{"version": "1.0.0", "migrated_at": "2025-01-01T00:00:00Z"}],
        }

        with open(migration_manager.version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f)

        history = migration_manager._get_migration_history()
        assert len(history) == 1
        assert history[0]["version"] == "1.0.0"

    def test_rollback_migration_no_backups(self, migration_manager):
        """バックアップなしでのロールバックテスト"""
        result = migration_manager.rollback_migration()

        assert not result["success"]
        assert "利用可能なバックアップがありません" in result["error"]

    def test_rollback_migration_success(self, migration_manager):
        """ロールバック成功テスト"""
        # 実際のバックアップを作成
        backup_path = migration_manager._create_migration_backup()
        backup_name = backup_path.stem.replace(".tar", "")

        # ロールバック実行
        result = migration_manager.rollback_migration(backup_name)

        assert result["success"]
        assert backup_name in result["message"]

    def test_list_migration_backups(self, migration_manager):
        """マイグレーションバックアップ一覧テスト"""
        # バックアップディレクトリとメタデータを作成
        backup_dir = migration_manager.migrations_dir / "backups"
        backup_dir.mkdir(parents=True)

        backup_metadata = {"name": "test_backup", "timestamp": "2025-01-01T00:00:00Z", "version": "1.0.0"}

        metadata_file = backup_dir / "test_backup.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(backup_metadata, f)

        backups = migration_manager._list_migration_backups()

        assert len(backups) == 1
        assert backups[0]["name"] == "test_backup"
        assert backups[0]["version"] == "1.0.0"

    def test_error_handling_invalid_json(self, migration_manager):
        """不正なJSONファイルのエラーハンドリングテスト"""
        # 不正なJSONファイルを作成
        config_file = migration_manager.project_root / "config.local.json"
        config_file.write_text("invalid json", encoding="utf-8")

        # エラーが発生しても例外が発生しないことを確認
        changes = migration_manager._check_config_changes()
        assert isinstance(changes, list)

    def test_error_handling_missing_files(self, migration_manager):
        """ファイル不存在時のエラーハンドリングテスト"""
        # 設定ファイルを削除
        config_file = migration_manager.project_root / "config.local.json"
        config_file.unlink()

        # エラーが発生しても例外が発生しないことを確認
        changes = migration_manager._check_config_changes()
        assert isinstance(changes, list)

    @patch("setup_repo.migration_manager.logger")
    def test_logging(self, mock_logger, migration_manager):
        """ログ出力テスト"""
        migration_manager.check_migration_needed()

        # ログが呼び出されることを確認
        mock_logger.info.assert_called()
