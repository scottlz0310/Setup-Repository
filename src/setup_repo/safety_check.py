#!/usr/bin/env python3
"""安全性チェックモジュール"""

from pathlib import Path


def check_unpushed_changes(repo_path: Path) -> tuple[bool, list[str]]:
    """未pushの変更をチェック"""
    if not (repo_path / ".git").exists():
        return False, []

    issues = []

    try:
        # 未コミットの変更
        from .security_helpers import safe_subprocess_run

        result = safe_subprocess_run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            issues.append("未コミットの変更があります")

        # 未pushのコミット
        result = safe_subprocess_run(
            ["git", "log", "@{u}..HEAD", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            issues.append("未pushのコミットがあります")

        # stashの存在
        result = safe_subprocess_run(
            ["git", "stash", "list"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            issues.append("stashがあります")

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Gitコマンド実行エラー: {e}")

    return len(issues) > 0, issues


def prompt_user_action(repo_name: str, issues: list[str], repo_path: Path | None = None) -> str:
    """ユーザーに対処法を選択させる"""
    print(f"\n⚠️  {repo_name} に未保存の変更があります:")
    for issue in issues:
        print(f"   - {issue}")

    while True:
        print("\n選択してください:")
        print("  s) スキップ（このリポジトリを処理しない）")
        print("  c) 続行（変更を失う可能性があります）")
        if repo_path:
            print("  d) 詳細を表示（git status / git stash list）")
        print("  q) 終了")

        prompt = "選択 [s/c/d/q]: " if repo_path else "選択 [s/c/q]: "
        choice = input(prompt).strip().lower()

        if choice == "d" and repo_path:
            from .security_helpers import safe_subprocess_run

            print(f"\n--- {repo_name} の詳細状況 ---")
            print("\n[git status]")
            safe_subprocess_run(["git", "status"], cwd=repo_path, check=False)
            print("\n[git stash list]")
            safe_subprocess_run(["git", "stash", "list"], cwd=repo_path, check=False)
            print("------------------------------\n")
            continue

        if choice in ["s", "c", "q"]:
            return choice

        valid_choices = "s, c, d, q" if repo_path else "s, c, q"
        print(f"{valid_choices} のいずれかを入力してください")


def create_emergency_backup(repo_path: Path) -> bool:
    """緊急バックアップを作成"""
    try:
        backup_name = f"{repo_path.name}.backup.{int(__import__('time').time())}"
        backup_path = repo_path.parent / backup_name

        import shutil

        shutil.copytree(repo_path, backup_path)
        print(f"   📦 緊急バックアップ作成: {backup_name}")
        return True
    except Exception as e:
        print(f"   ❌ バックアップ失敗: {e}")
        return False
