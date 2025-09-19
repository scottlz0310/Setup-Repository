"""マイグレーション管理モジュール"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .logging_config import setup_project_logging
from .security_helpers import safe_path_join

logger = setup_project_logging()


class MigrationManager:
    """マイグレーション管理クラス"""

    def __init__(self, project_root: Path):
        """初期化"""
        self.project_root = project_root
        self.migrations_dir = safe_path_join(project_root, ".migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        self.version_file = safe_path_join(self.migrations_dir, "version.json")

    def check_migration_needed(self) -> dict[str, Any]:
        """マイグレーション必要性チェック"""
        logger.info("マイグレーション必要性をチェック中...")

        current_version = self._get_current_version()
        target_version = self._get_target_version()

        migration_needed = current_version != target_version

        result = {
            "migration_needed": migration_needed,
            "current_version": current_version,
            "target_version": target_version,
            "timestamp": datetime.now().isoformat(),
            "changes": [],
        }

        if migration_needed:
            result["changes"] = self._detect_changes(current_version, target_version)
            logger.warning(f"マイグレーションが必要です: {current_version} -> {target_version}")
        else:
            logger.info("マイグレーションは不要です")

        return result

    def run_migration(self, backup: bool = True) -> dict[str, Any]:
        """マイグレーション実行"""
        logger.info("マイグレーションを開始...")

        check_result = self.check_migration_needed()
        if not check_result["migration_needed"]:
            return {"success": True, "message": "マイグレーションは不要です"}

        # バックアップ作成
        backup_path = None
        if backup:
            backup_path = self._create_migration_backup()
            logger.info(f"バックアップを作成: {backup_path}")

        try:
            # マイグレーション実行
            migration_result = self._execute_migration(check_result["current_version"], check_result["target_version"])

            # バージョン更新
            self._update_version(check_result["target_version"])

            logger.info("マイグレーションが完了しました")
            return {
                "success": True,
                "message": "マイグレーションが完了しました",
                "backup_path": str(backup_path) if backup_path else None,
                "migration_result": migration_result,
            }

        except Exception as e:
            logger.error(f"マイグレーション失敗: {e}")
            if backup_path:
                logger.info("バックアップからの復元を検討してください")
            return {"success": False, "error": str(e), "backup_path": str(backup_path) if backup_path else None}

    def rollback_migration(self, backup_name: str | None = None) -> dict[str, Any]:
        """マイグレーションロールバック"""
        logger.info("マイグレーションロールバックを開始...")

        try:
            # 最新のバックアップを使用
            if not backup_name:
                backups = self._list_migration_backups()
                if not backups:
                    return {"success": False, "error": "利用可能なバックアップがありません"}
                backup_name = backups[0]["name"]

            # バックアップから復元
            backup_dir = safe_path_join(self.migrations_dir, "backups")
            backup_path = safe_path_join(backup_dir, f"{backup_name}.tar.gz")
            if not backup_path.exists():
                return {"success": False, "error": f"バックアップが見つかりません: {backup_name}"}

            self._restore_from_backup(backup_path)

            logger.info("ロールバックが完了しました")
            return {"success": True, "message": f"バックアップ '{backup_name}' からロールバックしました"}

        except Exception as e:
            logger.error(f"ロールバック失敗: {e}")
            return {"success": False, "error": str(e)}

    def _get_current_version(self) -> str:
        """現在のバージョンを取得"""
        if not self.version_file.exists():
            return "0.0.0"

        try:
            with open(self.version_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
        except Exception:
            return "0.0.0"

    def _get_target_version(self) -> str:
        """ターゲットバージョンを取得"""
        # pyproject.tomlからバージョンを読み取り
        pyproject_file = safe_path_join(self.project_root, "pyproject.toml")
        if pyproject_file.exists():
            try:
                # Python 3.11+のtomllibを使用
                import tomllib

                with open(pyproject_file, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "1.0.0")
            except (ImportError, Exception):
                # フォールバック: シンプルな正規表現でバージョンを抽出
                try:
                    import re

                    content = pyproject_file.read_text(encoding="utf-8")
                    # version = "1.2.0" の形式を検索
                    pattern = r'version\s*=\s*["\']([^"\']+)["\']'
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
                except Exception:
                    # フォールバック処理: 正規表現パーシング失敗時はデフォルトバージョンを使用
                    pass  # nosec B110

        return "1.0.0"

    def _detect_changes(self, current: str, target: str) -> list[dict[str, Any]]:
        """バージョン間の変更を検出"""
        changes = []

        # 設定ファイル形式の変更チェック
        config_changes = self._check_config_changes()
        if config_changes:
            changes.extend(config_changes)

        # データ構造の変更チェック
        data_changes = self._check_data_structure_changes()
        if data_changes:
            changes.extend(data_changes)

        return changes

    def _check_config_changes(self) -> list[dict[str, Any]]:
        """設定ファイルの変更をチェック"""
        changes = []

        # config.json.templateの変更チェック
        template_file = safe_path_join(self.project_root, "config.json.template")
        if template_file.exists():
            # 新しい設定項目の検出
            try:
                with open(template_file, encoding="utf-8") as f:
                    template_config = json.load(f)

                local_config_file = safe_path_join(self.project_root, "config.local.json")
                if local_config_file.exists():
                    with open(local_config_file, encoding="utf-8") as f:
                        local_config = json.load(f)

                    # 新しいキーの検出
                    new_keys = set(template_config.keys()) - set(local_config.keys())
                    if new_keys:
                        changes.append(
                            {
                                "type": "config_update",
                                "description": f"新しい設定項目: {', '.join(new_keys)}",
                                "action": "merge_config",
                                "data": {"new_keys": list(new_keys)},
                            }
                        )
            except Exception as e:
                logger.warning(f"設定ファイルチェック失敗: {e}")

        return changes

    def _check_data_structure_changes(self) -> list[dict[str, Any]]:
        """データ構造の変更をチェック"""
        changes = []

        # 品質トレンドデータの構造変更チェック
        trend_file = safe_path_join(self.project_root, "output/quality-trends/trend-data.json")
        if trend_file.exists():
            try:
                with open(trend_file, encoding="utf-8") as f:
                    data = json.load(f)

                # データ構造の検証
                if isinstance(data, list) and data:
                    sample = data[0]
                    required_fields = ["timestamp", "quality_score", "test_coverage"]
                    missing_fields = [field for field in required_fields if field not in sample]

                    if missing_fields:
                        changes.append(
                            {
                                "type": "data_structure_update",
                                "description": f"品質トレンドデータの構造更新が必要: {', '.join(missing_fields)}",
                                "action": "update_trend_data",
                                "data": {"missing_fields": missing_fields},
                            }
                        )
            except Exception as e:
                logger.warning(f"データ構造チェック失敗: {e}")

        return changes

    def _execute_migration(self, current_version: str, target_version: str) -> dict[str, Any]:
        """マイグレーション実行"""
        results = []

        # 設定ファイルのマイグレーション
        config_result = self._migrate_config_files()
        if config_result:
            results.append(config_result)

        # データ構造のマイグレーション
        data_result = self._migrate_data_structures()
        if data_result:
            results.append(data_result)

        return {"migrations": results}

    def _migrate_config_files(self) -> dict[str, Any] | None:
        """設定ファイルのマイグレーション"""
        template_file = safe_path_join(self.project_root, "config.json.template")
        local_config_file = safe_path_join(self.project_root, "config.local.json")

        if not template_file.exists() or not local_config_file.exists():
            return None

        try:
            with open(template_file, encoding="utf-8") as f:
                template_config = json.load(f)

            with open(local_config_file, encoding="utf-8") as f:
                local_config = json.load(f)

            # 新しいキーをマージ
            updated = False
            for key, value in template_config.items():
                if key not in local_config:
                    local_config[key] = value
                    updated = True

            if updated:
                # バックアップ作成
                backup_file = safe_path_join(
                    self.project_root, f"config.local.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.copy2(local_config_file, backup_file)

                # 更新されたファイルを保存
                with open(local_config_file, "w", encoding="utf-8") as f:
                    json.dump(local_config, f, indent=2, ensure_ascii=False)

                return {
                    "type": "config_migration",
                    "description": "設定ファイルを更新しました",
                    "backup_file": str(backup_file),
                }

        except Exception as e:
            logger.error(f"設定ファイルマイグレーション失敗: {e}")
            raise

        return None

    def _migrate_data_structures(self) -> dict[str, Any] | None:
        """データ構造のマイグレーション"""
        # 品質トレンドデータの更新
        trend_file = safe_path_join(self.project_root, "output/quality-trends/trend-data.json")
        if not trend_file.exists():
            return None

        try:
            with open(trend_file, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list) or not data:
                return None

            # データ構造の更新
            updated = False
            for item in data:
                # 必要なフィールドの追加
                if "quality_score" not in item and "score" in item:
                    item["quality_score"] = item["score"]
                    updated = True

                if "test_coverage" not in item and "coverage" in item:
                    item["test_coverage"] = item["coverage"]
                    updated = True

            if updated:
                # バックアップ作成
                backup_file = safe_path_join(
                    trend_file.parent, f"trend-data.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.copy2(trend_file, backup_file)

                # 更新されたデータを保存
                with open(trend_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return {
                    "type": "data_migration",
                    "description": "品質トレンドデータを更新しました",
                    "backup_file": str(backup_file),
                }

        except Exception as e:
            logger.error(f"データ構造マイグレーション失敗: {e}")
            raise

        return None

    def _create_migration_backup(self) -> Path:
        """マイグレーション用バックアップ作成"""
        import tarfile

        backup_dir = safe_path_join(self.migrations_dir, "backups")
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"migration_backup_{timestamp}"
        backup_path = safe_path_join(backup_dir, f"{backup_name}.tar.gz")

        with tarfile.open(backup_path, "w:gz") as tar:
            # 設定ファイル
            config_files = ["config.local.json", "pyproject.toml"]
            for config_file in config_files:
                file_path = safe_path_join(self.project_root, config_file)
                if file_path.exists():
                    tar.add(file_path, arcname=config_file)

            # 品質データ
            output_dir = safe_path_join(self.project_root, "output")
            if output_dir.exists():
                tar.add(output_dir, arcname="output")

        # メタデータ保存
        metadata = {
            "name": backup_name,
            "timestamp": datetime.now().isoformat(),
            "version": self._get_current_version(),
            "files_backed_up": config_files + ["output/"],
        }

        metadata_file = safe_path_join(backup_dir, f"{backup_name}.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return backup_path

    def _restore_from_backup(self, backup_path: Path) -> None:
        """バックアップから復元"""
        import tarfile

        with tarfile.open(backup_path, "r:gz") as tar:
            # セキュリティチェック: 危険なメンバーをフィルタリング
            safe_members = []
            for member in tar.getmembers():
                # パストラバーサル攻撃を防ぐ
                if member.name.startswith("/") or ".." in member.name:
                    logger.warning(f"危険なパスをスキップ: {member.name}")
                    continue
                # シンボリックリンクをスキップ
                if member.issym() or member.islnk():
                    logger.warning(f"シンボリックリンクをスキップ: {member.name}")
                    continue
                safe_members.append(member)

            # セキュリティ対策済み: safe_membersは上記でパストラバーサル攻撃と
            # シンボリックリンク攻撃を防ぐため適切に検証済み
            tar.extractall(self.project_root, members=safe_members)  # nosec B202

        logger.info(f"バックアップから復元完了: {backup_path}")

    def _list_migration_backups(self) -> list[dict[str, Any]]:
        """マイグレーションバックアップ一覧"""
        backup_dir = safe_path_join(self.migrations_dir, "backups")
        if not backup_dir.exists():
            return []

        backups = []
        for metadata_file in backup_dir.glob("*.json"):
            try:
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)
                backups.append(metadata)
            except Exception as e:
                logger.warning(f"バックアップメタデータ読み込み失敗: {e}")

        # タイムスタンプでソート（新しい順）
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def _update_version(self, version: str) -> None:
        """バージョン情報更新"""
        version_data = {
            "version": version,
            "updated_at": datetime.now().isoformat(),
            "migration_history": self._get_migration_history()
            + [{"version": version, "migrated_at": datetime.now().isoformat()}],
        }

        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)

    def _get_migration_history(self) -> list[dict[str, Any]]:
        """マイグレーション履歴取得"""
        if not self.version_file.exists():
            return []

        try:
            with open(self.version_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("migration_history", [])
        except Exception:
            return []
