#!/usr/bin/env python3
"""VS Code設定テンプレート適用モジュール"""

import json
import shutil
import time
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from setup_repo.json_merge import merge_multiple_settings
from setup_repo.project_detector import ProjectDetector


def apply_vscode_template(repo_path: Path, platform: str, dry_run: bool = False) -> bool:
    """
    VS Code設定テンプレートを適用

    新しい動作：
    1. プロジェクトタイプを自動検出（Python, Node.js等）
    2. 以下のテンプレートを順番にマージ：
       - common/settings.json（言語非依存の共通設定）
       - {language}/settings.json（検出された言語の設定）
       - platform/{platform}.json（プラットフォーム固有設定）
       - 既存の.vscode/settings.json（既存設定を保持）
    3. マージ結果を.vscode/settings.jsonに書き込み
    """
    repo_name = repo_path.name

    # テンプレートディレクトリの取得（パッケージ内のtemplates/vscode）
    import importlib.resources

    try:
        # Python 3.9+
        templates_dir = importlib.resources.files("setup_repo").joinpath("templates/vscode")
    except (ImportError, AttributeError):
        # Fallback
        templates_dir = Path(__file__).parent / "templates" / "vscode"

    vscode_path = repo_path / ".vscode"
    settings_file = vscode_path / "settings.json"

    print(f"   📁 {repo_name}: VS Code設定適用中...")

    if dry_run:
        print(f"   ✅ {repo_name}: VS Code設定適用予定")
        return True

    try:
        # 1. プロジェクトタイプを検出
        detector = ProjectDetector(repo_path)
        project_types = detector.detect_project_types()
        print(
            f"   🔍 {repo_name}: 検出されたプロジェクトタイプ: {', '.join(project_types) if project_types else 'なし'}"
        )

        # 2. テンプレートを収集
        templates_to_merge: list[dict[str, Any]] = []

        # 2-1. common/settings.json（必須）
        common_settings = _load_template(templates_dir, "common/settings.json")
        if common_settings:
            templates_to_merge.append(common_settings)

        # 2-2. 言語別設定（python, node等）
        for project_type in project_types:
            lang_settings = _load_template(templates_dir, f"{project_type.lower()}/settings.json")
            if lang_settings:
                templates_to_merge.append(lang_settings)

        # 2-3. プラットフォーム固有設定
        platform_settings = _load_template(templates_dir, f"platform/{platform}.json")
        if not platform_settings and platform != "linux":
            # フォールバック: linuxを使用
            platform_settings = _load_template(templates_dir, "platform/linux.json")
        if platform_settings:
            templates_to_merge.append(platform_settings)

        # 3. 既存の設定を読み込み（存在する場合）
        existing_settings: dict[str, Any] = {}
        if settings_file.exists():
            try:
                existing_settings = json.loads(settings_file.read_text(encoding="utf-8"))
                print(f"   📦 {repo_name}: 既存設定を保持してマージ")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  {repo_name}: 既存設定の読み込み失敗（{e}）、バックアップして新規作成")
                # バックアップを作成
                backup_path = repo_path / f".vscode.bak.{int(time.time())}"
                shutil.move(str(vscode_path), str(backup_path))
                print(f"   📦 {repo_name}: 既存設定をバックアップ -> {backup_path.name}")

        # 4. すべての設定をマージ
        if not templates_to_merge:
            print(f"   ⚠️  {repo_name}: 適用可能なテンプレートが見つかりません")
            return True

        # 既存設定を最後にマージ（既存設定を優先）
        merged_settings = merge_multiple_settings(*templates_to_merge, existing_settings)

        # 5. .vscode/settings.jsonに書き込み
        vscode_path.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(json.dumps(merged_settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # 6. 言語別の追加ファイル（tasks.json, launch.json等）をコピー
        for project_type in project_types:
            _copy_additional_files(templates_dir, vscode_path, project_type.lower())

        print(f"   ✅ {repo_name}: VS Code設定適用完了")
        return True

    except Exception as e:
        print(f"   ❌ {repo_name}: VS Code設定適用失敗 - {e}")
        import traceback

        traceback.print_exc()
        return False


def _load_template(templates_dir: Path | Traversable, relative_path: str) -> dict[str, Any] | None:
    """
    テンプレートJSONファイルを読み込む

    Args:
        templates_dir: テンプレートディレクトリ（PathまたはTraversable）
        relative_path: 相対パス（例: "common/settings.json"）

    Returns:
        読み込んだJSON辞書、存在しない場合はNone
    """
    try:
        if hasattr(templates_dir, "joinpath"):
            # Traversable
            template_file = templates_dir.joinpath(relative_path)
        else:
            # Path
            template_file = templates_dir / relative_path

        if not template_file.is_file():
            return None

        # ファイル読み込み
        if isinstance(template_file, Path):
            content = template_file.read_text(encoding="utf-8")
        else:
            # Traversable
            content = template_file.read_text(encoding="utf-8")

        return json.loads(content)

    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None


def _copy_additional_files(templates_dir: Path | Traversable, vscode_path: Path, project_type: str) -> None:
    """
    言語別テンプレートディレクトリから追加ファイルをコピー

    settings.json以外のファイル（tasks.json, launch.json, extensions.json等）を
    テンプレートディレクトリからコピーします。既存ファイルは上書きしません。

    Args:
        templates_dir: テンプレートディレクトリ
        vscode_path: .vscodeディレクトリのパス
        project_type: プロジェクトタイプ（python, node, rust等）
    """
    additional_files = ["tasks.json", "launch.json", "extensions.json"]

    for filename in additional_files:
        template_file_path = f"{project_type}/{filename}"

        try:
            if hasattr(templates_dir, "joinpath"):
                # Traversable
                template_file = templates_dir.joinpath(template_file_path)
            else:
                # Path
                template_file = templates_dir / template_file_path

            if not template_file.is_file():
                continue

            # 宛先ファイルパス
            dest_file = vscode_path / filename

            # 既存ファイルがある場合はスキップ
            if dest_file.exists():
                continue

            # ファイル内容を読み込み
            if isinstance(template_file, Path):
                content = template_file.read_text(encoding="utf-8")
            else:
                # Traversable
                content = template_file.read_text(encoding="utf-8")

            # ファイルを書き込み
            dest_file.write_text(content, encoding="utf-8")

        except (FileNotFoundError, AttributeError, OSError):
            # ファイルが存在しない場合は単にスキップ
            continue
