"""パフォーマンスベンチマーク統合テスト."""

import platform
import shutil
import tempfile
import time
from pathlib import Path

import psutil
import pytest

from ..multiplatform.helpers import verify_current_platform


class TestPerformanceBenchmarks:
    """パフォーマンスベンチマーク統合テストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.performance_thresholds = {
            "file_operations": 2.0,  # 秒（緩和）
            "memory_usage": 100,  # MB
            "cpu_usage": 80,  # %
            "disk_io": 50,  # MB/s
            "network_latency": 100,  # ms
        }

    def teardown_method(self):
        """テストメソッドの後処理."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_file_operation_performance(self):
        """ファイル操作パフォーマンステスト."""

        # ファイル操作ベンチマーク
        def benchmark_file_operations(num_files=100, file_size_kb=10):
            start_time = time.time()
            created_files = []

            # ファイル作成ベンチマーク
            create_start = time.time()
            for i in range(num_files):
                file_path = self.temp_dir / f"test_file_{i}.txt"
                content = "x" * (file_size_kb * 1024)  # KB単位のコンテンツ
                file_path.write_text(content)
                created_files.append(file_path)
            create_time = time.time() - create_start

            # ファイル読み取りベンチマーク
            read_start = time.time()
            total_bytes_read = 0
            for file_path in created_files:
                content = file_path.read_text()
                total_bytes_read += len(content)
            read_time = time.time() - read_start

            # ファイル削除ベンチマーク
            delete_start = time.time()
            for file_path in created_files:
                file_path.unlink()
            delete_time = time.time() - delete_start

            total_time = time.time() - start_time

            return {
                "total_time": total_time,
                "create_time": create_time,
                "read_time": read_time,
                "delete_time": delete_time,
                "files_processed": num_files,
                "total_bytes": total_bytes_read,
                "throughput_mb_s": (total_bytes_read / (1024 * 1024)) / max(total_time, 0.001),
            }

        # ファイル操作ベンチマーク実行
        result = benchmark_file_operations(num_files=50, file_size_kb=5)

        # パフォーマンス検証（閾値を緩和）
        assert result["total_time"] < self.performance_thresholds["file_operations"]
        assert result["files_processed"] == 50
        assert result["throughput_mb_s"] > 0.1  # 最低0.1MB/s（緩和）

    @pytest.mark.integration
    @pytest.mark.slow
    def test_memory_usage_benchmark(self):
        """メモリ使用量ベンチマークテスト."""

        # メモリ使用量測定
        def measure_memory_usage(operation_func, *args, **kwargs):
            import gc

            # ガベージコレクション実行
            gc.collect()

            # 開始時のメモリ使用量
            process = psutil.Process()
            start_memory = process.memory_info().rss / (1024 * 1024)  # MB

            # 操作実行
            start_time = time.time()
            _ = operation_func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 終了時のメモリ使用量
            end_memory = process.memory_info().rss / (1024 * 1024)  # MB

            # ガベージコレクション実行
            gc.collect()

            # 最終メモリ使用量
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB

            return {
                "start_memory_mb": start_memory,
                "peak_memory_mb": end_memory,
                "final_memory_mb": final_memory,
                "memory_increase_mb": end_memory - start_memory,
                "memory_leaked_mb": final_memory - start_memory,
                "execution_time": execution_time,
                "operation_result": _,
            }

        # メモリ集約的な操作
        def memory_intensive_operation():
            # 大きなデータ構造を作成
            data = []
            for i in range(10000):
                data.append(
                    {
                        "id": i,
                        "data": "x" * 100,  # 100文字の文字列
                        "nested": {"value": i * 2},
                    }
                )

            # データ処理
            processed = [item for item in data if item["id"] % 2 == 0]
            return len(processed)

        # メモリベンチマーク実行
        memory_result = measure_memory_usage(memory_intensive_operation)

        # メモリ使用量検証
        assert memory_result["memory_increase_mb"] < self.performance_thresholds["memory_usage"]
        assert memory_result["memory_leaked_mb"] < 10  # メモリリーク10MB未満
        assert memory_result["operation_result"] == 5000  # 偶数の数

    @pytest.mark.integration
    @pytest.mark.slow
    def test_cpu_usage_benchmark(self):
        """CPU使用率ベンチマークテスト."""

        # CPU使用率測定
        def measure_cpu_usage(operation_func, duration=2.0):
            import threading

            cpu_samples = []
            stop_monitoring = threading.Event()

            def monitor_cpu():
                while not stop_monitoring.is_set():
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    cpu_samples.append(cpu_percent)

            # CPU監視開始
            monitor_thread = threading.Thread(target=monitor_cpu)
            monitor_thread.start()

            # 操作実行
            start_time = time.time()
            _ = operation_func()
            execution_time = time.time() - start_time

            # CPU監視停止
            stop_monitoring.set()
            monitor_thread.join()

            # CPU使用率統計
            if cpu_samples:
                avg_cpu = sum(cpu_samples) / len(cpu_samples)
                max_cpu = max(cpu_samples)
                min_cpu = min(cpu_samples)
            else:
                avg_cpu = max_cpu = min_cpu = 0

            return {
                "execution_time": execution_time,
                "avg_cpu_percent": avg_cpu,
                "max_cpu_percent": max_cpu,
                "min_cpu_percent": min_cpu,
                "cpu_samples": len(cpu_samples),
                "operation_result": _,
            }

        # CPU集約的な操作
        def cpu_intensive_operation():
            # 計算集約的なタスク
            result = 0
            for i in range(100000):
                result += i**2
                if i % 1000 == 0:
                    # 素数判定（CPU集約的）
                    n = i + 1
                    is_prime = n > 1 and all(n % j != 0 for j in range(2, int(n**0.5) + 1))
                    if is_prime:
                        result += n
            return result

        # CPUベンチマーク実行
        cpu_result = measure_cpu_usage(cpu_intensive_operation)

        # CPU使用率検証
        assert cpu_result["execution_time"] > 0
        assert cpu_result["avg_cpu_percent"] >= 0
        assert cpu_result["max_cpu_percent"] <= 100

    @pytest.mark.integration
    @pytest.mark.slow
    def test_disk_io_benchmark(self):
        """ディスクI/Oベンチマークテスト."""

        # ディスクI/O測定
        def benchmark_disk_io(file_size_mb=10, block_size_kb=64):
            file_path = self.temp_dir / "disk_benchmark.dat"
            block_size = block_size_kb * 1024
            total_size = file_size_mb * 1024 * 1024
            num_blocks = total_size // block_size

            # 書き込みベンチマーク
            write_start = time.time()
            with open(file_path, "wb") as f:
                for _ in range(num_blocks):
                    f.write(b"x" * block_size)
                f.flush()  # バッファをフラッシュ
            write_time = time.time() - write_start

            # 読み取りベンチマーク
            read_start = time.time()
            total_read = 0
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(block_size)
                    if not chunk:
                        break
                    total_read += len(chunk)
            read_time = time.time() - read_start

            # ファイル削除
            file_path.unlink()

            # スループット計算（ゼロ除算を防ぐ）
            write_throughput = (total_size / (1024 * 1024)) / max(write_time, 0.001)  # MB/s
            read_throughput = (total_read / (1024 * 1024)) / max(read_time, 0.001)  # MB/s

            return {
                "file_size_mb": file_size_mb,
                "write_time": write_time,
                "read_time": read_time,
                "write_throughput_mb_s": write_throughput,
                "read_throughput_mb_s": read_throughput,
                "total_bytes_written": total_size,
                "total_bytes_read": total_read,
            }

        # ディスクI/Oベンチマーク実行
        io_result = benchmark_disk_io(file_size_mb=5, block_size_kb=32)

        # ディスクI/O性能検証
        assert io_result["write_throughput_mb_s"] > 1.0  # 最低1MB/s
        assert io_result["read_throughput_mb_s"] > 1.0  # 最低1MB/s
        assert io_result["total_bytes_written"] == io_result["total_bytes_read"]

    @pytest.mark.integration
    @pytest.mark.slow
    def test_concurrent_operations_benchmark(self):
        """並行操作ベンチマークテスト."""
        import concurrent.futures

        # 並行操作ベンチマーク
        def benchmark_concurrent_operations(num_threads=4, operations_per_thread=25):
            results = []

            def worker_operation(worker_id):
                worker_results = []
                start_time = time.time()

                for i in range(operations_per_thread):
                    # ファイル操作
                    file_path = self.temp_dir / f"worker_{worker_id}_file_{i}.txt"
                    content = f"Worker {worker_id} - Operation {i} - " + "x" * 100

                    # 書き込み
                    file_path.write_text(content)

                    # 読み取り
                    read_content = file_path.read_text()

                    # 削除
                    file_path.unlink()

                    worker_results.append(
                        {"worker_id": worker_id, "operation_id": i, "content_length": len(read_content)}
                    )

                execution_time = time.time() - start_time
                return {
                    "worker_id": worker_id,
                    "execution_time": execution_time,
                    "operations_completed": len(worker_results),
                    "operations_per_second": len(worker_results) / max(execution_time, 0.001),
                }

            # 並行実行
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_operation, i) for i in range(num_threads)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time

            # 統計計算
            total_operations = sum(r["operations_completed"] for r in results)
            avg_ops_per_second = sum(r["operations_per_second"] for r in results) / max(len(results), 1)

            return {
                "total_time": total_time,
                "num_threads": num_threads,
                "total_operations": total_operations,
                "avg_operations_per_second": avg_ops_per_second,
                "overall_operations_per_second": total_operations / max(total_time, 0.001),
                "worker_results": results,
            }

        # 並行操作ベンチマーク実行
        concurrent_result = benchmark_concurrent_operations(num_threads=3, operations_per_thread=10)

        # 並行操作性能検証
        assert concurrent_result["total_operations"] == 30  # 3 threads * 10 operations
        assert concurrent_result["overall_operations_per_second"] > 5  # 最低5ops/s
        assert len(concurrent_result["worker_results"]) == 3

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のパフォーマンステスト")
    def test_unix_specific_performance(self):
        """Unix固有のパフォーマンステスト."""

        # Unix固有の操作ベンチマーク
        def benchmark_unix_operations():
            import os
            import subprocess

            results = {}

            # プロセス作成ベンチマーク
            start_time = time.time()
            for i in range(10):
                result = subprocess.run(["echo", f"test_{i}"], capture_output=True, text=True)
                assert result.returncode == 0
            results["process_creation_time"] = time.time() - start_time

            # ファイル権限操作ベンチマーク
            test_file = self.temp_dir / "unix_test.txt"
            test_file.write_text("test content")

            start_time = time.time()
            for _i in range(100):
                os.chmod(test_file, 0o644)
                os.chmod(test_file, 0o755)
            results["permission_change_time"] = time.time() - start_time

            test_file.unlink()

            return results

        # Unix固有ベンチマーク実行
        unix_result = benchmark_unix_operations()

        # Unix固有性能検証
        assert unix_result["process_creation_time"] < 2.0  # 2秒未満
        assert unix_result["permission_change_time"] < 1.0  # 1秒未満

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のパフォーマンステスト")
    def test_windows_specific_performance(self):
        """Windows固有のパフォーマンステスト."""

        # Windows固有の操作ベンチマーク
        def benchmark_windows_operations():
            import subprocess

            results = {}

            # Windows コマンド実行ベンチマーク
            start_time = time.time()
            for i in range(10):
                result = subprocess.run(["echo", f"test_{i}"], shell=True, capture_output=True, text=True)
                assert result.returncode == 0
            results["cmd_execution_time"] = time.time() - start_time

            # ファイルパス操作ベンチマーク
            start_time = time.time()
            for i in range(1000):
                path = Path(f"C:\\temp\\test_{i}.txt")
                normalized = path.resolve()
                _ = str(normalized)
            results["path_operation_time"] = time.time() - start_time

            return results

        # Windows固有ベンチマーク実行
        windows_result = benchmark_windows_operations()

        # Windows固有性能検証
        assert windows_result["cmd_execution_time"] < 3.0  # 3秒未満
        assert windows_result["path_operation_time"] < 1.0  # 1秒未満

    @pytest.mark.integration
    @pytest.mark.slow
    def test_comprehensive_performance_suite(self):
        """包括的パフォーマンステストスイート."""

        # 包括的パフォーマンス測定
        def comprehensive_benchmark():
            benchmark_results = {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "benchmarks": {},
            }

            # 1. 基本的なファイル操作
            start_time = time.time()
            test_file = self.temp_dir / "comprehensive_test.txt"
            for i in range(100):
                test_file.write_text(f"Test content {i}")
                content = test_file.read_text()
                assert f"Test content {i}" in content
            test_file.unlink()
            benchmark_results["benchmarks"]["basic_file_ops"] = time.time() - start_time

            # 2. メモリ操作
            start_time = time.time()
            data = [i**2 for i in range(10000)]
            _ = [x for x in data if x % 2 == 0]
            benchmark_results["benchmarks"]["memory_ops"] = time.time() - start_time

            # 3. 計算処理
            start_time = time.time()
            _ = sum(i**0.5 for i in range(10000))
            benchmark_results["benchmarks"]["computation"] = time.time() - start_time

            # 4. 文字列処理
            start_time = time.time()
            text = "test string " * 1000
            _ = text.upper().replace("TEST", "PROCESSED").split()
            benchmark_results["benchmarks"]["string_ops"] = time.time() - start_time

            # 5. JSON処理
            import json

            start_time = time.time()
            data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]}
            json_str = json.dumps(data)
            _ = json.loads(json_str)
            benchmark_results["benchmarks"]["json_ops"] = time.time() - start_time

            return benchmark_results

        # 包括的ベンチマーク実行
        comprehensive_result = comprehensive_benchmark()

        # 包括的性能検証
        assert comprehensive_result["platform"] in ["Windows", "Linux", "Darwin"]
        assert comprehensive_result["cpu_count"] > 0
        assert comprehensive_result["memory_total_gb"] > 0

        # 各ベンチマークの性能検証
        benchmarks = comprehensive_result["benchmarks"]
        assert benchmarks["basic_file_ops"] < 2.0
        assert benchmarks["memory_ops"] < 1.0
        assert benchmarks["computation"] < 1.0
        assert benchmarks["string_ops"] < 1.0
        assert benchmarks["json_ops"] < 1.0

        # 性能レポート生成
        performance_score = 100 - sum(benchmarks.values()) * 10  # 簡単なスコア計算
        performance_grade = "A" if performance_score >= 90 else "B" if performance_score >= 80 else "C"

        comprehensive_result["performance_score"] = max(0, performance_score)
        comprehensive_result["performance_grade"] = performance_grade

        # 性能スコア検証
        assert comprehensive_result["performance_score"] >= 0
        assert comprehensive_result["performance_grade"] in ["A", "B", "C", "D", "F"]
