"""
移行チェックポイント機能のテスト
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_repo.migration_checkpoint import (
    MigrationCheckpoint,
    MigrationError,
    handle_migration_error,
)


class TestMigrationCheckpoint:
    """MigrationCheckpointクラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 元のディレクトリを保存し、テスト用ディレクトリに移動
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.temp_dir)
        
        # ディレクトリ変更後にMigrationCheckpointを初期化
        self.checkpoint_manager = MigrationCheckpoint(Path("checkpoints"))

        # テスト用のソースディレクトリを作成
        self.test_src = Path("src")
        self.test_src.mkdir()
        (self.test_src / "test_file.py").write_text("# test content")

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import os

        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_create_checkpoint_success(self):
        """チェックポイント作成の成功テスト"""
        phase = "test_phase"
        description = "テストチェックポイント"

        checkpoint_id = self.checkpoint_manager.create_checkpoint(phase, description)

        # チェックポイントIDの形式確認
        assert checkpoint_id.startswith(f"{phase}_")
        assert len(checkpoint_id.split("_")) >= 3  # phase_YYYYMMDD_HHMMSS

        # チェックポイントディレクトリの存在確認
        checkpoint_path = self.checkpoint_manager.checkpoint_dir / checkpoint_id
        assert checkpoint_path.exists()

        # バックアップファイルの存在確認
        src_backup = checkpoint_path / "src"
        assert src_backup.exists()
        assert (src_backup / "test_file.py").exists()

        # メタデータの確認
        metadata = self.checkpoint_manager._load_metadata()
        assert checkpoint_id in metadata
        assert metadata[checkpoint_id]["phase"] == phase
        assert metadata[checkpoint_id]["description"] == description

    def test_create_checkpoint_without_src(self):
        """srcディレクトリが存在しない場合のチェックポイント作成"""
        # srcディレクトリを削除
        shutil.rmtree(self.test_src)

        checkpoint_id = self.checkpoint_manager.create_checkpoint("test_phase")

        # チェックポイントは作成されるが、srcバックアップは存在しない
        checkpoint_path = self.checkpoint_manager.checkpoint_dir / checkpoint_id
        assert checkpoint_path.exists()
        assert not (checkpoint_path / "src").exists()

    def test_rollback_to_checkpoint_success(self):
        """チェックポイントへのロールバック成功テスト"""
        # 初期チェックポイントを作成
        checkpoint_id = self.checkpoint_manager.create_checkpoint("initial", "初期状態")

        # ファイルを変更
        (self.test_src / "test_file.py").write_text("# modified content")
        (self.test_src / "new_file.py").write_text("# new file")

        # ロールバック実行
        self.checkpoint_manager.rollback_to_checkpoint(checkpoint_id)

        # ファイルが元の状態に戻っていることを確認
        assert (self.test_src / "test_file.py").read_text() == "# test content"
        assert not (self.test_src / "new_file.py").exists()

    def test_rollback_to_nonexistent_checkpoint(self):
        """存在しないチェックポイントへのロールバック"""
        with pytest.raises(MigrationError, match="チェックポイントが見つかりません"):
            self.checkpoint_manager.rollback_to_checkpoint("nonexistent_checkpoint")

    def test_list_checkpoints(self):
        """チェックポイント一覧取得テスト"""
        # 複数のチェックポイントを作成
        checkpoint1 = self.checkpoint_manager.create_checkpoint("phase1", "フェーズ1")
        checkpoint2 = self.checkpoint_manager.create_checkpoint("phase2", "フェーズ2")

        checkpoints = self.checkpoint_manager.list_checkpoints()

        assert len(checkpoints) == 2

        # 最新のものが最初に来ることを確認
        assert checkpoints[0]["id"] == checkpoint2
        assert checkpoints[1]["id"] == checkpoint1

        # 各チェックポイントの情報確認
        for checkpoint in checkpoints:
            assert "id" in checkpoint
            assert "phase" in checkpoint
            assert "description" in checkpoint
            assert "timestamp" in checkpoint
            assert "created_at" in checkpoint

    def test_cleanup_checkpoints(self):
        """チェックポイントクリーンアップテスト"""
        # 6個のチェックポイントを作成
        checkpoint_ids = []
        for i in range(6):
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                f"phase{i}", f"フェーズ{i}"
            )
            checkpoint_ids.append(checkpoint_id)

        # 最新3個を保持してクリーンアップ
        self.checkpoint_manager.cleanup_checkpoints(keep_latest=3)

        checkpoints = self.checkpoint_manager.list_checkpoints()
        assert len(checkpoints) == 3

        # 最新3個が残っていることを確認
        remaining_ids = [cp["id"] for cp in checkpoints]
        assert checkpoint_ids[-3:] == remaining_ids[::-1]  # 逆順で返される

    def test_get_checkpoint_info(self):
        """チェックポイント情報取得テスト"""
        phase = "test_phase"
        description = "テスト説明"
        checkpoint_id = self.checkpoint_manager.create_checkpoint(phase, description)

        info = self.checkpoint_manager.get_checkpoint_info(checkpoint_id)

        assert info is not None
        assert info["phase"] == phase
        assert info["description"] == description
        assert "timestamp" in info
        assert "created_at" in info
        assert "path" in info

    def test_get_nonexistent_checkpoint_info(self):
        """存在しないチェックポイント情報取得テスト"""
        info = self.checkpoint_manager.get_checkpoint_info("nonexistent")
        assert info is None

    @patch("shutil.copytree")
    def test_create_checkpoint_error_handling(self, mock_copytree):
        """チェックポイント作成エラーハンドリングテスト"""
        mock_copytree.side_effect = OSError("Permission denied")

        with pytest.raises(MigrationError, match="チェックポイント作成に失敗"):
            self.checkpoint_manager.create_checkpoint("test_phase")

    def test_metadata_file_corruption_handling(self):
        """メタデータファイル破損時のハンドリングテスト"""
        # 破損したメタデータファイルを作成
        self.checkpoint_manager.metadata_file.write_text("invalid json content")

        # メタデータ読み込みは空辞書を返すべき
        metadata = self.checkpoint_manager._load_metadata()
        assert metadata == {}

        # 新しいチェックポイント作成は正常に動作するべき
        checkpoint_id = self.checkpoint_manager.create_checkpoint("recovery_test")
        assert checkpoint_id is not None


