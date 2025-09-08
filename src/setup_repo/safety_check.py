#!/usr/bin/env python3
"""安全性チェックモジュール"""
import subprocess
from pathlib import Path
from typing import List, Tuple


def check_unpushed_changes(repo_path: Path) -> Tuple[bool, List[str]]:
    """未pushの変更をチェック"""
    if not (repo_path / ".git").exists():
        return False, []
    
    issues = []
    
    try:
        # 未コミットの変更
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            issues.append("未コミットの変更があります")
        
        # 未pushのコミット
        result = subprocess.run(['git', 'log', '@{u}..HEAD', '--oneline'], 
                              cwd=repo_path, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            issues.append("未pushのコミットがあります")
        
        # stashの存在
        result = subprocess.run(['git', 'stash', 'list'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            issues.append("stashがあります")
            
    except subprocess.CalledProcessError:
        pass
    
    return len(issues) > 0, issues


def prompt_user_action(repo_name: str, issues: List[str]) -> str:
    """ユーザーに対処法を選択させる"""
    print(f"\n⚠️  {repo_name} に未保存の変更があります:")
    for issue in issues:
        print(f"   - {issue}")
    
    print("\n選択してください:")
    print("  s) スキップ（このリポジトリを処理しない）")
    print("  c) 続行（変更を失う可能性があります）")
    print("  q) 終了")
    
    while True:
        choice = input("選択 [s/c/q]: ").strip().lower()
        if choice in ['s', 'c', 'q']:
            return choice
        print("s, c, q のいずれかを入力してください")


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