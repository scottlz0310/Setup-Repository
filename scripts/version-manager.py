#!/usr/bin/env python3
"""
バージョン管理スクリプト
pyproject.toml、__init__.py、その他のファイルのバージョン番号を一括更新
"""

import argparse
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

import tomli_w


class VersionManager:
    """バージョン管理クラス"""

    def __init__(self):
        self.root_path = Path.cwd()
        self.version_files = {
            "pyproject.toml": self._update_pyproject_toml,
            "src/setup_repo/__init__.py": self._update_init_py,
        }

    def get_current_version(self) -> str | None:
        """現在のバージョンを取得"""
        pyproject_path = self.root_path / "pyproject.toml"

        if not pyproject_path.exists():
            print("❌ pyproject.tomlが見つかりません")
            return None

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
        except Exception as e:
            print(f"❌ バージョン取得エラー: {e}")
            return None

    def validate_version(self, version: str) -> bool:
        """セマンティックバージョンの形式をチェック"""
        # セマンティックバージョンの正規表現
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$"
        return bool(re.match(pattern, version))

    def _update_pyproject_toml(self, version: str) -> bool:
        """pyproject.tomlのバージョンを更新"""
        pyproject_path = self.root_path / "pyproject.toml"

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            data["project"]["version"] = version

            with open(pyproject_path, "wb") as f:
                tomli_w.dump(data, f)

            print(f"✅ pyproject.toml: {version}")
            return True
        except Exception as e:
            print(f"❌ pyproject.toml更新エラー: {e}")
            return False

    def _update_init_py(self, version: str) -> bool:
        """__init__.pyのバージョンを更新"""
        init_path = self.root_path / "src/setup_repo/__init__.py"

        if not init_path.exists():
            print(f"⚠️ {init_path} が見つかりません")
            return True  # 存在しない場合はスキップ

        try:
            content = init_path.read_text(encoding="utf-8")

            # __version__ = "x.x.x" の形式を更新
            pattern = r'(__version__\s*=\s*["\'])([^"\']+)(["\'])'
            replacement = f"\\g<1>{version}\\g<3>"

            updated_content = re.sub(pattern, replacement, content)

            if updated_content == content and "__version__" not in content:
                updated_content = f'"""セットアップリポジトリパッケージ"""\n\n__version__ = "{version}"\n'

            init_path.write_text(updated_content, encoding="utf-8")
            print(f"✅ __init__.py: {version}")
            return True
        except Exception as e:
            print(f"❌ __init__.py更新エラー: {e}")
            return False

    def update_version(self, new_version: str) -> bool:
        """全ファイルのバージョンを更新"""
        if not self.validate_version(new_version):
            print(f"❌ 無効なバージョン形式: {new_version}")
            print("セマンティックバージョン形式を使用してください (例: 1.0.0, 1.2.3-beta.1)")
            return False

        current_version = self.get_current_version()
        if current_version:
            print(f"🔄 バージョン更新: {current_version} → {new_version}")
        else:
            print(f"🆕 新しいバージョンを設定: {new_version}")

        success = True
        for _file_path, update_func in self.version_files.items():
            if not update_func(new_version):
                success = False

        if success:
            print(f"✅ 全ファイルのバージョン更新完了: {new_version}")
        else:
            print("❌ 一部のファイルでバージョン更新に失敗しました")

        return success

    def check_consistency(self) -> bool:
        """バージョンの一貫性をチェック"""
        versions = {}

        # pyproject.tomlのバージョン
        try:
            with open(self.root_path / "pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            versions["pyproject.toml"] = data["project"]["version"]
        except Exception as e:
            print(f"❌ pyproject.toml読み込みエラー: {e}")
            return False

        # __init__.pyのバージョン
        init_path = self.root_path / "src/setup_repo/__init__.py"
        if init_path.exists():
            try:
                content = init_path.read_text(encoding="utf-8")
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    versions["__init__.py"] = match.group(1)
                else:
                    print("⚠️ __init__.pyに__version__が見つかりません")
            except Exception as e:
                print(f"❌ __init__.py読み込みエラー: {e}")

        # 一貫性チェック
        unique_versions = set(versions.values())

        if len(unique_versions) == 1:
            version = list(unique_versions)[0]
            print(f"✅ バージョン一貫性チェック完了: {version}")
            for file_name, file_version in versions.items():
                print(f"  - {file_name}: {file_version}")
            return True
        else:
            print("❌ バージョン不整合が検出されました:")
            for file_name, file_version in versions.items():
                print(f"  - {file_name}: {file_version}")
            return False

    def bump_version(self, bump_type: str) -> str | None:
        """バージョンを自動的にインクリメント"""
        current_version = self.get_current_version()
        if not current_version:
            return None

        # セマンティックバージョンを解析
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?", current_version)
        if not match:
            print(f"❌ 現在のバージョンが解析できません: {current_version}")
            return None

        major, minor, patch = map(int, match.groups()[:3])
        prerelease = match.group(4)

        if bump_type == "major":
            new_version = f"{major + 1}.0.0"
        elif bump_type == "minor":
            new_version = f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            new_version = f"{major}.{minor}.{patch + 1}"
        elif bump_type == "prerelease":
            if prerelease:
                # 既存のプレリリースをインクリメント
                pre_match = re.match(r"([a-zA-Z]+)\.?(\d+)?", prerelease)
                if pre_match:
                    pre_type = pre_match.group(1)
                    pre_num = int(pre_match.group(2) or 0) + 1
                    new_version = f"{major}.{minor}.{patch}-{pre_type}.{pre_num}"
                else:
                    new_version = f"{major}.{minor}.{patch}-beta.1"
            else:
                # 新しいプレリリース
                new_version = f"{major}.{minor}.{patch + 1}-beta.1"
        else:
            print(f"❌ 無効なバンプタイプ: {bump_type}")
            return None

        return new_version

    def create_git_tag(self, version: str, push: bool = False) -> bool:
        """Gitタグを作成"""
        try:
            tag_name = f"v{version}"

            # タグが既に存在するかチェック
            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from setup_repo.security_helpers import safe_subprocess_run

            result = safe_subprocess_run(
                ["git", "tag", "-l", tag_name],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                print(f"⚠️ タグ {tag_name} は既に存在します")
                return False

            # タグを作成
            safe_subprocess_run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
            )
            print(f"✅ Gitタグを作成: {tag_name}")

            if push:
                safe_subprocess_run(
                    ["git", "push", "origin", tag_name],
                )
                print(f"✅ タグをプッシュ: {tag_name}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Gitタグ作成エラー: {e}")
            return False

    def update_changelog(self, version: str, is_prerelease: bool = False) -> bool:
        """CHANGELOG.mdを更新"""
        changelog_path = self.root_path / "CHANGELOG.md"

        if not changelog_path.exists():
            print("⚠️ CHANGELOG.mdが見つかりません")
            return False

        content = changelog_path.read_text(encoding="utf-8")

        # 既に同じバージョンが存在するかチェック
        if f"## [{version}]" in content:
            print(f"ℹ️ バージョン {version} は既にCHANGELOGに存在します")
            # 日付のみ更新
            today = datetime.now().strftime("%Y-%m-%d")
            updated_content = re.sub(
                f"## \\[{re.escape(version)}\\] - \\d{{4}}-\\d{{2}}-\\d{{2}}", f"## [{version}] - {today}", content
            )

            if updated_content != content:
                changelog_path.write_text(updated_content, encoding="utf-8")
                print(f"✅ CHANGELOG.mdの日付を更新: {today}")
            return True  # 既存バージョンが見つかった場合も成功として扱う

        return False

    def generate_release_notes(self, version: str, is_prerelease: bool = False) -> str:
        """リリースノートを生成"""
        changelog_path = self.root_path / "CHANGELOG.md"

        if not changelog_path.exists():
            return f"バージョン {version} のリリースです。"

        content = changelog_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # バージョンセクションを探す
        start_index = None
        end_index = None

        for i, line in enumerate(lines):
            if f"## [{version}]" in line:
                start_index = i + 1
            elif start_index is not None and line.startswith("## ["):
                end_index = i
                break

        if start_index is None:
            return f"バージョン {version} のリリースです。"

        if end_index is None:
            end_index = len(lines)

        # セクションの内容を抽出
        section_lines = lines[start_index:end_index]
        section_content = "\n".join(section_lines).strip()

        if not section_content:
            return f"バージョン {version} のリリースです。"

        prerelease_notice = ""
        if is_prerelease:
            prerelease_notice = """
> **⚠️ プレリリース版です**
> このバージョンはテスト目的であり、本番環境での使用は推奨されません。

"""

        release_notes = f"""# 🚀 Setup Repository v{version}

{prerelease_notice}## 📋 変更内容

{section_content}

## 📦 インストール方法

### 🐍 Pythonパッケージとして
```bash
pip install setup-repository
```

### 📥 ソースからインストール
```bash
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository
uv sync --dev
uv run main.py setup
```

## 🔧 使用方法

```bash
# 初期セットアップ
setup-repo setup

# リポジトリ同期
setup-repo sync

# ドライランモード
setup-repo sync --dry-run
```

## 🌐 サポートプラットフォーム

- ✅ Windows (Scoop, Winget, Chocolatey)
- ✅ Linux (Snap, APT)
- ✅ WSL (Linux互換)
- ✅ macOS (Homebrew)

## 🐍 Python要件

- Python 3.11以上
- 対応バージョン: 3.11, 3.12, 3.13

---

**完全な変更履歴**: [CHANGELOG.md](https://github.com/scottlz0310/Setup-Repository/blob/main/CHANGELOG.md)
"""

        return release_notes

    def create_release(self, version: str, is_prerelease: bool = False, push: bool = False) -> bool:
        """完全なリリースプロセスを実行"""
        print(f"🚀 リリースプロセス開始: v{version}")

        # 1. バージョン一貫性チェック
        if not self.check_consistency():
            print("❌ バージョン一貫性チェックに失敗しました")
            return False

        # 2. CHANGELOGを更新
        self.update_changelog(version, is_prerelease)

        # 3. リリースノートを生成
        release_notes = self.generate_release_notes(version, is_prerelease)
        notes_path = self.root_path / "release-notes.md"
        notes_path.write_text(release_notes, encoding="utf-8")
        print(f"✅ リリースノートを生成: {notes_path}")

        # 4. Gitタグを作成
        if not self.create_git_tag(version, push):
            print("❌ Gitタグ作成に失敗しました")
            return False

        print(f"🎉 リリース v{version} が正常に作成されました！")
        return True


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Setup Repository バージョン管理ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 現在のバージョンを確認
  python scripts/version-manager.py --check

  # バージョンを手動設定
  python scripts/version-manager.py --set 1.2.0

  # バージョンを自動インクリメント
  python scripts/version-manager.py --bump patch
  python scripts/version-manager.py --bump minor
  python scripts/version-manager.py --bump major
  python scripts/version-manager.py --bump prerelease

  # バージョン更新とGitタグ作成
  python scripts/version-manager.py --bump patch --tag --push

  # 完全なリリースプロセス
  python scripts/version-manager.py --bump patch --release --push
  python scripts/version-manager.py --set 1.3.0 --release --prerelease

  # CHANGELOG更新のみ
  python scripts/version-manager.py --update-changelog 1.3.0

  # リリースノート生成のみ
  python scripts/version-manager.py --generate-notes 1.3.0 --prerelease
        """,
    )

    parser.add_argument("--check", action="store_true", help="バージョンの一貫性をチェック")
    parser.add_argument("--set", metavar="VERSION", help="バージョンを手動設定 (例: 1.2.0)")
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch", "prerelease"],
        help="バージョンを自動インクリメント",
    )
    parser.add_argument("--tag", action="store_true", help="Gitタグを作成")
    parser.add_argument("--push", action="store_true", help="タグをリモートにプッシュ (--tagと併用)")
    parser.add_argument("--release", action="store_true", help="完全なリリースプロセスを実行")
    parser.add_argument("--prerelease", action="store_true", help="プレリリースとしてマーク")
    parser.add_argument("--update-changelog", metavar="VERSION", help="CHANGELOG.mdの日付を更新")
    parser.add_argument("--generate-notes", metavar="VERSION", help="リリースノートを生成")

    args = parser.parse_args()

    if not any([args.check, args.set, args.bump, args.update_changelog, args.generate_notes, args.release]):
        parser.print_help()
        return 1

    manager = VersionManager()

    if args.check:
        if not manager.check_consistency():
            return 1
        return 0

    if args.update_changelog:
        if not manager.update_changelog(args.update_changelog, args.prerelease):
            return 1
        return 0

    if args.generate_notes:
        notes = manager.generate_release_notes(args.generate_notes, args.prerelease)
        notes_path = Path("release-notes.md")
        notes_path.write_text(notes, encoding="utf-8")
        print(f"✅ リリースノートを生成: {notes_path}")
        return 0

    new_version = None

    if args.set:
        new_version = args.set
    elif args.bump:
        new_version = manager.bump_version(args.bump)
        if not new_version:
            return 1

    if new_version:
        if not manager.update_version(new_version):
            return 1

        if args.release:
            if not manager.create_release(new_version, args.prerelease, args.push):
                return 1
        elif args.tag and not manager.create_git_tag(new_version, args.push):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
