"""バックアップ・復元管理"""

import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from .security_helpers import safe_path_join
from .utils import ensure_directory


class BackupTargetInfo(TypedDict):
    """バックアップ対象のファイル情報"""

    path: str
    type: str
    size: int


class BackupInfo(TypedDict):
    """バックアップメタデータ"""

    name: str
    created_at: str
    file_path: str
    file_size: int
    targets: list[BackupTargetInfo]
    project_root: NotRequired[str]


class BackupManager:
    """バックアップ管理クラス"""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.backup_dir = safe_path_join(self.project_root, "backups")
        ensure_directory(self.backup_dir)

    def create_backup(self, name: str | None = None) -> Path:
        """設定とデータのバックアップを作成"""
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"backup_{timestamp}"

        backup_path = safe_path_join(self.backup_dir, f"{name}.tar.gz")

        # バックアップ対象ファイル・ディレクトリ
        backup_targets = [
            "config.local.json",
            "quality-history",
            ".vscode",
            "pyproject.toml",
            ".gitignore",
            "templates",
        ]

        # メタデータ作成
        metadata: dict[str, Any] = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "targets": [],
        }

        with tarfile.open(backup_path, "w:gz") as tar:
            for target in backup_targets:
                target_path = safe_path_join(self.project_root, target)
                if target_path.exists():
                    arcname = target_path.name
                    tar.add(target_path, arcname=arcname)
                    metadata["targets"].append(
                        {
                            "path": target,
                            "type": "directory" if target_path.is_dir() else "file",
                            "size": self._get_size(target_path),
                        }
                    )

            # メタデータをバックアップに含める
            import io

            metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
            metadata_bytes = metadata_json.encode("utf-8")
            metadata_info = tarfile.TarInfo(name="backup_metadata.json")
            metadata_info.size = len(metadata_bytes)
            tar.addfile(metadata_info, io.BytesIO(metadata_bytes))

        return backup_path

    def list_backups(self) -> list[BackupInfo]:
        """利用可能なバックアップ一覧を取得"""
        backups: list[BackupInfo] = []

        if not self.backup_dir.exists():
            return backups

        for backup_file in self.backup_dir.glob("*.tar.gz"):
            try:
                metadata = self._get_backup_metadata(backup_file)
                if metadata:
                    metadata["file_path"] = str(backup_file)
                    metadata["file_size"] = backup_file.stat().st_size
                    backups.append(metadata)
            except Exception:
                # メタデータが読めない場合はファイル情報のみ
                fallback_backup: BackupInfo = {
                    "name": backup_file.stem,
                    "file_path": str(backup_file),
                    "file_size": backup_file.stat().st_size,
                    "created_at": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    "targets": [],
                }
                backups.append(fallback_backup)

        return sorted(backups, key=lambda x: str(x.get("created_at", "")), reverse=True)

    def restore_backup(self, backup_name: str, target_path: Path | None = None) -> bool:
        """バックアップから復元"""
        if target_path is None:
            target_path = self.project_root

        backup_file = safe_path_join(self.backup_dir, f"{backup_name}.tar.gz")
        if not backup_file.exists():
            # .tar.gz拡張子なしでも検索
            backup_file = safe_path_join(self.backup_dir, backup_name)
            if not backup_file.exists():
                raise FileNotFoundError(f"バックアップファイル '{backup_name}' が見つかりません")

        # 既存ファイルのバックアップ
        self._backup_existing_files(target_path)

        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                # メタデータをスキップして復元
                for member in tar.getmembers():
                    if member.name != "backup_metadata.json":
                        tar.extract(member, target_path)
            return True
        except Exception as e:
            raise RuntimeError(f"バックアップの復元に失敗しました: {e}") from e

    def remove_backup(self, backup_name: str) -> bool:
        """バックアップファイルを削除"""
        backup_file = safe_path_join(self.backup_dir, f"{backup_name}.tar.gz")
        if not backup_file.exists():
            backup_file = safe_path_join(self.backup_dir, backup_name)
            if not backup_file.exists():
                return False

        backup_file.unlink()
        return True

    def _get_backup_metadata(self, backup_file: Path) -> BackupInfo | None:
        """バックアップファイルからメタデータを取得"""
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                try:
                    metadata_member = tar.getmember("backup_metadata.json")
                    metadata_file = tar.extractfile(metadata_member)
                    if metadata_file:
                        data: BackupInfo = json.loads(metadata_file.read().decode("utf-8"))
                        return data
                except KeyError:
                    return None
        except Exception:
            return None
        return None

    def _get_size(self, path: Path) -> int:
        """ファイル・ディレクトリのサイズを取得"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        return 0

    def _backup_existing_files(self, target_path: Path) -> None:
        """復元前に既存ファイルをバックアップ"""
        restore_backup_dir = safe_path_join(target_path, ".restore_backup")
        ensure_directory(restore_backup_dir)

        backup_targets = [
            "config.local.json",
            "quality-history",
            ".vscode",
            "pyproject.toml",
            ".gitignore",
            "templates",
        ]

        for target in backup_targets:
            target_path_full = safe_path_join(target_path, target)
            if target_path_full.exists():
                backup_target = safe_path_join(restore_backup_dir, target)
                if target_path_full.is_file():
                    ensure_directory(backup_target.parent)
                    shutil.copy2(target_path_full, backup_target)
                else:
                    if backup_target.exists():
                        shutil.rmtree(backup_target)
                    shutil.copytree(target_path_full, backup_target)
