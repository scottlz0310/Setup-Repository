""".gitignore管理機能"""

from pathlib import Path


class GitignoreManager:
    """Gitignore管理クラス"""

    # 推奨.gitignore設定
    RECOMMENDED_GITIGNORE = """# Personal configuration files
config.local.json

# Environment files
.env
.env.local

# Log files
*.log
logs/

# Lock files
*.lock

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.venv/
venv/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# OS specific
.DS_Store
Thumbs.db

# IDE
.vscode/settings.json
.idea/
*.swp
*.swo
*~

# uv
uv.lock
"""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self.gitignore_path = self.repo_path / ".gitignore"

    def ensure_gitignore_exists(self, dry_run: bool = False) -> bool:
        """.gitignoreファイルの存在確認と作成"""
        if self.gitignore_path.exists():
            return True

        if dry_run:
            print(f"   📝 作成予定: {self.gitignore_path}")
            return True

        try:
            self.gitignore_path.write_text(
                self.RECOMMENDED_GITIGNORE.strip() + "\n", encoding="utf-8"
            )
            print(f"   ✅ .gitignoreを作成しました: {self.gitignore_path}")
            return True
        except OSError as e:
            print(f"   ❌ .gitignore作成に失敗: {e}")
            return False

    def get_current_entries(self) -> set[str]:
        """現在の.gitignoreエントリを取得"""
        if not self.gitignore_path.exists():
            return set()

        try:
            content = self.gitignore_path.read_text(encoding="utf-8")
            entries = set()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    entries.add(line)
            return entries
        except OSError:
            return set()

    def add_entries(self, new_entries: list[str], dry_run: bool = False) -> bool:
        """新しいエントリを.gitignoreに追加"""
        if not new_entries:
            return True

        current_entries = self.get_current_entries()
        entries_to_add = [
            entry for entry in new_entries if entry not in current_entries
        ]

        if not entries_to_add:
            return True

        if dry_run:
            print(f"   📝 追加予定エントリ: {', '.join(entries_to_add)}")
            return True

        try:
            # 既存内容を読み込み
            existing_content = ""
            if self.gitignore_path.exists():
                existing_content = self.gitignore_path.read_text(encoding="utf-8")

            # 新しいエントリを追加
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"

            existing_content += "\n# Auto-generated entries\n"
            for entry in entries_to_add:
                existing_content += f"{entry}\n"

            self.gitignore_path.write_text(existing_content, encoding="utf-8")
            print(f"   ✅ .gitignoreに追加: {', '.join(entries_to_add)}")
            return True

        except OSError as e:
            print(f"   ❌ .gitignore更新に失敗: {e}")
            return False

    def add_common_python_entries(self, dry_run: bool = False) -> bool:
        """Python開発でよく生成されるファイルを追加"""
        python_entries = [
            "*.pyc",
            "__pycache__/",
            ".pytest_cache/",
            ".coverage",
            ".venv/",
            "venv/",
            "*.egg-info/",
            "build/",
            "dist/",
            ".mypy_cache/",
            ".ruff_cache/",
        ]
        return self.add_entries(python_entries, dry_run)

    def add_uv_entries(self, dry_run: bool = False) -> bool:
        """uv関連ファイルを追加"""
        uv_entries = ["uv.lock"]
        return self.add_entries(uv_entries, dry_run)

    def add_vscode_entries(self, dry_run: bool = False) -> bool:
        """VS Code関連ファイルを追加"""
        vscode_entries = [
            ".vscode/settings.json",
            ".vscode/launch.json",
            ".vscode/tasks.json",
        ]
        return self.add_entries(vscode_entries, dry_run)

    def setup_gitignore(self, dry_run: bool = False) -> bool:
        """完全な.gitignoreセットアップ"""
        success = True

        # .gitignoreファイルの存在確認・作成
        if not self.ensure_gitignore_exists(dry_run):
            success = False

        # 各種エントリの追加
        if not self.add_common_python_entries(dry_run):
            success = False

        if not self.add_uv_entries(dry_run):
            success = False

        if not self.add_vscode_entries(dry_run):
            success = False

        return success
