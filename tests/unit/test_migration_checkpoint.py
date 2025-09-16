"""マイグレーション機能のテスト"""

import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.migration_checkpoint import MigrationCheckpoint, MigrationError, handle_migration_error

from ..multiplatform.helpers import verify_current_platform


class TestMigrationCheckpoint:
    """MigrationCheckpointのテストクラス"""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """テスト用ワークスペース"""
        # テスト用のソースディレクトリを作成
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_module.py").write_text("# Test module", encoding="utf-8")

        # テスト用のテストディレクトリを作成
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text("# Test file", encoding="utf-8")

        # テスト用の設定ファイルを作成
        (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (tmp_path / "config.json.template").write_text("{}", encoding="utf-8")

        return tmp_path

    @pytest.fixture
    def migration_checkpoint(self, temp_workspace):
        """MigrationCheckpointインスタンス"""
        # 作業ディレクトリを変更
        original_cwd = Path.cwd()
        import os

        os.chdir(temp_workspace)

        checkpoint_dir = temp_workspace / ".migration_checkpoints"
        checkpoint = MigrationCheckpoint(checkpoint_dir)

        yield checkpoint

        # 作業ディレクトリを復元
        os.chdir(original_cwd)

    @pytest.mark.unit
    def test_init_default_dir(self, temp_workspace):
        """デフォルトディレクトリでの初期化"""
        verify_current_platform()  # プラットフォーム検証

        import os

        original_cwd = Path.cwd()
        os.chdir(temp_workspace)

        try:
            checkpoint = MigrationCheckpoint()

            expected_dir = temp_workspace / ".migration_checkpoints"
            assert checkpoint.checkpoint_dir == expected_dir.resolve()
            assert checkpoint.checkpoint_dir.exists()
            assert checkpoint.metadata_file == expected_dir / "metadata.json"
        finally:
            os.chdir(original_cwd)

    @pytest.mark.unit
    def test_init_custom_dir(self, temp_workspace):
        """カスタムディレクトリでの初期化"""
        verify_current_platform()  # プラットフォーム検証

        import os

        original_cwd = Path.cwd()
        os.chdir(temp_workspace)

        try:
            custom_dir = temp_workspace / "custom_checkpoints"
            checkpoint = MigrationCheckpoint(custom_dir)

            assert checkpoint.checkpoint_dir == custom_dir.resolve()
            assert checkpoint.checkpoint_dir.exists()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.unit
    def test_init_security_validation(self, temp_workspace):
        """セキュリティバリデーションテスト"""
        verify_current_platform()  # プラットフォーム検証

        import os
        import platform

        original_cwd = Path.cwd()
        os.chdir(temp_workspace)

        try:
            # パストラバーサル攻撃を試行（Windowsでは存在しないパスを使用）
            invalid_path = Path("C:/etc/passwd") if platform.system() == "Windows" else Path("/etc/passwd")
            with pytest.raises((ValueError, FileNotFoundError)):
                MigrationCheckpoint(invalid_path)
        finally:
            os.chdir(original_cwd)

    @pytest.mark.unit
    def test_create_checkpoint_success(self, migration_checkpoint):
        """チェックポイント作成成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        phase = "test_phase"
        description = "Test checkpoint"

        checkpoint_id = migration_checkpoint.create_checkpoint(phase, description)

        assert checkpoint_id.startswith(f"{phase}_")
        assert len(checkpoint_id.split("_")) >= 3  # phase_YYYYMMDD_HHMMSS

        # メタデータが保存されていることを確認
        metadata = migration_checkpoint._load_metadata()
        assert checkpoint_id in metadata
        assert metadata[checkpoint_id]["phase"] == phase
        assert metadata[checkpoint_id]["description"] == description

    @pytest.mark.unit
    def test_create_checkpoint_with_files(self, migration_checkpoint):
        """ファイル付きチェックポイント作成テスト"""
        verify_current_platform()  # プラットフォーム検証

        checkpoint_id = migration_checkpoint.create_checkpoint("test_phase")

        # チェックポイントディレクトリが作成されていることを確認
        checkpoint_path = migration_checkpoint.checkpoint_dir / checkpoint_id
        assert checkpoint_path.exists()

        # バックアップファイルが作成されていることを確認
        assert (checkpoint_path / "src").exists()
        assert (checkpoint_path / "tests").exists()
        assert (checkpoint_path / "pyproject.toml").exists()
        assert (checkpoint_path / "config.json.template").exists()

    @pytest.mark.unit
    def test_create_checkpoint_no_source_files(self, tmp_path):
        """ソースファイルがない場合のチェックポイント作成"""
        verify_current_platform()  # プラットフォーム検証

        import os

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            checkpoint = MigrationCheckpoint()
            checkpoint_id = checkpoint.create_checkpoint("empty_phase")

            # チェックポイントは作成されるが、ファイルバックアップはない
            checkpoint_path = checkpoint.checkpoint_dir / checkpoint_id
            assert checkpoint_path.exists()
            assert not (checkpoint_path / "src").exists()
            assert not (checkpoint_path / "tests").exists()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.unit
    def test_rollback_to_checkpoint_success(self, migration_checkpoint):
        """ロールバック成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 初期チェックポイントを作成
        checkpoint_id = migration_checkpoint.create_checkpoint("initial")

        # ファイルを変更
        Path("src/test_module.py").write_text("# Modified content", encoding="utf-8")

        # ロールバック実行
        migration_checkpoint.rollback_to_checkpoint(checkpoint_id)

        # ファイルが復元されていることを確認
        content = Path("src/test_module.py").read_text(encoding="utf-8")
        assert content == "# Test module"

    @pytest.mark.unit
    def test_rollback_to_nonexistent_checkpoint(self, migration_checkpoint):
        """存在しないチェックポイントへのロールバック"""
        verify_current_platform()  # プラットフォーム検証

        with pytest.raises(MigrationError, match="チェックポイントが見つかりません"):
            migration_checkpoint.rollback_to_checkpoint("nonexistent")

    @pytest.mark.unit
    def test_rollback_creates_backup(self, migration_checkpoint):
        """ロールバック時のバックアップ作成テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 初期チェックポイントを作成
        checkpoint_id = migration_checkpoint.create_checkpoint("initial")

        # ファイルを変更
        Path("src/test_module.py").write_text("# Modified content", encoding="utf-8")

        # ロールバック実行
        migration_checkpoint.rollback_to_checkpoint(checkpoint_id)

        # バックアップチェックポイントが作成されていることを確認
        checkpoints = migration_checkpoint.list_checkpoints()
        backup_checkpoints = [cp for cp in checkpoints if cp["id"].startswith("pre_rollback_")]
        assert len(backup_checkpoints) > 0

    @pytest.mark.unit
    def test_list_checkpoints_empty(self, migration_checkpoint):
        """空のチェックポイントリスト"""
        verify_current_platform()  # プラットフォーム検証

        checkpoints = migration_checkpoint.list_checkpoints()
        assert checkpoints == []

    @pytest.mark.unit
    def test_list_checkpoints_with_data(self, migration_checkpoint):
        """データありのチェックポイントリスト"""
        verify_current_platform()  # プラットフォーム検証

        # 複数のチェックポイントを作成
        checkpoint1 = migration_checkpoint.create_checkpoint("phase1", "First checkpoint")
        checkpoint2 = migration_checkpoint.create_checkpoint("phase2", "Second checkpoint")

        checkpoints = migration_checkpoint.list_checkpoints()

        assert len(checkpoints) == 2
        # 新しい順にソートされていることを確認
        assert checkpoints[0]["id"] == checkpoint2
        assert checkpoints[1]["id"] == checkpoint1

    @pytest.mark.unit
    def test_cleanup_checkpoints_keep_latest(self, migration_checkpoint):
        """最新チェックポイント保持テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 複数のチェックポイントを作成
        checkpoints = []
        for i in range(7):
            checkpoint_id = migration_checkpoint.create_checkpoint(f"phase{i}")
            checkpoints.append(checkpoint_id)

        # 最新5個を保持してクリーンアップ
        migration_checkpoint.cleanup_checkpoints(keep_latest=5)

        remaining_checkpoints = migration_checkpoint.list_checkpoints()
        assert len(remaining_checkpoints) == 5

        # 最新の5個が残っていることを確認
        remaining_ids = [cp["id"] for cp in remaining_checkpoints]
        expected_ids = sorted(checkpoints[-5:], reverse=True)  # 作成順の最新5個を降順ソート
        actual_ids = sorted(remaining_ids, reverse=True)  # 実際の残存IDを降順ソート
        assert expected_ids == actual_ids  # ソート済みリストで比較

    @pytest.mark.unit
    def test_cleanup_checkpoints_no_cleanup_needed(self, migration_checkpoint):
        """クリーンアップ不要な場合"""
        verify_current_platform()  # プラットフォーム検証

        # 3個のチェックポイントを作成
        for i in range(3):
            migration_checkpoint.create_checkpoint(f"phase{i}")

        # 5個保持でクリーンアップ（何も削除されない）
        migration_checkpoint.cleanup_checkpoints(keep_latest=5)

        checkpoints = migration_checkpoint.list_checkpoints()
        assert len(checkpoints) == 3

    @pytest.mark.unit
    def test_get_checkpoint_info_exists(self, migration_checkpoint):
        """存在するチェックポイント情報取得"""
        verify_current_platform()  # プラットフォーム検証

        checkpoint_id = migration_checkpoint.create_checkpoint("test_phase", "Test description")

        info = migration_checkpoint.get_checkpoint_info(checkpoint_id)

        assert info is not None
        assert info["phase"] == "test_phase"
        assert info["description"] == "Test description"

    @pytest.mark.unit
    def test_get_checkpoint_info_not_exists(self, migration_checkpoint):
        """存在しないチェックポイント情報取得"""
        verify_current_platform()  # プラットフォーム検証

        info = migration_checkpoint.get_checkpoint_info("nonexistent")
        assert info is None

    @pytest.mark.unit
    def test_load_metadata_file_not_exists(self, migration_checkpoint):
        """メタデータファイルが存在しない場合"""
        verify_current_platform()  # プラットフォーム検証

        metadata = migration_checkpoint._load_metadata()
        assert metadata == {}

    @pytest.mark.unit
    def test_load_metadata_invalid_json(self, migration_checkpoint):
        """無効なJSONメタデータファイル"""
        verify_current_platform()  # プラットフォーム検証

        # 無効なJSONを書き込み
        migration_checkpoint.metadata_file.write_text("invalid json", encoding="utf-8")

        metadata = migration_checkpoint._load_metadata()
        assert metadata == {}

    @pytest.mark.unit
    def test_save_metadata_success(self, migration_checkpoint):
        """メタデータ保存成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        test_metadata = {
            "test_checkpoint": {"phase": "test", "description": "Test checkpoint", "timestamp": "20240101_120000"}
        }

        migration_checkpoint._save_metadata(test_metadata)

        # ファイルが作成されていることを確認
        assert migration_checkpoint.metadata_file.exists()

        # 内容が正しく保存されていることを確認
        loaded_metadata = migration_checkpoint._load_metadata()
        assert loaded_metadata == test_metadata

    @pytest.mark.unit
    def test_save_metadata_permission_error(self, migration_checkpoint):
        """メタデータ保存権限エラー"""
        verify_current_platform()  # プラットフォーム検証

        with (
            patch("builtins.open", side_effect=OSError("Permission denied")),
            pytest.raises(MigrationError, match="メタデータファイル保存に失敗"),
        ):
            migration_checkpoint._save_metadata({})

    @pytest.mark.unit
    def test_create_checkpoint_error_handling(self, migration_checkpoint):
        """チェックポイント作成エラーハンドリング"""
        verify_current_platform()  # プラットフォーム検証

        with (
            patch("shutil.copytree", side_effect=OSError("Copy failed")),
            pytest.raises(MigrationError, match="チェックポイント作成に失敗"),
        ):
            migration_checkpoint.create_checkpoint("error_phase")

    @pytest.mark.unit
    def test_rollback_error_handling(self, migration_checkpoint):
        """ロールバックエラーハンドリング"""
        verify_current_platform()  # プラットフォーム検証

        # 存在するチェックポイントを作成
        checkpoint_id = migration_checkpoint.create_checkpoint("test_phase")

        # チェックポイントディレクトリを削除してエラーを発生させる
        checkpoint_path = migration_checkpoint.checkpoint_dir / checkpoint_id
        shutil.rmtree(checkpoint_path)

        with pytest.raises(MigrationError, match="チェックポイントパスが存在しません"):
            migration_checkpoint.rollback_to_checkpoint(checkpoint_id)


class TestHandleMigrationError:
    """handle_migration_error関数のテスト"""

    @pytest.mark.unit
    @patch("src.setup_repo.migration_checkpoint.MigrationCheckpoint")
    def test_handle_migration_error_success_rollback(self, mock_checkpoint_class):
        """移行エラー処理（ロールバック成功）"""
        verify_current_platform()  # プラットフォーム検証

        mock_checkpoint = Mock()
        mock_checkpoint_class.return_value = mock_checkpoint

        test_error = Exception("Test migration error")
        rollback_point = "test_checkpoint"

        with pytest.raises(MigrationError, match="移行に失敗しました"):
            handle_migration_error(test_error, rollback_point)

        mock_checkpoint.rollback_to_checkpoint.assert_called_once_with(rollback_point)

    @pytest.mark.unit
    @patch("src.setup_repo.migration_checkpoint.MigrationCheckpoint")
    def test_handle_migration_error_rollback_failure(self, mock_checkpoint_class):
        """移行エラー処理（ロールバック失敗）"""
        verify_current_platform()  # プラットフォーム検証

        mock_checkpoint = Mock()
        mock_checkpoint.rollback_to_checkpoint.side_effect = Exception("Rollback failed")
        mock_checkpoint_class.return_value = mock_checkpoint

        test_error = Exception("Test migration error")
        rollback_point = "test_checkpoint"

        with pytest.raises(MigrationError, match="移行失敗後のロールバックにも失敗"):
            handle_migration_error(test_error, rollback_point)


class TestMigrationIntegration:
    """マイグレーション統合テスト"""

    @pytest.mark.unit
    def test_full_migration_workflow(self, tmp_path):
        """完全なマイグレーションワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        import os

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # 初期ファイルを作成
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            original_file = src_dir / "module.py"
            original_file.write_text("# Original content", encoding="utf-8")

            # マイグレーション管理を初期化
            checkpoint = MigrationCheckpoint()

            # Phase 1: 初期チェックポイント作成
            phase1_id = checkpoint.create_checkpoint("phase1", "Initial state")

            # ファイルを変更
            original_file.write_text("# Phase 1 changes", encoding="utf-8")

            # Phase 2: 変更後のチェックポイント作成
            checkpoint.create_checkpoint("phase2", "After phase 1 changes")

            # さらにファイルを変更
            original_file.write_text("# Phase 2 changes", encoding="utf-8")

            # Phase 1にロールバック
            checkpoint.rollback_to_checkpoint(phase1_id)

            # ファイルが初期状態に戻っていることを確認
            content = original_file.read_text(encoding="utf-8")
            assert content == "# Original content"

            # チェックポイントリストを確認
            checkpoints = checkpoint.list_checkpoints()
            assert len(checkpoints) >= 3  # phase1, phase2, pre_rollback_*

        finally:
            os.chdir(original_cwd)

    @pytest.mark.unit
    def test_concurrent_checkpoint_creation(self, tmp_path):
        """並行チェックポイント作成テスト"""
        verify_current_platform()  # プラットフォーム検証

        import os

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # 基本ファイル構造を作成
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            (src_dir / "module.py").write_text("# Content", encoding="utf-8")

            checkpoint = MigrationCheckpoint()

            # 短時間で複数のチェックポイントを作成
            checkpoint_ids = []
            for i in range(3):
                checkpoint_id = checkpoint.create_checkpoint(f"concurrent_{i}")
                checkpoint_ids.append(checkpoint_id)

            # すべてのチェックポイントが作成されていることを確認
            checkpoints = checkpoint.list_checkpoints()
            assert len(checkpoints) == 3

            # すべてのチェックポイントIDがユニークであることを確認
            ids = [cp["id"] for cp in checkpoints]
            assert len(set(ids)) == len(ids)

        finally:
            os.chdir(original_cwd)
