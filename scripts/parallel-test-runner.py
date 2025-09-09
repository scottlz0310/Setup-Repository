#!/usr/bin/env python3
"""
並列テスト実行スクリプト

pytest-xdistを使用してテストを並列実行し、
パフォーマンスを最適化します。
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def get_cpu_count() -> int:
    """利用可能なCPUコア数を取得"""
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def calculate_optimal_workers(test_count: int, cpu_count: int) -> int:
    """最適なワーカー数を計算"""
    # テスト数が少ない場合は並列化の効果が薄い
    if test_count < 10:
        return 1

    # CPUコア数の75%を使用（システムリソースを残す）
    optimal_workers = max(1, int(cpu_count * 0.75))

    # テスト数がワーカー数より少ない場合は調整
    return min(optimal_workers, test_count)


def count_tests(test_paths: list[str]) -> int:
    """テスト数をカウント"""
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q"] + test_paths,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            # 出力からテスト数を抽出
            lines = result.stdout.strip().split("\n")
            for line in reversed(lines):
                if "test" in line and ("collected" in line or "selected" in line):
                    # "X tests collected" のような行を探す
                    words = line.split()
                    for _i, word in enumerate(words):
                        if word.isdigit():
                            return int(word)

        # フォールバック: ディレクトリ内のテストファイル数を概算
        test_files = 0
        for path in test_paths:
            if os.path.isfile(path) and path.endswith(".py"):
                test_files += 1
            elif os.path.isdir(path):
                test_files += len(list(Path(path).rglob("test_*.py")))

        return test_files * 5  # ファイルあたり平均5テストと仮定

    except Exception as e:
        print(f"⚠️ テスト数の取得に失敗: {e}")
        return 20  # デフォルト値


def run_parallel_tests(
    test_paths: list[str],
    workers: Optional[int] = None,
    coverage: bool = True,
    markers: Optional[str] = None,
    verbose: bool = False,
    junit_xml: Optional[str] = None,
    timeout: int = 1800,  # 30分
) -> int:
    """並列テストを実行"""

    # ワーカー数の決定
    if workers is None or workers == 0:
        cpu_count = get_cpu_count()
        test_count = count_tests(test_paths)
        workers = calculate_optimal_workers(test_count, cpu_count)

        if verbose:
            print(
                "🔧 自動設定: "
                f"CPUコア数={cpu_count}, "
                f"テスト数≈{test_count}, "
                f"ワーカー数={workers}"
            )

    # pytest コマンドを構築
    cmd = ["uv", "run", "pytest"]

    # テストパスを追加
    cmd.extend(test_paths)

    # 並列実行設定
    if workers > 1:
        cmd.extend(["-n", str(workers)])
        cmd.extend(["--dist", "worksteal"])  # 動的負荷分散

    # カバレッジ設定
    if coverage:
        cmd.extend(
            [
                "--cov=src/setup_repo",
                "--cov-report=term-missing",
                "--cov-report=xml:coverage.xml",
                "--cov-report=html:htmlcov",
                "--cov-fail-under=80",
            ]
        )

    # マーカー設定
    if markers:
        cmd.extend(["-m", markers])

    # 出力設定
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # JUnit XML出力
    if junit_xml:
        cmd.extend(["--junit-xml", junit_xml])

    # その他のオプション
    cmd.extend(["--tb=short", "--strict-markers", "--strict-config"])

    print(f"🚀 並列テスト実行開始 (ワーカー数: {workers})")
    print(f"📝 実行コマンド: {' '.join(cmd)}")

    start_time = time.time()

    try:
        result = subprocess.run(cmd, timeout=timeout)
        execution_time = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ テスト完了 (実行時間: {execution_time:.2f}秒)")
        else:
            print(f"❌ テスト失敗 (実行時間: {execution_time:.2f}秒)")

        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"⏰ テストがタイムアウトしました ({timeout}秒)")
        return 1
    except KeyboardInterrupt:
        print("🛑 テストが中断されました")
        return 1
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return 1


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="並列テスト実行スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全テストを自動並列実行
  python scripts/parallel-test-runner.py

  # 単体テストのみを4ワーカーで実行
  python scripts/parallel-test-runner.py tests/unit/ -w 4

  # パフォーマンステストを除外して実行
  python scripts/parallel-test-runner.py -m "not slow and not performance"

  # カバレッジなしで高速実行
  python scripts/parallel-test-runner.py --no-coverage -v
        """,
    )

    parser.add_argument(
        "paths", nargs="*", default=["tests/"], help="テストパス (デフォルト: tests/)"
    )

    parser.add_argument(
        "-w", "--workers", type=int, help="ワーカー数 (0またはautoで自動設定)"
    )

    parser.add_argument("-m", "--markers", help="テストマーカー (例: 'not slow')")

    parser.add_argument(
        "--no-coverage", action="store_true", help="カバレッジ測定を無効化"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="詳細出力")

    parser.add_argument("--junit-xml", help="JUnit XML出力ファイル")

    parser.add_argument(
        "--timeout", type=int, default=1800, help="タイムアウト時間（秒）"
    )

    args = parser.parse_args()

    # 環境変数からワーカー数を取得（CI環境用）
    if args.workers is None:
        env_workers = os.environ.get("PYTEST_XDIST_WORKER_COUNT")
        if env_workers == "auto":
            args.workers = 0  # 自動設定
        elif env_workers and env_workers.isdigit():
            args.workers = int(env_workers)

    # テスト実行
    exit_code = run_parallel_tests(
        test_paths=args.paths,
        workers=args.workers,
        coverage=not args.no_coverage,
        markers=args.markers,
        verbose=args.verbose,
        junit_xml=args.junit_xml,
        timeout=args.timeout,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
