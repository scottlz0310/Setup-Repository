""".gitignore管理機能"""

from pathlib import Path

from .security_helpers import safe_path_join


class GitignoreManager:
    """Gitignore管理クラス"""

    def __init__(self, repo_path: Path, templates_dir: Path = None, auto_push: bool = None):
        self.repo_path = Path(repo_path)
        self.gitignore_path = self.repo_path / ".gitignore"

        # テンプレートディレクトリの設定
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # デフォルト: プロジェクトルートのgitignore-templatesディレクトリ
            project_root = Path(__file__).parent.parent.parent
            self.templates_dir = project_root / "gitignore-templates"

        # auto_pushのデフォルト設定（テスト/CI時は自動的に無効化）
        if auto_push is None:
            self.auto_push_default = self._should_enable_auto_push()
        else:
            self.auto_push_default = auto_push

    def _should_enable_auto_push(self) -> bool:
        """
        auto_pushを有効にすべきかを判定

        以下の場合は無効化:
        - pytestやunittestの実行中
        - CI環境での実行中
        - 環境変数で明示的に無効化
        """
        import os
        import sys

        # 環境変数で明示的に制御
        env_value = os.environ.get("SETUP_REPO_AUTO_PUSH", "").lower()
        if env_value in ("0", "false", "no"):
            return False
        if env_value in ("1", "true", "yes"):
            return True

        # pytest実行中かチェック
        if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
            return False

        # unittest実行中かチェック
        if "unittest" in sys.modules:
            return False

        # CI環境かチェック（主要なCI環境の環境変数）
        ci_indicators = [
            "CI",  # GitHub Actions, GitLab CI, Travis CI など
            "CONTINUOUS_INTEGRATION",  # 汎用
            "GITHUB_ACTIONS",  # GitHub Actions
            "GITLAB_CI",  # GitLab CI
            "JENKINS_HOME",  # Jenkins
            "CIRCLECI",  # CircleCI
            "TRAVIS",  # Travis CI
        ]
        return not any(os.environ.get(indicator) for indicator in ci_indicators)

    def ensure_gitignore_exists(self, dry_run: bool = False) -> bool:
        """.gitignoreファイルの存在確認と作成"""
        if self.gitignore_path.exists():
            return True

        # テンプレートベースで作成
        return self.setup_gitignore(dry_run)

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

    def add_entries(self, new_entries: list[str], dry_run: bool = False, auto_push: bool = None) -> bool:
        """新しいエントリを.gitignoreに追加"""
        if not new_entries:
            return True

        current_entries = self.get_current_entries()
        entries_to_add = [entry for entry in new_entries if entry not in current_entries]

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
            success = True

        except OSError as e:
            print(f"   ❌ .gitignore更新に失敗: {e}")
            success = False

        # 追加成功後、auto_pushが有効ならpushを試みる
        # auto_pushがNoneの場合はインスタンスのデフォルト設定を使用
        effective_auto_push = auto_push if auto_push is not None else self.auto_push_default
        if success and effective_auto_push and not dry_run:
            from .git_operations import commit_and_push_file

            commit_msg = "chore: update .gitignore (auto-generated entries)"
            if commit_and_push_file(self.repo_path, ".gitignore", commit_msg, auto_confirm=False):
                print("   ✅ .gitignoreをpushしました")
            else:
                print("   ⚠️  pushに失敗しました。後で手動でpushしてください")

        return success

    def load_template(self, template_name: str) -> str:
        """テンプレートファイルを読み込み"""
        try:
            template_file = safe_path_join(self.templates_dir, f"{template_name}.gitignore")
        except ValueError:
            return ""

        if not template_file.exists():
            return ""

        try:
            return template_file.read_text(encoding="utf-8")
        except OSError:
            return ""

    def get_available_templates(self) -> list[str]:
        """利用可能なテンプレート一覧を取得"""
        if not self.templates_dir.exists():
            return []

        templates = []
        for file in self.templates_dir.glob("*.gitignore"):
            templates.append(file.stem)
        return sorted(templates)

    def setup_gitignore_from_templates(
        self,
        template_names: list[str],
        dry_run: bool = False,
        merge_mode: bool = True,
        auto_push: bool = None,
    ) -> bool:
        """テンプレートから.gitignoreを作成またはマージ"""
        if dry_run:
            print(f"   📝 テンプレート使用予定: {', '.join(template_names)}")
            return True

        # 既存の.gitignoreをチェック
        success = False
        if self.gitignore_path.exists():
            if merge_mode:
                success = self._merge_with_existing(template_names)
            else:
                print(f"   ℹ️  既存の.gitignoreが存在します: {self.gitignore_path}")
                success = True
        else:
            # 新規作成
            success = self._create_new_gitignore(template_names)

        # 成功後、auto_pushが有効ならpushを試みる
        # auto_pushがNoneの場合はインスタンスのデフォルト設定を使用
        effective_auto_push = auto_push if auto_push is not None else self.auto_push_default
        if success and effective_auto_push and not dry_run:
            from .git_operations import commit_and_push_file

            commit_msg = "chore: update .gitignore (setup from templates)"
            if commit_and_push_file(self.repo_path, ".gitignore", commit_msg, auto_confirm=False):
                print("   ✅ .gitignoreをpushしました")
            else:
                print("   ⚠️  pushに失敗しました。後で手動でpushしてください")

        return success

    def _create_new_gitignore(self, template_names: list[str]) -> bool:
        """新規.gitignore作成"""
        content_parts = []
        used_templates = []

        for template_name in template_names:
            template_content = self.load_template(template_name)
            if template_content:
                content_parts.append(f"# {template_name.title()}")
                content_parts.append(template_content.strip())
                content_parts.append("")  # 空行
                used_templates.append(template_name)

        if not content_parts:
            print("   ⚠️  利用可能なテンプレートがありません")
            return False

        try:
            full_content = "\n".join(content_parts)
            self.gitignore_path.write_text(full_content, encoding="utf-8")
            print(f"   ✅ .gitignoreを作成しました: {', '.join(used_templates)}")
            return True
        except OSError as e:
            print(f"   ❌ .gitignore作成に失敗: {e}")
            return False

    def _merge_with_existing(self, template_names: list[str]) -> bool:
        """既存.gitignoreとテンプレートをマージ"""
        try:
            existing_content = self.gitignore_path.read_text(encoding="utf-8")
            existing_entries = self.get_current_entries()

            # テンプレートから新しいエントリを収集（重複除去）
            new_entries = set()
            for template_name in template_names:
                template_content = self.load_template(template_name)
                if template_content:
                    for line in template_content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and line not in existing_entries:
                            new_entries.add(line)

            if not new_entries:
                print("   ℹ️  既存の.gitignoreに追加するエントリはありません")
                return True

            # 既存コンテンツに新しいエントリを追加
            if not existing_content.endswith("\n"):
                existing_content += "\n"

            existing_content += "\n# Auto-generated entries from templates\n"
            # ソートして一貫性を保つ
            for entry in sorted(new_entries):
                existing_content += f"{entry}\n"

            self.gitignore_path.write_text(existing_content, encoding="utf-8")
            print(f"   ✅ .gitignoreにエントリを追加しました: {len(new_entries)}件")
            return True

        except OSError as e:
            print(f"   ❌ .gitignoreマージに失敗: {e}")
            return False

    def setup_gitignore(self, dry_run: bool = False, merge_mode: bool = True, auto_push: bool = None) -> bool:
        """プロジェクトタイプを自動検出して.gitignoreセットアップ"""
        from .project_detector import ProjectDetector

        detector = ProjectDetector(self.repo_path)
        recommended_templates = detector.get_recommended_templates()

        if not dry_run:
            analysis = detector.analyze_project()
            print(f"   🔍 検出されたプロジェクトタイプ: {', '.join(analysis['project_types']) or 'なし'}")
            print(f"   🛠️  検出されたツール: {', '.join(analysis['tools']) or 'なし'}")
            print(f"   📝 適用テンプレート: {', '.join(recommended_templates)}")

        return self.setup_gitignore_from_templates(recommended_templates, dry_run, merge_mode, auto_push)
