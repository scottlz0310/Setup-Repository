#!/usr/bin/env python3
"""VS Code設定テンプレート適用モジュール"""

import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable


def apply_vscode_template(repo_path: Path, platform: str, dry_run: bool = False) -> bool:
    """VS Code設定テンプレートを適用"""
    repo_name = repo_path.name

    # テンプレートディレクトリの取得（パッケージ内のtemplates/vscode）
    import importlib.resources

    try:
        # Python 3.9+
        templates_dir = importlib.resources.files("setup_repo").joinpath("templates/vscode")
    except (ImportError, AttributeError):
        # Fallback
        templates_dir = Path(__file__).parent / "templates" / "vscode"

    # プラットフォーム別テンプレート選択
    template_path: Path | Traversable
    linux_fallback: Path | Traversable
    if hasattr(templates_dir, "joinpath"):
        # Traversable
        template_path = templates_dir.joinpath(platform)
        linux_fallback = templates_dir.joinpath("linux")
    else:
        # Path
        template_path = templates_dir / platform
        linux_fallback = templates_dir / "linux"

    # パスの存在確認（TraversableとPathの両方に対応）
    if not template_path.is_dir():
        template_path = linux_fallback  # フォールバック

    if not template_path.is_dir():
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
        vscode_path.mkdir(parents=True, exist_ok=True)

        item: Path | Traversable
        if isinstance(template_path, Path):
            # Pathの場合は通常のcopytree
            for item in template_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, vscode_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, vscode_path / item.name)
        else:
            # Traversableの場合は個別にコピー
            for item in template_path.iterdir():
                if item.is_file():
                    (vscode_path / item.name).write_bytes(item.read_bytes())
                # Traversableはディレクトリのネストをサポートしない

        print(f"   ✅ {repo_name}: VS Code設定適用完了")
        return True

    except Exception as e:
        print(f"   ❌ {repo_name}: VS Code設定適用失敗 - {e}")
        return False
