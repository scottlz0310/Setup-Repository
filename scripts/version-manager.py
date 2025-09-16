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

    args = parser.parse_args()

    if not any([args.check, args.set, args.bump]):
        parser.print_help()
        return 1

    manager = VersionManager()

    if args.check:
        if not manager.check_consistency():
            return 1
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

        if args.tag and not manager.create_git_tag(new_version, args.push):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