class TestMigrationErrorHandling:
    """移行エラーハンドリング機能のテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.temp_dir)

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import os

        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("setup_repo.migration_checkpoint.MigrationCheckpoint")
    def test_handle_migration_error_success(self, mock_checkpoint_class):
        """移行エラーハンドリング成功テスト"""
        mock_checkpoint = MagicMock()
        mock_checkpoint_class.return_value = mock_checkpoint

        test_error = ValueError("テストエラー")
        rollback_point = "test_checkpoint"

        with pytest.raises(MigrationError, match="移行に失敗しました"):
            handle_migration_error(test_error, rollback_point)

        # ロールバックが呼び出されたことを確認
        mock_checkpoint.rollback_to_checkpoint.assert_called_once_with(rollback_point)

    @patch("setup_repo.migration_checkpoint.MigrationCheckpoint")
    def test_handle_migration_error_rollback_failure(self, mock_checkpoint_class):
        """ロールバック失敗時のエラーハンドリングテスト"""
        mock_checkpoint = MagicMock()
        mock_checkpoint.rollback_to_checkpoint.side_effect = Exception(
            "ロールバックエラー"
        )
        mock_checkpoint_class.return_value = mock_checkpoint

        test_error = ValueError("テストエラー")
        rollback_point = "test_checkpoint"

        with pytest.raises(MigrationError, match="移行失敗後のロールバックにも失敗"):
            handle_migration_error(test_error, rollback_point)


class TestMigrationCheckpointIntegration:
    """MigrationCheckpoint統合テスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 元のディレクトリを保存し、テスト用ディレクトリに移動
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.temp_dir)
        
        # ディレクトリ変更後にMigrationCheckpointを初期化
        self.checkpoint_manager = MigrationCheckpoint(Path("checkpoints"))

        # テスト用のプロジェクト構造を作成
        self.test_src = Path("src")
        self.test_src.mkdir()
        (self.test_src / "module1.py").write_text("# module1 original")
        (self.test_src / "module2.py").write_text("# module2 original")

        self.test_tests = Path("tests")
        self.test_tests.mkdir()
        (self.test_tests / "test_module1.py").write_text("# test1 original")

        Path("pyproject.toml").write_text("[tool.pytest]")

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import os

        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_full_migration_workflow(self):
        """完全な移行ワークフローテスト"""
        # Phase 1: 初期チェックポイント作成
        phase1_checkpoint = self.checkpoint_manager.create_checkpoint(
            "phase1_start", "Phase 1開始前の状態"
        )

        # Phase 1: ファイル変更をシミュレート
        (self.test_src / "module1.py").write_text("# module1 phase1 modified")
        (self.test_src / "new_module.py").write_text("# new module in phase1")

        # Phase 1完了チェックポイント
        phase1_complete = self.checkpoint_manager.create_checkpoint(
            "phase1_complete", "Phase 1完了"
        )

        # Phase 2: さらなる変更
        (self.test_src / "module2.py").write_text("# module2 phase2 modified")
        (self.test_tests / "test_new.py").write_text("# new test")

        # Phase 2完了チェックポイント
        self.checkpoint_manager.create_checkpoint("phase2_complete", "Phase 2完了")

        # チェックポイント一覧確認
        checkpoints = self.checkpoint_manager.list_checkpoints()
        assert len(checkpoints) == 3

        # Phase 1完了時点にロールバック
        self.checkpoint_manager.rollback_to_checkpoint(phase1_complete)

        # Phase 1完了時の状態が復元されていることを確認
        assert (self.test_src / "module1.py").read_text() == "# module1 phase1 modified"
        assert (self.test_src / "new_module.py").exists()
        assert (
            self.test_src / "module2.py"
        ).read_text() == "# module2 original"  # Phase 2の変更は戻る
        assert not (
            self.test_tests / "test_new.py"
        ).exists()  # Phase 2で追加されたファイルは削除

        # 初期状態にロールバック
        self.checkpoint_manager.rollback_to_checkpoint(phase1_checkpoint)

        # 初期状態が復元されていることを確認
        assert (self.test_src / "module1.py").read_text() == "# module1 original"
        assert not (self.test_src / "new_module.py").exists()
        assert (self.test_src / "module2.py").read_text() == "# module2 original"
