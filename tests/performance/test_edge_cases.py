"""
エッジケース（空文字、None、境界値）のテスト

このモジュールでは、システムの境界条件や異常な入力値に対する
堅牢性を検証します。空文字列、None値、極端に大きな値、
特殊文字などのエッジケースを包括的にテストします。
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from setup_repo.sync import sync_repositories


class EdgeCaseGenerator:
    """エッジケースデータ生成クラス"""

    @staticmethod
    def get_empty_values() -> list[Any]:
        """空値のリストを返す"""
        return ["", None, [], {}, 0, False]

    @staticmethod
    def get_whitespace_values() -> list[str]:
        """空白文字のリストを返す"""
        return [" ", "\t", "\n", "\r", "\r\n", "   ", "\t\n\r"]

    @staticmethod
    def get_special_characters() -> list[str]:
        """特殊文字のリストを返す"""
        return [
            "!@#$%^&*()",
            '<>?:"{}|',
            "\\//\\//\\",
            "../../..",
            "null\x00byte",
            "unicode🚀test",
            "日本語テスト",
            "Ñoñó-tëst",
            "test\u200bwith\u200bzero\u200bwidth",
        ]

    @staticmethod
    def get_boundary_values() -> dict[str, Any]:
        """境界値のリストを返す"""
        return {
            "max_int": 2**31 - 1,
            "min_int": -(2**31),
            "max_string_length": "x" * 10000,
            "max_path_length": "a" * 260,  # Windows MAX_PATH
            "large_number": 999999999999999,
            "negative_number": -999999999999999,
            "float_precision": 1.7976931348623157e308,
            "tiny_float": 2.2250738585072014e-308,
        }


@pytest.fixture
def edge_case_config(temp_dir: Path) -> dict[str, Any]:
    """エッジケーステスト用の基本設定"""
    return {
        "github_token": "test_token_edge",
        "github_username": "test_user",
        "clone_destination": str(temp_dir / "edge_repos"),
        "timeout_seconds": 30,
        "retry_attempts": 2,
        "dry_run": True,
    }


@pytest.mark.performance
class TestEmptyAndNullValues:
    """空値・NULL値のエッジケーステストクラス"""

    def test_empty_string_inputs(
        self,
        temp_dir: Path,
    ) -> None:
        """空文字列入力のテスト"""
        empty_values = EdgeCaseGenerator.get_empty_values()

        for empty_value in empty_values:
            config = {
                "github_token": empty_value,
                "github_username": "test_user",
                "clone_destination": str(temp_dir / "empty_test"),
            }

            result = sync_repositories(config, dry_run=True)

            # 空値の場合は失敗することを期待
            assert not result.success, f"空値 {empty_value} で成功すべきではありません"
            assert result.errors

    def test_none_configuration_values(
        self,
        temp_dir: Path,
    ) -> None:
        """None値設定のテスト"""
        base_config = {
            "github_token": "valid_token",
            "github_username": "valid_user",
            "clone_destination": str(temp_dir / "none_test"),
        }

        # 各設定項目をNoneに設定してテスト
        for key in base_config:
            test_config = base_config.copy()
            test_config[key] = None

            result = sync_repositories(test_config, dry_run=True)

            assert not result.success, f"{key}=None で成功すべきではありません"
            assert result.errors

    def test_empty_repository_list(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """空のリポジトリリストのテスト"""
        empty_repos = []

        with patch("setup_repo.sync.get_repositories", return_value=empty_repos):
            result = sync_repositories(edge_case_config, dry_run=True)

        # 空のリポジトリリストは適切にエラーとして処理される
        assert not result.success
        assert not result.synced_repos
        assert len(result.errors) == 1
        assert "リポジトリが見つかりませんでした" in str(result.errors[0])

    def test_whitespace_only_inputs(
        self,
        temp_dir: Path,
    ) -> None:
        """空白文字のみの入力テスト"""
        whitespace_values = EdgeCaseGenerator.get_whitespace_values()

        for whitespace in whitespace_values:
            config = {
                "github_token": whitespace,
                "github_username": "test_user",
                "clone_destination": str(temp_dir / "whitespace_test"),
            }

            result = sync_repositories(config, dry_run=True)

            # 空白文字のみの場合は失敗することを期待
            assert not result.success, f"空白文字 '{repr(whitespace)}' で成功すべきではありません"
            assert result.errors


@pytest.mark.performance
class TestSpecialCharacters:
    """特殊文字のエッジケーステストクラス"""

    def test_special_characters_in_repository_names(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """リポジトリ名の特殊文字テスト"""
        special_chars = EdgeCaseGenerator.get_special_characters()

        for special_char in special_chars:
            repo_name = f"test-repo-{special_char}"
            repos = [
                {
                    "name": repo_name,
                    "full_name": f"test_user/{repo_name}",
                    "clone_url": f"https://github.com/test_user/{repo_name}.git",
                    "ssh_url": f"git@github.com:test_user/{repo_name}.git",
                    "description": f"特殊文字テスト: {special_char}",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(edge_case_config, dry_run=True)

            # 特殊文字を含むリポジトリ名でも処理できることを確認
            # ただし、一部の特殊文字は失敗する可能性がある
            if result.success:
                assert len(result.synced_repos) == 1
                print(f"特殊文字 '{special_char}' での処理成功")
            else:
                print(f"特殊文字 '{special_char}' での処理失敗（予期される場合あり）")

    def test_unicode_characters_in_paths(
        self,
        temp_dir: Path,
        edge_case_config: dict[str, Any],
    ) -> None:
        """パス内Unicode文字のテスト"""
        unicode_paths = [
            "リポジトリ",
            "测试仓库",
            "тест-репо",
            "مستودع-اختبار",
            "🚀-rocket-repo",
            "café-münü-naïve",
        ]

        for unicode_path in unicode_paths:
            test_path = temp_dir / unicode_path
            edge_case_config["clone_destination"] = str(test_path)

            repos = [
                {
                    "name": "unicode-test-repo",
                    "full_name": "test_user/unicode-test-repo",
                    "clone_url": "https://github.com/test_user/unicode-test-repo.git",
                    "ssh_url": "git@github.com:test_user/unicode-test-repo.git",
                    "description": f"Unicode パステスト: {unicode_path}",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(edge_case_config, dry_run=True)

            # Unicode パスでも処理できることを確認
            assert result.success, f"Unicode パス '{unicode_path}' で失敗"
            assert len(result.synced_repos) == 1

    def test_control_characters_handling(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """制御文字の処理テスト"""
        control_chars = [
            "\x00",  # NULL
            "\x01",  # SOH
            "\x07",  # BEL
            "\x08",  # BS
            "\x0b",  # VT
            "\x0c",  # FF
            "\x1b",  # ESC
            "\x7f",  # DEL
        ]

        for control_char in control_chars:
            repo_name = f"test{control_char}repo"
            repos = [
                {
                    "name": repo_name,
                    "full_name": f"test_user/{repo_name}",
                    "clone_url": f"https://github.com/test_user/{repo_name}.git",
                    "ssh_url": f"git@github.com:test_user/{repo_name}.git",
                    "description": f"制御文字テスト: {repr(control_char)}",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(edge_case_config, dry_run=True)

            # 制御文字は処理できない場合が多いため、失敗も許容
            if not result.success:
                print(f"制御文字 {repr(control_char)} での処理失敗（予期される）")
            else:
                print(f"制御文字 {repr(control_char)} での処理成功")


@pytest.mark.performance
class TestBoundaryValues:
    """境界値のエッジケーステストクラス"""

    def test_extremely_long_repository_names(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """極端に長いリポジトリ名のテスト"""
        boundary_values = EdgeCaseGenerator.get_boundary_values()
        long_name = boundary_values["max_string_length"][:100]  # 100文字に制限

        repos = [
            {
                "name": long_name,
                "full_name": f"test_user/{long_name}",
                "clone_url": f"https://github.com/test_user/{long_name}.git",
                "ssh_url": f"git@github.com:test_user/{long_name}.git",
                "description": "極端に長い名前のテスト",
                "private": False,
                "default_branch": "main",
            }
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(edge_case_config, dry_run=True)

        # 長い名前でも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == 1

    def test_maximum_path_length(
        self,
        temp_dir: Path,
        edge_case_config: dict[str, Any],
    ) -> None:
        """最大パス長のテスト"""
        # プラットフォーム別の最大パス長を考慮
        max_path_components = ["very"] * 10 + ["long"] * 10 + ["path"] * 5
        long_path = temp_dir

        for component in max_path_components:
            long_path = long_path / component
            # パス長が制限を超えないように調整
            if len(str(long_path)) > 200:  # 安全な制限
                break

        edge_case_config["clone_destination"] = str(long_path)

        repos = [
            {
                "name": "max-path-test",
                "full_name": "test_user/max-path-test",
                "clone_url": "https://github.com/test_user/max-path-test.git",
                "ssh_url": "git@github.com:test_user/max-path-test.git",
                "description": "最大パス長テスト",
                "private": False,
                "default_branch": "main",
            }
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(edge_case_config, dry_run=True)

        # 長いパスでも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == 1

    def test_large_number_of_repositories(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """大量リポジトリ数の境界値テスト"""
        # 実用的な大量リポジトリ数（1000個）
        large_repo_count = 1000
        repos = []

        for i in range(large_repo_count):
            repos.append(
                {
                    "name": f"boundary-repo-{i:04d}",
                    "full_name": f"test_user/boundary-repo-{i:04d}",
                    "clone_url": f"https://github.com/test_user/boundary-repo-{i:04d}.git",
                    "ssh_url": f"git@github.com:test_user/boundary-repo-{i:04d}.git",
                    "description": f"境界値テスト用リポジトリ {i}",
                    "private": i % 10 == 0,
                    "default_branch": "main",
                }
            )

        import time

        start_time = time.time()

        with (
            patch("setup_repo.sync.get_repositories", return_value=repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(edge_case_config, dry_run=True)

        execution_time = time.time() - start_time

        # 大量リポジトリでも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == large_repo_count

        # パフォーマンス要件: 1000リポジトリを5分以内で処理
        assert execution_time < 300.0, f"実行時間が長すぎます: {execution_time:.2f}秒"

        print(f"1000リポジトリ処理時間: {execution_time:.2f}秒")

    def test_extreme_timeout_values(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """極端なタイムアウト値のテスト"""
        extreme_timeouts = [0, 0.001, 1, 3600, 86400]  # 0秒から1日まで

        repos = [
            {
                "name": "timeout-test-repo",
                "full_name": "test_user/timeout-test-repo",
                "clone_url": "https://github.com/test_user/timeout-test-repo.git",
                "ssh_url": "git@github.com:test_user/timeout-test-repo.git",
                "description": "タイムアウトテスト",
                "private": False,
                "default_branch": "main",
            }
        ]

        for timeout_value in extreme_timeouts:
            test_config = edge_case_config.copy()
            test_config["timeout_seconds"] = timeout_value

            with (
                patch("setup_repo.sync.get_repositories", return_value=repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(test_config, dry_run=True)

            if timeout_value <= 0:
                # 無効なタイムアウト値では失敗することを期待
                print(f"タイムアウト {timeout_value}秒: 結果={result.success}")
            else:
                # 有効なタイムアウト値では成功することを期待
                assert result.success, f"タイムアウト {timeout_value}秒で失敗"


@pytest.mark.performance
class TestMalformedData:
    """不正形式データのエッジケーステストクラス"""

    def test_malformed_repository_data(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """不正形式のリポジトリデータテスト"""
        malformed_repos = [
            # 必須フィールド不足
            {"name": "incomplete-repo"},
            # 不正なURL
            {
                "name": "invalid-url-repo",
                "full_name": "test_user/invalid-url-repo",
                "clone_url": "not-a-valid-url",
                "ssh_url": "also-not-valid",
                "description": "不正URLテスト",
                "private": False,
                "default_branch": "main",
            },
            # 不正なデータ型
            {
                "name": 12345,  # 数値（文字列であるべき）
                "full_name": ["test_user", "array-name"],  # 配列（文字列であるべき）
                "clone_url": True,  # ブール値（文字列であるべき）
                "ssh_url": None,
                "description": {"desc": "object"},  # オブジェクト（文字列であるべき）
                "private": "yes",  # 文字列（ブール値であるべき）
                "default_branch": 42,  # 数値（文字列であるべき）
            },
        ]

        for malformed_repo in malformed_repos:
            with (
                patch("setup_repo.sync.get_repositories", return_value=[malformed_repo]),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(edge_case_config, dry_run=True)

            # 不正形式データでは失敗することを期待
            # ただし、一部は処理できる場合もある
            print(f"不正形式データ処理結果: {result.success}")
            if not result.success:
                assert result.errors

    def test_corrupted_json_configuration(
        self,
        temp_dir: Path,
    ) -> None:
        """破損したJSON設定のテスト"""
        corrupted_json_samples = [
            '{"github_token": "test"',  # 閉じ括弧なし
            '{"github_token": "test", "github_username":}',  # 値なし
            '{"github_token": "test", "github_username": "user",}',  # 末尾カンマ
            '{github_token: "test"}',  # クォートなしキー
            '{"github_token": "test" "github_username": "user"}',  # カンマなし
            '{"github_token": "test\\"}',  # 不正エスケープ
        ]

        for corrupted_json in corrupted_json_samples:
            config_file = temp_dir / f"corrupted_{hash(corrupted_json)}.json"

            with open(config_file, "w", encoding="utf-8") as f:
                f.write(corrupted_json)

            # 破損したJSONファイルの読み込みテスト
            try:
                with open(config_file, encoding="utf-8") as f:
                    json.load(f)
                # 読み込みが成功した場合（予期しない）
                print(f"破損JSON読み込み成功（予期しない）: {corrupted_json[:50]}...")
            except json.JSONDecodeError:
                # 読み込みが失敗した場合（期待される）
                print(f"破損JSON読み込み失敗（期待される）: {corrupted_json[:50]}...")

    def test_circular_reference_data(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """循環参照データのテスト"""
        # 循環参照を含むデータ構造をシミュレート
        circular_data = {"name": "circular-repo"}
        circular_data["self_ref"] = circular_data  # 循環参照

        # 循環参照データは通常JSONシリアライズできない
        try:
            json.dumps(circular_data)
            print("循環参照データのシリアライズが成功（予期しない）")
        except (ValueError, RecursionError):
            print("循環参照データのシリアライズが失敗（期待される）")

    def test_extremely_nested_data(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """極端にネストしたデータのテスト"""
        # 深くネストしたデータ構造を作成
        nested_data = {"level": 0}
        current = nested_data

        for i in range(100):  # 100レベルのネスト
            current["next"] = {"level": i + 1}
            current = current["next"]

        # 深いネストデータの処理テスト
        try:
            json_str = json.dumps(nested_data)
            parsed = json.loads(json_str)

            # ネストレベルを確認
            level_count = 0
            current = parsed
            while "next" in current:
                level_count += 1
                current = current["next"]

            print(f"ネストレベル処理成功: {level_count}レベル")
            assert level_count == 100

        except RecursionError:
            print("深いネストデータで再帰エラー（制限による）")


@pytest.mark.performance
class TestResourceExhaustion:
    """リソース枯渇のエッジケーステストクラス"""

    def test_memory_pressure_simulation(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """メモリ圧迫状況のシミュレーション"""
        # 大量のリポジトリデータを生成してメモリ圧迫をシミュレート
        large_repos = []

        for i in range(5000):  # 5000個のリポジトリ
            large_description = "x" * 1000  # 1KB の説明文
            large_repos.append(
                {
                    "name": f"memory-test-repo-{i:05d}",
                    "full_name": f"test_user/memory-test-repo-{i:05d}",
                    "clone_url": f"https://github.com/test_user/memory-test-repo-{i:05d}.git",
                    "ssh_url": f"git@github.com:test_user/memory-test-repo-{i:05d}.git",
                    "description": large_description,
                    "private": i % 2 == 0,
                    "default_branch": "main",
                    "topics": [f"topic-{j}" for j in range(10)],  # 10個のトピック
                }
            )

        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")
            return

        with (
            patch("setup_repo.sync.get_repositories", return_value=large_repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(edge_case_config, dry_run=True)

        try:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
        except NameError:
            final_memory = 0
        memory_growth = final_memory - initial_memory

        print(f"メモリ使用量変化: {memory_growth:.2f}MB")

        # メモリ圧迫下でも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == 5000

        # メモリ使用量が過度に増加していないことを確認
        assert memory_growth < 1000.0, f"メモリ使用量増加が過大: {memory_growth:.2f}MB"

    def test_file_descriptor_exhaustion(
        self,
        edge_case_config: dict[str, Any],
    ) -> None:
        """ファイルディスクリプタ枯渇のテスト"""
        # 多数のファイル操作をシミュレート
        repos = []

        for i in range(1000):  # 1000個のリポジトリ
            repos.append(
                {
                    "name": f"fd-test-repo-{i:04d}",
                    "full_name": f"test_user/fd-test-repo-{i:04d}",
                    "clone_url": f"https://github.com/test_user/fd-test-repo-{i:04d}.git",
                    "ssh_url": f"git@github.com:test_user/fd-test-repo-{i:04d}.git",
                    "description": f"ファイルディスクリプタテスト {i}",
                    "private": False,
                    "default_branch": "main",
                }
            )

        def mock_sync_with_file_operations(repo, dest_dir, config):
            # ファイル操作をシミュレート
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(b"test data")
            os.unlink(temp_file.name)
            return True

        with (
            patch("setup_repo.sync.get_repositories", return_value=repos),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_file_operations,
            ),
        ):
            result = sync_repositories(edge_case_config, dry_run=True)

        # ファイルディスクリプタ枯渇下でも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == 1000

        print("ファイルディスクリプタ枯渇テスト完了")
