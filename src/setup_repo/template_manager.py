"""プロジェクトテンプレート管理"""

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .security_helpers import safe_path_join
from .utils import ensure_directory

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable


class TemplateManager:
    """テンプレート管理クラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

        import importlib.resources

        try:
            # Python 3.9+
            base_templates_dir = importlib.resources.files("setup_repo").joinpath("templates")
        except (ImportError, AttributeError):
            # Fallback
            base_templates_dir = Path(__file__).parent / "templates"

        # Custom templates are user-defined and stored in project root
        # gitignore/vscode templates come from the package
        self.templates_dir = safe_path_join(self.project_root, "templates")

        if isinstance(base_templates_dir, Path):
            self.gitignore_templates_dir: Path | Traversable = base_templates_dir / "gitignore"
            self.vscode_templates_dir: Path | Traversable = base_templates_dir / "vscode"
        else:
            # importlib.resources.abc.Traversable
            self.gitignore_templates_dir = base_templates_dir.joinpath("gitignore")
            self.vscode_templates_dir = base_templates_dir.joinpath("vscode")

    def list_templates(self) -> dict[str, list[str]]:
        """利用可能なテンプレート一覧を取得"""
        templates: dict[str, list[str]] = {"gitignore": [], "vscode": [], "custom": []}

        # gitignoreテンプレート
        if self.gitignore_templates_dir.is_dir():
            templates["gitignore"] = [
                f.name[:-10]
                for f in self.gitignore_templates_dir.iterdir()
                if f.is_file() and f.name.endswith(".gitignore")
            ]

        # VS Codeテンプレート（新構造対応）
        # 新しい構造: common/, python/, node/, rust/, platform/
        # platform/の中に linux.json, windows.json, wsl.json
        if self.vscode_templates_dir.is_dir():
            vscode_templates = []
            for d in self.vscode_templates_dir.iterdir():
                if d.is_dir():
                    # 言語別テンプレート（common, python, node, rust）
                    vscode_templates.append(d.name)
                    # platformディレクトリの中身も追加
                    if d.name == "platform":
                        try:
                            for platform_file in d.iterdir():
                                if platform_file.is_file() and platform_file.name.endswith(".json"):
                                    # "linux.json" -> "linux"
                                    platform_name = platform_file.name[:-5]
                                    if platform_name not in vscode_templates:
                                        vscode_templates.append(platform_name)
                        except (OSError, AttributeError):
                            pass
            templates["vscode"] = vscode_templates

        # カスタムテンプレート
        if self.templates_dir.exists():
            templates["custom"] = [d.name for d in self.templates_dir.iterdir() if d.is_dir()]

        return templates

    def apply_gitignore_template(self, template_name: str, target_path: Path | None = None) -> Path:
        """gitignoreテンプレートを適用"""
        if target_path is None:
            target_path = Path.cwd()

        # Validate template_name
        if ".." in template_name or "/" in template_name or "\\" in template_name:
            raise FileNotFoundError(f"gitignoreテンプレート '{template_name}' が見つかりません")

        template_file: Path | Traversable
        if isinstance(self.gitignore_templates_dir, Path):
            template_file = safe_path_join(self.gitignore_templates_dir, f"{template_name}.gitignore")
        else:
            template_file = self.gitignore_templates_dir.joinpath(f"{template_name}.gitignore")

        if not template_file.is_file():
            raise FileNotFoundError(f"gitignoreテンプレート '{template_name}' が見つかりません")

        target_gitignore = safe_path_join(target_path, ".gitignore")

        # 既存の.gitignoreがある場合はバックアップ
        if target_gitignore.exists():
            backup_path = safe_path_join(target_path, ".gitignore.backup")
            shutil.copy2(target_gitignore, backup_path)

        if isinstance(template_file, Path):
            shutil.copy2(template_file, target_gitignore)
        else:
            target_gitignore.write_bytes(template_file.read_bytes())

        return target_gitignore

    def apply_vscode_template(self, platform: str, target_path: Path | None = None) -> Path:
        """
        VS Codeテンプレートを適用

        新しい構造では、vscode_setup.apply_vscode_template()を使用することを推奨します。
        このメソッドは後方互換性のために残されています。
        """
        if target_path is None:
            target_path = Path.cwd()

        # プラットフォームテンプレートの存在を確認
        platform_template_path = self.vscode_templates_dir.joinpath(f"platform/{platform}.json")
        if not platform_template_path.is_file():
            raise FileNotFoundError(f"VS Codeテンプレート '{platform}' が見つかりません")

        # 新しい構造に対応：vscode_setup.apply_vscode_templateを使用
        from .vscode_setup import apply_vscode_template as apply_vscode

        result = apply_vscode(target_path, platform, dry_run=False)
        if not result:
            raise FileNotFoundError(f"VS Codeテンプレート '{platform}' の適用に失敗しました")

        return safe_path_join(target_path, ".vscode")

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
