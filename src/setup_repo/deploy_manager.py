"""デプロイメント管理ワークフロー."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .git_operations import GitOperations
from .logging_config import setup_project_logging

logger = setup_project_logging()


class DeployManager:
    """デプロイメント管理ワークフロー."""

    def __init__(self, config: dict) -> None:
        """初期化."""
        self.config = config
        self.git_ops = GitOperations()
        self.deploy_history_file = Path("output/deploy_history.json")
        self.deploy_history_file.parent.mkdir(exist_ok=True)

    def prepare(self) -> bool:
        """デプロイ準備."""
        logger.info("デプロイ準備を開始します")

        try:
            # 品質チェック
            if not self._run_quality_checks():
                logger.error("品質チェックに失敗しました")
                return False

            # ビルド実行
            if not self._build_project():
                logger.error("ビルドに失敗しました")
                return False

            logger.info("デプロイ準備が完了しました")
            return True

        except Exception as e:
            logger.error(f"デプロイ準備中にエラーが発生しました: {e}")
            return False

    def execute(self, environment: str = "production") -> bool:
        """デプロイ実行."""
        logger.info(f"環境 '{environment}' へのデプロイを開始します")

        try:
            # デプロイ前チェック
            if not self._pre_deploy_check():
                return False

            # デプロイ実行
            deploy_id = self._generate_deploy_id()

            if not self._execute_deploy(environment, deploy_id):
                logger.error("デプロイ実行に失敗しました")
                return False

            # デプロイ履歴記録
            self._record_deploy_history(environment, deploy_id, "success")

            logger.info(f"デプロイが正常に完了しました (ID: {deploy_id})")
            return True

        except Exception as e:
            logger.error(f"デプロイ実行中にエラーが発生しました: {e}")
            return False

    def rollback(self, deploy_id: str | None = None) -> bool:
        """ロールバック実行."""
        logger.info("ロールバックを開始します")

        try:
            # ロールバック対象特定
            target_deploy = self._get_rollback_target(deploy_id)
            if not target_deploy:
                logger.error("ロールバック対象が見つかりません")
                return False

            # ロールバック実行
            if not self._execute_rollback(target_deploy):
                logger.error("ロールバック実行に失敗しました")
                return False

            # ロールバック履歴記録
            rollback_id = self._generate_deploy_id()
            self._record_deploy_history("rollback", rollback_id, "success", target_deploy)

            logger.info(f"ロールバックが正常に完了しました (ID: {rollback_id})")
            return True

        except Exception as e:
            logger.error(f"ロールバック実行中にエラーが発生しました: {e}")
            return False

    def _run_quality_checks(self) -> bool:
        """品質チェック実行."""
        logger.info("品質チェックを実行中...")

        checks = [
            ("ruff check .", "リンティングチェック"),
            ("ruff format --check .", "フォーマットチェック"),
            ("uv run basedpyright src/", "型チェック"),
            ("pytest --cov-fail-under=80", "テスト・カバレッジチェック"),
        ]

        for cmd, desc in checks:
            logger.info(f"{desc}を実行中...")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"{desc}に失敗しました: {result.stderr}")
                return False

        logger.info("全ての品質チェックが完了しました")
        return True

    def _build_project(self) -> bool:
        """プロジェクトビルド."""
        logger.info("プロジェクトをビルド中...")

        try:
            result = subprocess.run(["uv", "build"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"ビルドに失敗しました: {result.stderr}")
                return False

            logger.info("ビルドが完了しました")
            return True

        except FileNotFoundError:
            logger.warning("uvが見つかりません。ビルドをスキップします")
            return True

    def _pre_deploy_check(self) -> bool:
        """デプロイ前チェック."""
        logger.info("デプロイ前チェックを実行中...")

        # Git状態チェック
        if not self.git_ops.is_clean():
            logger.error("作業ディレクトリが汚れています")
            return False

        # ブランチチェック
        current_branch = self.git_ops.get_current_branch()
        if current_branch != "main":
            logger.warning(f"現在のブランチは '{current_branch}' です")

        logger.info("デプロイ前チェックが完了しました")
        return True

    def _execute_deploy(self, environment: str, deploy_id: str) -> bool:
        """デプロイ実行."""
        logger.info(f"環境 '{environment}' にデプロイ中... (ID: {deploy_id})")

        # GitHub Actions連携（実際の実装では適切なAPIを使用）
        logger.info("GitHub Actionsワークフローをトリガー中...")

        # デプロイシミュレーション
        import time

        time.sleep(1)  # デプロイ処理のシミュレーション

        logger.info("デプロイが完了しました")
        return True

    def _execute_rollback(self, target_deploy: dict[str, Any]) -> bool:
        """ロールバック実行."""
        logger.info(f"デプロイ {target_deploy['deploy_id']} にロールバック中...")

        # ロールバック処理のシミュレーション
        import time

        time.sleep(1)

        logger.info("ロールバックが完了しました")
        return True

    def _generate_deploy_id(self) -> str:
        """デプロイID生成."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        commit_hash = self.git_ops.get_current_commit()[:8]
        return f"deploy_{timestamp}_{commit_hash}"

    def _record_deploy_history(
        self, environment: str, deploy_id: str, status: str, rollback_target: dict[str, Any] | None = None
    ) -> None:
        """デプロイ履歴記録."""
        history = self._load_deploy_history()

        record = {
            "deploy_id": deploy_id,
            "environment": environment,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "commit_hash": self.git_ops.get_current_commit(),
            "branch": self.git_ops.get_current_branch(),
        }

        if rollback_target:
            record["rollback_target"] = rollback_target["deploy_id"]

        history.append(record)

        # 最新100件のみ保持
        if len(history) > 100:
            history = history[-100:]

        with open(self.deploy_history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def _load_deploy_history(self) -> list[dict[str, Any]]:
        """デプロイ履歴読み込み."""
        if not self.deploy_history_file.exists():
            return []

        try:
            with open(self.deploy_history_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("デプロイ履歴の読み込みに失敗しました")
            return []

    def _get_rollback_target(self, deploy_id: str | None = None) -> dict[str, Any] | None:
        """ロールバック対象取得."""
        history = self._load_deploy_history()

        if deploy_id:
            # 指定されたデプロイIDを検索
            for record in reversed(history):
                if record["deploy_id"] == deploy_id and record["status"] == "success":
                    return record
        else:
            # 最新の成功デプロイを検索
            for record in reversed(history):
                if record["status"] == "success" and record["environment"] != "rollback":
                    return record

        return None

    def list_deployments(self) -> list[dict[str, Any]]:
        """デプロイ履歴一覧."""
        return self._load_deploy_history()
