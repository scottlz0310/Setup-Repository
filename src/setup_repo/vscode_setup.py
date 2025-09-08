#!/usr/bin/env python3
"""VS Code設定テンプレート適用モジュール"""
import shutil
import time
from pathlib import Path


def apply_vscode_template(repo_path: Path, platform: str, dry_run: bool = False) -> bool:
    """VS Code設定テンプレートを適用"""
    repo_name = repo_path.name
    script_dir = Path(__file__).parent
    templates_dir = script_dir / "vscode-templates"
    
    # プラットフォーム別テンプレート選択
    template_path = templates_dir / platform
    if not template_path.exists():
        template_path = templates_dir / "linux"  # フォールバック
    
    if not template_path.exists():
        return True  # テンプレートがない場合はスキップ
    
    vscode_path = repo_path / ".vscode"
    
    print(f"   📁 {repo_name}: VS Code設定適用中...")
    
    if dry_run:
        print(f"   ✅ {repo_name}: VS Code設定適用予定")
        return True
    
    try:
        # 既存の.vscodeをバックアップ
        if vscode_path.exists():
            backup_path = repo_path / f".vscode.bak.{int(time.time())}"
            shutil.move(str(vscode_path), str(backup_path))
            print(f"   📦 {repo_name}: 既存設定をバックアップ -> {backup_path.name}")
        
        # テンプレートをコピー
        shutil.copytree(template_path, vscode_path)
        print(f"   ✅ {repo_name}: VS Code設定適用完了")
        return True
        
    except Exception as e:
        print(f"   ❌ {repo_name}: VS Code設定適用失敗 - {e}")
        return False