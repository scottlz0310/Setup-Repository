"""バックアップ管理のテスト"""

import tarfile
import tempfile
from pathlib import Path

import pytest

from setup_repo.backup_manager import BackupManager


class TestBackupManager:
    """BackupManagerクラスのテスト"""

    @pytest.fixture
    def temp_project(self):
        """テスト用の一時プロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # テスト用ファイルを作成
            (project_root / "config.local.json").write_text('{"test": "config"}')
            (project_root / "pyproject.toml").write_text('[tool.test]\nname = "test"')
            (project_root / ".gitignore").write_text("*.pyc\n__pycache__/")

            # quality-historyディレクトリを作成
            quality_dir = project_root / "quality-history"
            quality_dir.mkdir()
            (quality_dir / "metrics.json").write_text('{"score": 85}')

            # .vscodeディレクトリを作成
            vscode_dir = project_root / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text('{"python.defaultInterpreter": "python3"}')

            yield project_root

    @pytest.fixture
    def manager(self, temp_project):
        """BackupManagerインスタンス"""
        return BackupManager(temp_project)

    def test_create_backup(self, manager, temp_project):
        """バックアップ作成のテスト"""
        backup_path = manager.create_backup("test_backup")

        assert backup_path.exists()
        assert backup_path.name == "test_backup.tar.gz"
        assert backup_path.parent == manager.backup_dir

    def test_create_backup_with_auto_name(self, manager):
        """自動命名でのバックアップ作成のテスト"""
        backup_path = manager.create_backup()

        assert backup_path.exists()
        assert backup_path.name.startswith("backup_")
        assert backup_path.name.endswith(".tar.gz")

    def test_backup_contains_files(self, manager, temp_project):
        """バックアップにファイルが含まれることのテスト"""
        backup_path = manager.create_backup("test_backup")

        with tarfile.open(backup_path, "r:gz") as tar:
            names = tar.getnames()
            assert "config.local.json" in names
            assert "pyproject.toml" in names
            assert ".gitignore" in names
            assert "quality-history" in names
            assert ".vscode" in names

    def test_backup_metadata(self, manager):
        """バックアップメタデータのテスト"""
        backup_path = manager.create_backup("test_backup")

        with tarfile.open(backup_path, "r:gz") as tar:
            names = tar.getnames()
            assert "backup_metadata.json" in names

    def test_list_backups_empty(self, manager):
        """空のバックアップ一覧のテスト"""
        backups = manager.list_backups()
        assert backups == []

    def test_list_backups_with_data(self, manager):
        """バックアップがある場合の一覧のテスト"""
        # バックアップを作成
        manager.create_backup("backup1")
        manager.create_backup("backup2")

        backups = manager.list_backups()

        assert len(backups) == 2
        backup_names = [b["name"] for b in backups]
        assert "backup1" in backup_names
        assert "backup2" in backup_names

        # 最新のものが最初に来ることを確認
        assert backups[0]["created_at"] >= backups[1]["created_at"]

    def test_backup_metadata_content(self, manager):
        """バックアップメタデータの内容テスト"""
        manager.create_backup("test_backup")
        backups = manager.list_backups()

        assert len(backups) == 1
        backup = backups[0]

        assert backup["name"] == "test_backup"
        assert "created_at" in backup
        assert "project_root" in backup
        assert "targets" in backup
        assert "file_size" in backup

    def test_restore_backup(self, manager, temp_project):
        """バックアップ復元のテスト"""
        # 元のファイル内容を記録
        original_config = (temp_project / "config.local.json").read_text()

        # バックアップを作成
        manager.create_backup("test_backup")

        # ファイルを変更
        (temp_project / "config.local.json").write_text('{"modified": true}')

        # バックアップから復元
        success = manager.restore_backup("test_backup")

        assert success is True
        # 元の内容に戻っていることを確認
        restored_config = (temp_project / "config.local.json").read_text()
        assert restored_config == original_config

    def test_restore_backup_creates_backup_of_existing(self, manager, temp_project):
        """復元時に既存ファイルがバックアップされることのテスト"""
        # バックアップを作成
        manager.create_backup("test_backup")

        # ファイルを変更
        modified_content = '{"modified": true}'
        (temp_project / "config.local.json").write_text(modified_content)

        # バックアップから復元
        manager.restore_backup("test_backup")

        # 既存ファイルのバックアップが作成されることを確認
        restore_backup_dir = temp_project / ".restore_backup"
        assert restore_backup_dir.exists()

        backed_up_config = restore_backup_dir / "config.local.json"
        assert backed_up_config.exists()
        assert backed_up_config.read_text() == modified_content

    def test_restore_nonexistent_backup(self, manager):
        """存在しないバックアップの復元のテスト"""
        with pytest.raises(FileNotFoundError):
            manager.restore_backup("nonexistent_backup")

    def test_restore_backup_to_custom_path(self, manager, temp_project):
        """カスタムパスへのバックアップ復元のテスト"""
        # バックアップを作成
        manager.create_backup("test_backup")

        # カスタム復元先を作成
        custom_path = temp_project / "custom_restore"
        custom_path.mkdir()

        # カスタムパスに復元
        success = manager.restore_backup("test_backup", custom_path)

        assert success is True
        assert (custom_path / "config.local.json").exists()
        assert (custom_path / "pyproject.toml").exists()

    def test_remove_backup(self, manager):
        """バックアップ削除のテスト"""
        # バックアップを作成
        backup_path = manager.create_backup("test_backup")
        assert backup_path.exists()

        # バックアップを削除
        success = manager.remove_backup("test_backup")

        assert success is True
        assert not backup_path.exists()

    def test_remove_nonexistent_backup(self, manager):
        """存在しないバックアップの削除のテスト"""
        success = manager.remove_backup("nonexistent_backup")
        assert success is False

    def test_backup_with_missing_targets(self, temp_project):
        """一部のターゲットファイルが存在しない場合のテスト"""
        # 一部のファイルのみ存在する状態でマネージャーを作成
        (temp_project / "config.local.json").unlink()  # ファイルを削除

        manager = BackupManager(temp_project)
        backup_path = manager.create_backup("partial_backup")

        assert backup_path.exists()

        # バックアップの内容を確認
        with tarfile.open(backup_path, "r:gz") as tar:
            names = tar.getnames()
            assert "config.local.json" not in names  # 削除したファイルは含まれない
            assert "pyproject.toml" in names  # 存在するファイルは含まれる

    def test_get_size_file(self, manager, temp_project):
        """ファイルサイズ取得のテスト"""
        test_file = temp_project / "test.txt"
        test_content = "test content"
        test_file.write_text(test_content)

        size = manager._get_size(test_file)
        assert size == len(test_content.encode("utf-8"))

    def test_get_size_directory(self, manager, temp_project):
        """ディレクトリサイズ取得のテスト"""
        test_dir = temp_project / "test_dir"
        test_dir.mkdir()

        # ディレクトリ内にファイルを作成
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        size = manager._get_size(test_dir)
        expected_size = len(b"content1") + len(b"content2")
        assert size == expected_size

    def test_get_size_nonexistent(self, manager, temp_project):
        """存在しないパスのサイズ取得のテスト"""
        nonexistent_path = temp_project / "nonexistent"
        size = manager._get_size(nonexistent_path)
        assert size == 0

    def test_backup_manager_default_project_root(self):
        """デフォルトプロジェクトルートのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                # 一時ディレクトリに移動
                import os

                os.chdir(temp_dir)

                manager = BackupManager()
                assert manager.project_root.resolve() == Path(temp_dir).resolve()
            finally:
                # 元のディレクトリに戻る
                os.chdir(original_cwd)

    def test_backup_directory_creation(self, temp_project):
        """バックアップディレクトリの自動作成のテスト"""
        manager = BackupManager(temp_project)

        # バックアップディレクトリが自動作成されることを確認
        assert manager.backup_dir.exists()
        assert manager.backup_dir.is_dir()
        assert manager.backup_dir.name == "backups"
