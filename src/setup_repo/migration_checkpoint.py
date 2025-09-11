"""
移行チェックポイント管理モジュール

リファクタリング過程での段階的移行とロールバック機能を提供します。
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """移行関連のエラー"""

    pass


class MigrationCheckpoint:
    """
    リファクタリング移行のチェックポイント管理クラス

    段階的移行とロールバック機能を提供します。
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """
        チェックポイント管理を初期化

        Args:
            checkpoint_dir: チェックポイント保存ディレクトリ
                （デフォルト: .migration_checkpoints）
        """
        if checkpoint_dir:
            # パストラバーサル攻撃を防ぐためのバリデーション
            current_dir = Path.cwd().resolve()

            # 相対パスで指定された場合は、現在のディレクトリからの相対パスとして処理
            if not checkpoint_dir.is_absolute():
                resolved_dir = (current_dir / checkpoint_dir).resolve()
            else:
                resolved_dir = checkpoint_dir.resolve()
                # 絶対パスの場合のみセキュリティチェックを実行
                try:
                    # 現在のディレクトリからの相対パスを計算
                    resolved_dir.relative_to(current_dir)
                except ValueError:
                    raise ValueError(
                        "チェックポイントディレクトリは現在のディレクトリ以下である必要があります"
                    ) from None

            self.checkpoint_dir = resolved_dir
        else:
            self.checkpoint_dir = Path(".migration_checkpoints").resolve()
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.metadata_file = self.checkpoint_dir / "metadata.json"

    def create_checkpoint(self, phase: str, description: str = "") -> str:
        """
        現在の状態のチェックポイントを作成

        Args:
            phase: フェーズ名（例: "phase1_duplicate_removal"）
            description: チェックポイントの説明

        Returns:
            作成されたチェックポイントID

        Raises:
            MigrationError: チェックポイント作成に失敗した場合
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_id = f"{phase}_{timestamp}"
            checkpoint_path = self.checkpoint_dir / checkpoint_id

            # ソースコードのバックアップを作成
            src_backup = checkpoint_path / "src"
            if Path("src").exists():
                checkpoint_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree("src", src_backup, dirs_exist_ok=True)

            # テストファイルのバックアップを作成
            tests_backup = checkpoint_path / "tests"
            if Path("tests").exists():
                checkpoint_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree("tests", tests_backup, dirs_exist_ok=True)

            # 設定ファイルのバックアップを作成
            checkpoint_path.mkdir(parents=True, exist_ok=True)
            config_files = ["pyproject.toml", "config.json.template"]
            for config_file in config_files:
                if Path(config_file).exists():
                    shutil.copy2(config_file, checkpoint_path / config_file)

            # メタデータを保存
            metadata = self._load_metadata()
            metadata[checkpoint_id] = {
                "phase": phase,
                "description": description,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "path": str(checkpoint_path),
            }
            self._save_metadata(metadata)

            logger.info(f"チェックポイント作成完了: {checkpoint_id}")
            return checkpoint_id

        except Exception as e:
            raise MigrationError(f"チェックポイント作成に失敗: {e}") from e

    def rollback_to_checkpoint(self, checkpoint_id: str) -> None:
        """
        指定されたチェックポイントにロールバック

        Args:
            checkpoint_id: ロールバック先のチェックポイントID

        Raises:
            MigrationError: ロールバックに失敗した場合
        """
        try:
            metadata = self._load_metadata()
            if checkpoint_id not in metadata:
                raise MigrationError(
                    f"チェックポイントが見つかりません: {checkpoint_id}"
                )

            checkpoint_path = Path(metadata[checkpoint_id]["path"])
            if not checkpoint_path.exists():
                raise MigrationError(
                    f"チェックポイントパスが存在しません: {checkpoint_path}"
                )

            # 現在の状態をバックアップ（ロールバック前）
            backup_id = f"pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.create_checkpoint(
                backup_id,
                f"ロールバック前のバックアップ（{checkpoint_id}へのロールバック）",
            )

            # ソースコードを復元
            src_backup = checkpoint_path / "src"
            if src_backup.exists():
                if Path("src").exists():
                    shutil.rmtree("src")
                shutil.copytree(src_backup, "src")

            # テストファイルを復元
            tests_backup = checkpoint_path / "tests"
            if tests_backup.exists():
                if Path("tests").exists():
                    shutil.rmtree("tests")
                shutil.copytree(tests_backup, "tests")

            # 設定ファイルを復元
            config_files = ["pyproject.toml", "config.json.template"]
            for config_file in config_files:
                backup_file = checkpoint_path / config_file
                if backup_file.exists():
                    shutil.copy2(backup_file, config_file)

            logger.info(f"ロールバック完了: {checkpoint_id}")

        except Exception as e:
            raise MigrationError(f"ロールバックに失敗: {e}") from e

    def list_checkpoints(self) -> list[dict[str, str]]:
        """
        利用可能なチェックポイントのリストを取得

        Returns:
            チェックポイント情報のリスト
        """
        metadata = self._load_metadata()
        checkpoints = []

        for checkpoint_id, info in metadata.items():
            checkpoints.append(
                {
                    "id": checkpoint_id,
                    "phase": info.get("phase", "unknown"),
                    "description": info.get("description", ""),
                    "timestamp": info.get("timestamp", ""),
                    "created_at": info.get("created_at", ""),
                }
            )

        # タイムスタンプでソート
        checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
        return checkpoints

    def cleanup_checkpoints(self, keep_latest: int = 5) -> None:
        """
        古いチェックポイントをクリーンアップ

        Args:
            keep_latest: 保持する最新チェックポイント数
        """
        try:
            checkpoints = self.list_checkpoints()
            if len(checkpoints) <= keep_latest:
                return

            metadata = self._load_metadata()
            checkpoints_to_remove = checkpoints[keep_latest:]

            for checkpoint in checkpoints_to_remove:
                checkpoint_id = checkpoint["id"]
                checkpoint_path = Path(metadata[checkpoint_id]["path"])

                if checkpoint_path.exists():
                    shutil.rmtree(checkpoint_path)

                del metadata[checkpoint_id]
                logger.info(f"チェックポイント削除: {checkpoint_id}")

            self._save_metadata(metadata)
            logger.info(
                f"チェックポイントクリーンアップ完了: "
                f"{len(checkpoints_to_remove)}個削除"
            )

        except Exception as e:
            logger.error(f"チェックポイントクリーンアップに失敗: {e}")

    def get_checkpoint_info(self, checkpoint_id: str) -> Optional[dict[str, str]]:
        """
        指定されたチェックポイントの詳細情報を取得

        Args:
            checkpoint_id: チェックポイントID

        Returns:
            チェックポイント情報（存在しない場合はNone）
        """
        metadata = self._load_metadata()
        return metadata.get(checkpoint_id)

    def _load_metadata(self) -> dict[str, dict[str, str]]:
        """メタデータファイルを読み込み"""
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"メタデータファイル読み込みエラー: {e}")
            return {}

    def _save_metadata(self, metadata: dict[str, dict[str, str]]) -> None:
        """メタデータファイルを保存"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise MigrationError(f"メタデータファイル保存に失敗: {e}") from e


def handle_migration_error(error: Exception, rollback_point: str) -> None:
    """
    移行エラー時のロールバック処理

    Args:
        error: 発生したエラー
        rollback_point: ロールバック先のチェックポイントID

    Raises:
        MigrationError: ロールバック処理を含む移行エラー
    """
    logger.error(f"Migration failed: {error}")

    try:
        checkpoint_manager = MigrationCheckpoint()
        checkpoint_manager.rollback_to_checkpoint(rollback_point)
        logger.info(f"ロールバック完了: {rollback_point}")
    except Exception as rollback_error:
        logger.error(f"ロールバックにも失敗: {rollback_error}")
        raise MigrationError(
            f"移行失敗後のロールバックにも失敗: {error} -> {rollback_error}"
        ) from error

    raise MigrationError(f"移行に失敗しました: {error}") from error
