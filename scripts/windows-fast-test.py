#!/usr/bin/env python3
"""Windows環境でのテスト実行最適化スクリプト"""

import platform
import subprocess
import sys
from pathlib import Path


def is_windows() -> bool:
    """Windows環境かどうかを判定"""
    return platform.system().lower() == "windows"


def get_optimal_workers() -> str:
    """最適なワーカー数を取得"""
    # 全プラットフォームでautoが最適
    return "auto"


def run_fast_tests() -> int:
    """高速テスト実行"""
    workers = get_optimal_workers()

    # 基本的なテストオプション
    base_args = [
        "uv",
        "run",
        "pytest",
        "-v",
        "--tb=short",
        "--disable-warnings",
    ]

    # 並列実行設定（全プラットフォームでautoが最適）
    base_args.extend(["-n", workers, "--dist=worksteal"])

    # Windows固有の最適化
    if is_windows():
        base_args.extend(
            [
                "--timeout=120",  # タイムアウトを延長
                "--maxfail=5",  # 早期終了
                "-x",  # 最初の失敗で停止
            ]
        )
        # カバレッジを無効化して高速化
        print("[INFO] Windows環境: カバレッジを無効化して高速実行")
    else:
        # Linux/macOSではカバレッジ有効
        base_args.extend(
            [
                "--cov=src/setup_repo",
                "--cov-report=term-missing",
            ]
        )

    # 出力設定
    base_args.extend(
        [
            "--junit-xml=output/test-results.xml",
            "--json-report",
            "--json-report-file=output/test-report.json",
        ]
    )

    print(f"[INFO] テスト実行コマンド: {' '.join(base_args)}")
    print(f"[INFO] プラットフォーム: {platform.system()}")
    print(f"[INFO] 並列ワーカー数: {workers}")

    # テスト実行
    try:
        result = subprocess.run(base_args, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n[INFO] テストが中断されました")
        return 130
    except Exception as e:
        print(f"[ERROR] テスト実行エラー: {e}")
        return 1


def main() -> int:
    """メイン処理"""
    # 出力ディレクトリ作成
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    return run_fast_tests()


if __name__ == "__main__":
    sys.exit(main())
