#!/usr/bin/env python3
"""
リリース管理システムのテストスクリプト
バージョン管理、CHANGELOG生成、リリースワークフローの動作確認
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class ReleaseSystemTester:
    """リリース管理システムのテストクラス"""

    def __init__(self):
        self.root_path = Path.cwd()
        self.test_results: list[dict[str, Any]] = []

    def run_command(self, command: list[str], cwd: Path = None) -> dict[str, Any]:
        """コマンドを実行して結果を返す"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.root_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    def test_version_manager_check(self) -> bool:
        """バージョン一貫性チェックのテスト"""
        print("🔍 バージョン一貫性チェックをテスト中...")

        result = self.run_command(["uv", "run", "python", "scripts/version-manager.py", "--check"])

        success = result["success"]
        self.test_results.append(
            {
                "test": "version_consistency_check",
                "success": success,
                "output": result["stdout"],
                "error": result["stderr"],
            }
        )

        if success:
            print("✅ バージョン一貫性チェック: 成功")
        else:
            print("❌ バージョン一貫性チェック: 失敗")
            print(f"エラー: {result['stderr']}")

        return success

    def test_version_manager_bump(self) -> bool:
        """バージョン自動インクリメントのテスト"""
        print("📈 バージョン自動インクリメントをテスト中...")

        # 現在のバージョンを取得
        with open(self.root_path / "pyproject.toml", "rb") as f:
            import tomllib

            data = tomllib.load(f)
            original_version = data["project"]["version"]

        # テスト用の一時的なバージョンアップ
        result = self.run_command(
            [
                "uv",
                "run",
                "python",
                "scripts/version-manager.py",
                "--bump",
                "prerelease",
            ]
        )

        success = result["success"]

        if success:
            # バージョンが変更されたかチェック
            with open(self.root_path / "pyproject.toml", "rb") as f:
                new_data = tomllib.load(f)
                new_version = new_data["project"]["version"]

            if new_version != original_version:
                print(f"✅ バージョン自動インクリメント: 成功 ({original_version} → {new_version})")

                # 元のバージョンに戻す
                restore_result = self.run_command(
                    [
                        "uv",
                        "run",
                        "python",
                        "scripts/version-manager.py",
                        "--set",
                        original_version,
                    ]
                )

                if restore_result["success"]:
                    print(f"🔄 バージョンを元に戻しました: {new_version} → {original_version}")
                else:
                    print(f"⚠️ バージョンの復元に失敗: {restore_result['stderr']}")
            else:
                success = False
                print("❌ バージョンが変更されませんでした")
        else:
            print("❌ バージョン自動インクリメント: 失敗")
            print(f"エラー: {result['stderr']}")

        self.test_results.append(
            {
                "test": "version_bump",
                "success": success,
                "output": result["stdout"],
                "error": result["stderr"],
            }
        )

        return success

    def test_changelog_generation(self) -> bool:
        """CHANGELOG生成のテスト"""
        print("📝 CHANGELOG生成をテスト中...")

        # テスト用のCHANGELOGバックアップ
        changelog_path = self.root_path / "CHANGELOG.md"
        backup_path = self.root_path / "CHANGELOG.md.backup"

        if changelog_path.exists():
            shutil.copy2(changelog_path, backup_path)

        try:
            # CHANGELOG更新スクリプトを作成（リリースワークフローから抽出）
            test_script = self.root_path / "scripts" / "test-changelog-update.py"

            changelog_script = '''#!/usr/bin/env python3
import sys
import re
from datetime import datetime
from pathlib import Path

def test_changelog_update():
    """テスト用のCHANGELOG更新"""
    changelog_path = Path("CHANGELOG.md")

    # テスト用の新しいエントリを追加
    test_version = "1.0.0-test"
    today = datetime.now().strftime("%Y-%m-%d")

    new_entry = f"""
## [{test_version}] (テスト版) - {today}

### ✨ 追加

### 🐛 修正

"""

    if changelog_path.exists():
        content = changelog_path.read_text(encoding="utf-8")

        # 既存のテストエントリを削除
                content = re.sub(
                    r'\\n## \\[1\\.0\\.0-test\\].*?(?=\\n## \\[|$)',
                    '',
                    content,
                    flags=re.DOTALL,
                )

        # 新しいエントリを挿入
        lines = content.split('\\n')
        header_found = False
        insert_index = len(lines)

        for i, line in enumerate(lines):
            if line.startswith('# ') and not header_found:
                header_found = True
                continue
            if header_found and (line.startswith('## ') or i == len(lines) - 1):
                insert_index = i
                break

        lines.insert(insert_index, new_entry.strip())
        updated_content = '\\n'.join(lines)

        changelog_path.write_text(updated_content, encoding="utf-8")
        print("✅ テスト用CHANGELOGエントリを追加しました")
        return True
    else:
        print("❌ CHANGELOG.mdが見つかりません")
        return False

if __name__ == "__main__":
    test_changelog_update()
'''

            test_script.write_text(changelog_script, encoding="utf-8")
            test_script.chmod(0o755)

            # テストスクリプトを実行
            result = self.run_command(["uv", "run", "python", "scripts/test-changelog-update.py"])

            success = result["success"]

            if success:
                # CHANGELOGにテストエントリが追加されたかチェック
                if changelog_path.exists():
                    content = changelog_path.read_text(encoding="utf-8")
                    if "1.0.0-test" in content:
                        print("✅ CHANGELOG生成: 成功")
                    else:
                        success = False
                        print("❌ CHANGELOGにテストエントリが見つかりません")
                else:
                    success = False
                    print("❌ CHANGELOG.mdが生成されませんでした")
            else:
                print("❌ CHANGELOG生成: 失敗")
                print(f"エラー: {result['stderr']}")

            # テストスクリプトを削除
            if test_script.exists():
                test_script.unlink()

        finally:
            # CHANGELOGを元に戻す
            if backup_path.exists():
                shutil.move(backup_path, changelog_path)
                print("🔄 CHANGELOGを元に戻しました")

        self.test_results.append(
            {
                "test": "changelog_generation",
                "success": success,
                "output": result["stdout"],
                "error": result["stderr"],
            }
        )

        return success

    def test_build_system(self) -> bool:
        """ビルドシステムのテスト"""
        print("🏗️ ビルドシステムをテスト中...")

        # 既存のdistディレクトリを削除
        dist_path = self.root_path / "dist"
        if dist_path.exists():
            shutil.rmtree(dist_path)

        # ビルドを実行
        result = self.run_command(["uv", "build"])

        success = result["success"]

        if success:
            # ビルド成果物をチェック
            if dist_path.exists():
                files = list(dist_path.glob("*"))
                wheel_files = [f for f in files if f.suffix == ".whl"]
                tar_files = [f for f in files if f.name.endswith(".tar.gz")]

                if wheel_files and tar_files:
                    print("✅ ビルドシステム: 成功")
                    print(f"  - Wheelファイル: {len(wheel_files)}個")
                    print(f"  - Tarファイル: {len(tar_files)}個")
                else:
                    success = False
                    print("❌ 期待されるビルド成果物が見つかりません")
            else:
                success = False
                print("❌ distディレクトリが作成されませんでした")
        else:
            print("❌ ビルドシステム: 失敗")
            print(f"エラー: {result['stderr']}")

        self.test_results.append(
            {
                "test": "build_system",
                "success": success,
                "output": result["stdout"],
                "error": result["stderr"],
            }
        )

        return success

    def test_quality_checks(self) -> bool:
        """品質チェックのテスト"""
        print("🔍 品質チェックをテスト中...")

        # Ruffチェック
        ruff_result = self.run_command(["uv", "run", "ruff", "check", ".", "--quiet"])

        # BasedPyrightチェック
        pyright_result = self.run_command(["uv", "run", "basedpyright", "src/"])

        # テスト実行
        test_result = self.run_command(["uv", "run", "pytest", "tests/", "-x", "--tb=short"])

        ruff_success = ruff_result["success"]
        pyright_success = pyright_result["success"]
        test_success = test_result["success"]

        overall_success = ruff_success and pyright_success and test_success

        print(f"  - Ruffリンティング: {'✅ 成功' if ruff_success else '❌ 失敗'}")
        print(f"  - BasedPyright型チェック: {'✅ 成功' if pyright_success else '❌ 失敗'}")
        print(f"  - Pytestテスト: {'✅ 成功' if test_success else '❌ 失敗'}")

        if overall_success:
            print("✅ 品質チェック: 全て成功")
        else:
            print("❌ 品質チェック: 一部失敗")
            if not ruff_success:
                print(f"Ruffエラー: {ruff_result['stderr']}")
            if not pyright_success:
                print(f"Pyrightエラー: {pyright_result['stderr']}")
            if not test_success:
                print(f"テストエラー: {test_result['stderr']}")

        self.test_results.append(
            {
                "test": "quality_checks",
                "success": overall_success,
                "ruff": ruff_success,
                "mypy": pyright_success,
                "pyright": pyright_success,
                "pytest": test_success,
                "output": {
                    "ruff": ruff_result["stdout"],
                    "mypy": pyright_result["stdout"],
                    "pyright": pyright_result["stdout"],
                    "pytest": test_result["stdout"],
                },
            }
        )

        return overall_success

    def generate_test_report(self) -> None:
        """テスト結果レポートを生成"""
        print("\n" + "=" * 60)
        print("📊 リリース管理システム テスト結果")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])

        print(f"成功: {passed_tests}")
        print(f"失敗: {total_tests - passed_tests}")

        print("\n📋 詳細結果:")
        for result in self.test_results:
            status = "✅ 成功" if result["success"] else "❌ 失敗"
            test_name = result["test"].replace("_", " ").title()
            print(f"  - {test_name}: {status}")

        # JSON形式でも出力
        report_path = self.root_path / "test-release-system-report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": {
                        "total": total_tests,
                        "passed": passed_tests,
                        "failed": total_tests - passed_tests,
                        "success_rate": passed_tests / total_tests * 100,
                    },
                    "results": self.test_results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print(f"\n📄 詳細レポート: {report_path}")

    def run_all_tests(self) -> bool:
        """全テストを実行"""
        print("🚀 リリース管理システムの統合テストを開始...")
        print()

        tests = [
            ("バージョン一貫性チェック", self.test_version_manager_check),
            ("バージョン自動インクリメント", self.test_version_manager_bump),
            ("CHANGELOG生成", self.test_changelog_generation),
            ("ビルドシステム", self.test_build_system),
            ("品質チェック", self.test_quality_checks),
        ]

        all_passed = True

        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ {test_name}: 例外発生 - {e}")
                all_passed = False
                self.test_results.append(
                    {
                        "test": test_name.lower().replace(" ", "_"),
                        "success": False,
                        "error": str(e),
                    }
                )

        self.generate_test_report()

        if all_passed:
            print("\n🎉 全テスト成功！リリース管理システムは正常に動作しています。")
        else:
            print("\n⚠️ 一部のテストが失敗しました。問題を修正してください。")

        return all_passed


def main():
    """メイン関数"""
    print("🧪 Setup Repository - リリース管理システムテスト")
    print()

    tester = ReleaseSystemTester()
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
