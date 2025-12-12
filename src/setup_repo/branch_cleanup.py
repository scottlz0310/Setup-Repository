#!/usr/bin/env python3
"""リモートブランチクリーンナップモジュール"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

from .security_helpers import safe_subprocess


class BranchInfo(TypedDict):
    """ブランチ情報"""

    name: str
    last_commit_date: str
    author: str


class CleanupResult(TypedDict):
    """クリーンナップ結果"""

    deleted: int
    failed: int
    skipped: int
    branches: list[str]


class BranchCleanup:
    """リモートブランチのクリーンナップを管理するクラス"""

    def __init__(self, repo_path: Path | str) -> None:
        """初期化"""
        self.repo_path = Path(repo_path)

    def list_remote_branches(self) -> list[BranchInfo]:
        """リモートブランチ一覧を取得"""
        try:
            result = safe_subprocess(
                ["git", "branch", "-r", "--format=%(refname:short)|%(committerdate:iso)|%(authorname)"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branches: list[BranchInfo] = []
            for line in result.stdout.strip().split("\n"):
                if not line or "HEAD" in line:
                    continue
                parts = line.split("|")
                if len(parts) >= 3:
                    branches.append(
                        BranchInfo(
                            name=parts[0].strip(),
                            last_commit_date=parts[1].strip(),
                            author=parts[2].strip(),
                        )
                    )
            return branches
        except subprocess.CalledProcessError:
            return []

    def list_merged_branches(self, base_branch: str = "origin/main") -> list[str]:
        """マージ済みブランチ一覧を取得"""
        try:
            result = safe_subprocess(
                ["git", "branch", "-r", "--merged", base_branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branches = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip()
                if branch and "HEAD" not in branch and base_branch not in branch:
                    branches.append(branch)
            return branches
        except subprocess.CalledProcessError:
            return []

    def list_stale_branches(self, days: int = 90) -> list[BranchInfo]:
        """指定日数以上更新されていないブランチを取得"""
        all_branches = self.list_remote_branches()
        cutoff_date = datetime.now() - timedelta(days=days)
        stale_branches: list[BranchInfo] = []

        for branch in all_branches:
            try:
                commit_date = datetime.fromisoformat(branch["last_commit_date"].replace(" ", "T")[:19])
                if commit_date < cutoff_date:
                    stale_branches.append(branch)
            except (ValueError, KeyError):
                continue

        return stale_branches

    def delete_remote_branch(self, branch_name: str, dry_run: bool = False) -> bool:
        """リモートブランチを削除"""
        if dry_run:
            print(f"   [DRY-RUN] 削除予定: {branch_name}")
            return True

        try:
            # origin/branch-name から origin と branch-name を分離
            if "/" in branch_name:
                remote, branch = branch_name.split("/", 1)
            else:
                remote = "origin"
                branch = branch_name

            safe_subprocess(
                ["git", "push", remote, "--delete", branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 削除失敗 ({branch_name}): {e.stderr.strip()}")
            return False

    def cleanup_merged_branches(
        self, base_branch: str = "origin/main", dry_run: bool = False, auto_confirm: bool = False
    ) -> CleanupResult:
        """マージ済みブランチをクリーンナップ"""
        merged_branches = self.list_merged_branches(base_branch)

        if not merged_branches:
            return CleanupResult(deleted=0, failed=0, skipped=0, branches=[])

        print(f"\n📋 マージ済みブランチ: {len(merged_branches)}件")
        for branch in merged_branches:
            print(f"   - {branch}")

        if not auto_confirm and not dry_run:
            response = input(f"\n{len(merged_branches)}件のブランチを削除しますか？ [y/N]: ").strip().lower()
            if response != "y":
                return CleanupResult(deleted=0, failed=0, skipped=len(merged_branches), branches=[])

        deleted = 0
        failed = 0
        deleted_branches: list[str] = []

        for branch in merged_branches:
            if self.delete_remote_branch(branch, dry_run):
                deleted += 1
                deleted_branches.append(branch)
                if not dry_run:
                    print(f"   ✅ 削除完了: {branch}")
            else:
                failed += 1

        return CleanupResult(deleted=deleted, failed=failed, skipped=0, branches=deleted_branches)

    def cleanup_stale_branches(
        self, days: int = 90, dry_run: bool = False, auto_confirm: bool = False
    ) -> CleanupResult:
        """古いブランチをクリーンナップ"""
        stale_branches = self.list_stale_branches(days)

        if not stale_branches:
            return CleanupResult(deleted=0, failed=0, skipped=0, branches=[])

        print(f"\n📋 {days}日以上更新されていないブランチ: {len(stale_branches)}件")
        for branch in stale_branches:
            print(f"   - {branch['name']} (最終更新: {branch['last_commit_date'][:10]})")

        if not auto_confirm and not dry_run:
            response = input(f"\n{len(stale_branches)}件のブランチを削除しますか？ [y/N]: ").strip().lower()
            if response != "y":
                return CleanupResult(deleted=0, failed=0, skipped=len(stale_branches), branches=[])

        deleted = 0
        failed = 0
        deleted_branches: list[str] = []

        for branch in stale_branches:
            if self.delete_remote_branch(branch["name"], dry_run):
                deleted += 1
                deleted_branches.append(branch["name"])
                if not dry_run:
                    print(f"   ✅ 削除完了: {branch['name']}")
            else:
                failed += 1

        return CleanupResult(deleted=deleted, failed=failed, skipped=0, branches=deleted_branches)
