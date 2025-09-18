#!/usr/bin/env python3
"""Windows環境でのテスト実行最適化スクリプト"""

import os
import platform
import subprocess
import sys


def detect_windows_environment():
    """Windows環境の詳細を検出"""
    if platform.system() != "Windows":
        return None

    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "is_ci": os.environ.get("CI", "").lower() == "true",
        "is_github_actions": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    }
    return info


def optimize_pytest_args():
    """Windows環境に最適化されたpytestオプションを生成"""
    win_info = detect_windows_environment()
    if not win_info:
        return []

    # 並列度は auto のまま（CPUを最大活用）
    args = [
        "-v",
        "--tb=short",
        "--disable-warnings",
        "-p",
        "xdist",
        "-n",
        "auto",  # 自動並列度（最適）
        "--dist=worksteal",  # 効率的な作業分散
        "--maxfail=10",
        "--durations=10",  # 遅いテストを特定
        "-x",  # 最初の失敗で停止（高速化）
    ]

    return args


def run_optimized_tests():
    """最適化されたテスト実行"""
    print("🚀 Windows環境向け最適化テスト実行")

    win_info = detect_windows_environment()
    if not win_info:
        print("❌ Windows環境ではありません")
        return 1

    print(f"💻 検出環境: {win_info['system']} {win_info['release']}")
    print(f"🔧 CPU数: {win_info['cpu_count']}")
    print(f"🏗️ CI環境: {'Yes' if win_info['is_ci'] else 'No'}")

    # 最適化されたpytestコマンド構築
    base_cmd = ["uv", "run", "pytest"]
    optimized_args = optimize_pytest_args()

    # テストパス指定
    test_paths = [
        "tests/unit/",  # 高速な単体テストを優先
        "tests/multiplatform/test_windows_specific.py",  # Windows固有テスト
        "tests/integration/",  # 統合テスト
    ]

    # パフォーマンステストは除外
    exclude_args = [
        "-m",
        "not performance and not stress and not slow",
        "--ignore=tests/performance/",
    ]

    # カバレッジ設定（軽量化） - pytest-covが利用可能な場合のみ
    coverage_args = []
    try:
        # pytest-covの利用可能性をチェック
        import importlib.util

        if importlib.util.find_spec("pytest_cov") is not None:
            coverage_args = [
                "--cov=src/setup_repo",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        else:
            print("⚠️ pytest-covが利用できません。カバレッジなしで実行します。")
    except ImportError:
        print("⚠️ pytest-covが利用できません。カバレッジなしで実行します。")

    # 最終コマンド構築
    cmd = base_cmd + optimized_args + exclude_args + coverage_args + test_paths

    print(f"🔧 実行コマンド: {' '.join(cmd[:10])}...")
    try:
        n_index = optimized_args.index("-n")
        print(f"📊 並列度: {optimized_args[n_index + 1]}")
    except (ValueError, IndexError):
        print("📊 並列度: 設定なし")

    try:
        # テスト実行
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("✅ Windows最適化テストが成功しました")
        else:
            print(f"❌ テストが失敗しました (終了コード: {result.returncode})")

        return result.returncode

    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return 1


def main():
    """メイン実行"""
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        # 環境情報のみ表示
        win_info = detect_windows_environment()
        if win_info:
            print("Windows環境情報:")
            for key, value in win_info.items():
                print(f"  {key}: {value}")

            print("\n最適化されたpytestオプション:")
            args = optimize_pytest_args()
            print(f"  {' '.join(args)}")
        else:
            print("Windows環境ではありません")
        return 0

    return run_optimized_tests()


if __name__ == "__main__":
    sys.exit(main())
