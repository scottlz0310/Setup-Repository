"""プロジェクトテンプレート管理"""

import json
import shutil
from pathlib import Path

from .security_helpers import safe_path_join
from .utils import ensure_directory


class TemplateManager:
    """テンプレート管理クラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.templates_dir = safe_path_join(self.project_root, "templates")
        self.gitignore_templates_dir = safe_path_join(self.project_root, "gitignore-templates")
        self.vscode_templates_dir = safe_path_join(self.project_root, "vscode-templates")

    def list_templates(self) -> dict[str, list[str]]:
        """利用可能なテンプレート一覧を取得"""
        templates: dict[str, list[str]] = {"gitignore": [], "vscode": [], "custom": []}

        # gitignoreテンプレート
        if self.gitignore_templates_dir.exists():
            templates["gitignore"] = [f.stem for f in self.gitignore_templates_dir.glob("*.gitignore")]

        # VS Codeテンプレート
        if self.vscode_templates_dir.exists():
            templates["vscode"] = [d.name for d in self.vscode_templates_dir.iterdir() if d.is_dir()]

        # カスタムテンプレート
        if self.templates_dir.exists():
            templates["custom"] = [d.name for d in self.templates_dir.iterdir() if d.is_dir()]

        return templates

    def apply_gitignore_template(self, template_name: str, target_path: Path | None = None) -> Path:
        """gitignoreテンプレートを適用"""
        if target_path is None:
            target_path = Path.cwd()

        template_file = safe_path_join(self.gitignore_templates_dir, f"{template_name}.gitignore")
        if not template_file.exists():
            raise FileNotFoundError(f"gitignoreテンプレート '{template_name}' が見つかりません")

        target_gitignore = safe_path_join(target_path, ".gitignore")

        # 既存の.gitignoreがある場合はバックアップ
        if target_gitignore.exists():
            backup_path = safe_path_join(target_path, ".gitignore.backup")
            shutil.copy2(target_gitignore, backup_path)

        shutil.copy2(template_file, target_gitignore)
        return target_gitignore

    def apply_vscode_template(self, platform: str, target_path: Path | None = None) -> Path:
        """VS Codeテンプレートを適用"""
        if target_path is None:
            target_path = Path.cwd()

        template_dir = safe_path_join(self.vscode_templates_dir, platform)
        if not template_dir.exists():
            raise FileNotFoundError(f"VS Codeテンプレート '{platform}' が見つかりません")

        target_vscode_dir = safe_path_join(target_path, ".vscode")
        ensure_directory(target_vscode_dir)

        # settings.jsonをコピー
        template_settings = safe_path_join(template_dir, "settings.json")
        if template_settings.exists():
            target_settings = safe_path_join(target_vscode_dir, "settings.json")
            shutil.copy2(template_settings, target_settings)

        return target_vscode_dir

    def create_custom_template(self, name: str, source_path: Path) -> Path:
        """カスタムテンプレートを作成"""
        if not source_path.exists():
            raise FileNotFoundError(f"ソースパス '{source_path}' が見つかりません")

        ensure_directory(self.templates_dir)
        template_path = safe_path_join(self.templates_dir, name)

        if template_path.exists():
            raise FileExistsError(f"テンプレート '{name}' は既に存在します")

        if source_path.is_file():
            ensure_directory(template_path)
            shutil.copy2(source_path, template_path)
        else:
            shutil.copytree(source_path, template_path)

        # メタデータファイルを作成
        metadata = {
            "name": name,
            "created_from": str(source_path),
            "type": "file" if source_path.is_file() else "directory",
        }
        metadata_file = safe_path_join(template_path, "template.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return template_path

    def apply_custom_template(self, name: str, target_path: Path | None = None) -> Path:
        """カスタムテンプレートを適用"""
        if target_path is None:
            target_path = Path.cwd()

        template_path = safe_path_join(self.templates_dir, name)
        if not template_path.exists():
            raise FileNotFoundError(f"カスタムテンプレート '{name}' が見つかりません")

        # メタデータを読み込み
        metadata_file = safe_path_join(template_path, "template.json")
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {"type": "directory"}

        if metadata.get("type") == "file":
            # ファイルテンプレートの場合
            for file_path in template_path.iterdir():
                if file_path.name != "template.json":
                    target_file = safe_path_join(target_path, file_path.name)
                    shutil.copy2(file_path, target_file)
        else:
            # ディレクトリテンプレートの場合
            for item in template_path.iterdir():
                if item.name != "template.json":
                    target_item = safe_path_join(target_path, item.name)
                    if item.is_file():
                        shutil.copy2(item, target_item)
                    else:
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)

        return target_path

    def remove_template(self, name: str) -> bool:
        """カスタムテンプレートを削除"""
        template_path = safe_path_join(self.templates_dir, name)
        if not template_path.exists():
            return False

        shutil.rmtree(template_path)
        return True
