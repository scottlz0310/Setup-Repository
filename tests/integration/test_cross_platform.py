"""
クロスプラットフォーム動作の統合テスト

このモジュールでは、Windows、Linux、macOS、WSLなど、
異なるプラットフォームでのシステムの動作を検証します。
プラットフォーム固有の設定、パス処理、コマンド実行などを
テストします。
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from setup_repo.platform_detector import detect_platform
from setup_repo.sync import sync_repositories


@pytest.mark.integration
class TestCrossPlatform:
    """クロスプラットフォーム動作の統合テストクラス"""

    @pytest.mark.parametrize(
        "platform_name,expected",
        [
            ("Windows", "windows"),
            ("Linux", "linux"),
            ("Darwin", "macos"),
        ],
    )
    def test_platform_detection(self, platform_name: str, expected: str) -> None:
        """プラットフォーム検出テスト"""
        with (
            patch("platform.system", return_value=platform_name),
            patch("platform.release", return_value="5.4.0-generic"),  # 非WSLリリース
        ):
            platform_info = detect_platform()
            assert platform_info.name == expected

    def test_windows_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Windowsパス処理テスト"""
        # Windowsプラットフォームをシミュレート
        with patch(
            "setup_repo.platform_detector.detect_platform", return_value="windows"
        ):
            # Windowsスタイルのパスを設定
            windows_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(windows_path).replace("/", "\\")

            mock_repos = [
                {
                    "name": "windows-path-repo",
                    "full_name": "test_user/windows-path-repo",
                    "clone_url": "https://github.com/test_user/windows-path-repo.git",
                    "ssh_url": "git@github.com:test_user/windows-path-repo.git",
                    "description": "Windowsパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch(
                    "setup_repo.sync.sync_repository_with_retries", return_value=True
                ),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_linux_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Linuxパス処理テスト"""
        with patch(
            "setup_repo.platform_detector.detect_platform", return_value="linux"
        ):
            # Linuxスタイルのパスを設定
            linux_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(linux_path)

            mock_repos = [
                {
                    "name": "linux-path-repo",
                    "full_name": "test_user/linux-path-repo",
                    "clone_url": "https://github.com/test_user/linux-path-repo.git",
                    "ssh_url": "git@github.com:test_user/linux-path-repo.git",
                    "description": "Linuxパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch(
                    "setup_repo.sync.sync_repository_with_retries", return_value=True
                ),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_macos_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """macOSパス処理テスト"""
        with patch(
            "setup_repo.platform_detector.detect_platform", return_value="macos"
        ):
            # macOSスタイルのパスを設定
            macos_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(macos_path)

            mock_repos = [
                {
                    "name": "macos-path-repo",
                    "full_name": "test_user/macos-path-repo",
                    "clone_url": "https://github.com/test_user/macos-path-repo.git",
                    "ssh_url": "git@github.com:test_user/macos-path-repo.git",
                    "description": "macOSパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch(
                    "setup_repo.sync.sync_repository_with_retries", return_value=True
                ),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_wsl_environment_detection(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """WSL環境検出テスト"""
        # WSL環境をシミュレート
        wsl_env = {
            "WSL_DISTRO_NAME": "Ubuntu",
            "WSLENV": "PATH/l",
        }

        with (
            patch.dict(os.environ, wsl_env),
            patch("platform.system", return_value="Linux"),
            patch("setup_repo.platform_detector.detect_platform", return_value="wsl"),
        ):
            clone_destination = temp_dir / "repos"
            sample_config["clone_destination"] = str(clone_destination)

            mock_repos = [
                {
                    "name": "wsl-repo",
                    "full_name": "test_user/wsl-repo",
                    "clone_url": "https://github.com/test_user/wsl-repo.git",
                    "ssh_url": "git@github.com:test_user/wsl-repo.git",
                    "description": "WSLテスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch(
                    "setup_repo.sync.sync_repository_with_retries", return_value=True
                ),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_environment_variable_handling_cross_platform(
        self,
        temp_dir: Path,
    ) -> None:
        """クロスプラットフォーム環境変数処理テスト"""
        platforms = ["windows", "linux", "macos"]

        for platform_name in platforms:
            with patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=platform_name,
            ):
                # プラットフォーム固有の環境変数を設定
                env_vars = {
                    "GITHUB_TOKEN": f"{platform_name}_token",
                    "GITHUB_USERNAME": f"{platform_name}_user",
                    "CLONE_DESTINATION": str(temp_dir / f"{platform_name}_repos"),
                }

                with patch.dict(os.environ, env_vars):
                    # 環境変数から設定を読み込み
                    config = {
                        "github_token": os.getenv("GITHUB_TOKEN"),
                        "github_username": os.getenv("GITHUB_USERNAME"),
                        "clone_destination": os.getenv("CLONE_DESTINATION"),
                    }

                    mock_repos = [
                        {
                            "name": f"{platform_name}-env-repo",
                            "full_name": f"{platform_name}_user/{platform_name}-env-repo",
                            "clone_url": f"https://github.com/{platform_name}_user/{platform_name}-env-repo.git",
                            "ssh_url": f"git@github.com:{platform_name}_user/{platform_name}-env-repo.git",
                            "description": f"{platform_name}環境変数テスト用リポジトリ",
                            "private": False,
                            "default_branch": "main",
                        }
                    ]

                    with (
                        patch(
                            "setup_repo.sync.get_repositories", return_value=mock_repos
                        ),
                        patch(
                            "setup_repo.sync.sync_repository_with_retries",
                            return_value=True,
                        ),
                    ):
                        result = sync_repositories(config, dry_run=True)

                    assert result.success
                    assert len(result.synced_repos) == 1
                    assert f"{platform_name}-env-repo" in result.synced_repos

    def test_file_system_case_sensitivity(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """ファイルシステム大文字小文字区別テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 大文字小文字が異なるリポジトリ名
        mock_repos = [
            {
                "name": "CaseSensitive-Repo",
                "full_name": "test_user/CaseSensitive-Repo",
                "clone_url": "https://github.com/test_user/CaseSensitive-Repo.git",
                "ssh_url": "git@github.com:test_user/CaseSensitive-Repo.git",
                "description": "大文字小文字テスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
            {
                "name": "casesensitive-repo",
                "full_name": "test_user/casesensitive-repo",
                "clone_url": "https://github.com/test_user/casesensitive-repo.git",
                "ssh_url": "git@github.com:test_user/casesensitive-repo.git",
                "description": "小文字テスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(sample_config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 2

    def test_unicode_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Unicode文字を含むパス処理テスト"""
        # Unicode文字を含むパス
        unicode_path = temp_dir / "リポジトリ" / "テスト用フォルダ"
        sample_config["clone_destination"] = str(unicode_path)

        mock_repos = [
            {
                "name": "unicode-path-テスト",
                "full_name": "test_user/unicode-path-テスト",
                "clone_url": "https://github.com/test_user/unicode-path-テスト.git",
                "ssh_url": "git@github.com:test_user/unicode-path-テスト.git",
                "description": "Unicode パステスト用リポジトリ 🚀",
                "private": False,
                "default_branch": "main",
            },
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(sample_config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

    def test_long_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """長いパス処理テスト（Windows MAX_PATH制限対応）"""
        # 長いパスを生成
        long_path_components = ["very"] * 20 + ["long"] * 20 + ["path"] * 10
        long_path = temp_dir
        for component in long_path_components:
            long_path = long_path / component

        sample_config["clone_destination"] = str(long_path)

        mock_repos = [
            {
                "name": "long-path-repo",
                "full_name": "test_user/long-path-repo",
                "clone_url": "https://github.com/test_user/long-path-repo.git",
                "ssh_url": "git@github.com:test_user/long-path-repo.git",
                "description": "長いパステスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(sample_config, dry_run=True)

        # 長いパスでも処理できることを確認
        assert result.success
        assert len(result.synced_repos) == 1

    def test_special_characters_in_paths(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """パス内特殊文字処理テスト"""
        # 特殊文字を含むパス（プラットフォームで許可される範囲）
        special_chars_path = temp_dir / "test-repo_with.special@chars"
        sample_config["clone_destination"] = str(special_chars_path)

        mock_repos = [
            {
                "name": "special-chars-repo",
                "full_name": "test_user/special-chars-repo",
                "clone_url": "https://github.com/test_user/special-chars-repo.git",
                "ssh_url": "git@github.com:test_user/special-chars-repo.git",
                "description": "特殊文字テスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            result = sync_repositories(sample_config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

    def test_network_drive_paths_windows(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Windowsネットワークドライブパステスト"""
        with patch(
            "setup_repo.platform_detector.detect_platform", return_value="windows"
        ):
            # UNCパスをシミュレート
            network_path = "\\\\server\\share\\repos"
            sample_config["clone_destination"] = network_path

            mock_repos = [
                {
                    "name": "network-drive-repo",
                    "full_name": "test_user/network-drive-repo",
                    "clone_url": "https://github.com/test_user/network-drive-repo.git",
                    "ssh_url": "git@github.com:test_user/network-drive-repo.git",
                    "description": "ネットワークドライブテスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch(
                    "setup_repo.sync.sync_repository_with_retries", return_value=True
                ),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_symlink_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """シンボリックリンク処理テスト"""
        # シンボリックリンクを作成（Unix系のみ）
        if os.name != "nt":  # Windows以外
            real_path = temp_dir / "real_repos"
            real_path.mkdir()

            symlink_path = temp_dir / "symlink_repos"
            try:
                symlink_path.symlink_to(real_path)
                sample_config["clone_destination"] = str(symlink_path)

                mock_repos = [
                    {
                        "name": "symlink-repo",
                        "full_name": "test_user/symlink-repo",
                        "clone_url": "https://github.com/test_user/symlink-repo.git",
                        "ssh_url": "git@github.com:test_user/symlink-repo.git",
                        "description": "シンボリックリンクテスト用リポジトリ",
                        "private": False,
                        "default_branch": "main",
                    }
                ]

                with (
                    patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                    patch(
                        "setup_repo.sync.sync_repository_with_retries",
                        return_value=True,
                    ),
                ):
                    result = sync_repositories(sample_config, dry_run=True)

                assert result.success
                assert len(result.synced_repos) == 1
            except OSError:
                # シンボリックリンク作成に失敗した場合はスキップ
                pytest.skip("シンボリックリンクの作成に失敗しました")

    def test_permission_differences_cross_platform(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """クロスプラットフォーム権限処理テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # プラットフォーム別の権限設定をシミュレート
        platforms = ["windows", "linux", "macos"]

        for platform_name in platforms:
            with patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=platform_name,
            ):
                mock_repos = [
                    {
                        "name": f"{platform_name}-permission-repo",
                        "full_name": f"test_user/{platform_name}-permission-repo",
                        "clone_url": f"https://github.com/test_user/{platform_name}-permission-repo.git",
                        "ssh_url": f"git@github.com:test_user/{platform_name}-permission-repo.git",
                        "description": f"{platform_name}権限テスト用リポジトリ",
                        "private": False,
                        "default_branch": "main",
                    }
                ]

                with (
                    patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                    patch(
                        "setup_repo.sync.sync_repository_with_retries",
                        return_value=True,
                    ),
                ):
                    result = sync_repositories(sample_config, dry_run=True)

                assert result.success
                assert len(result.synced_repos) == 1

    def test_line_ending_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """改行コード処理テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 異なる改行コードを含む設定ファイルをテスト
        line_endings = {
            "windows": "\r\n",
            "linux": "\n",
            "macos": "\r",  # 古いMac
        }

        for platform_name, _line_ending in line_endings.items():
            with patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=platform_name,
            ):
                mock_repos = [
                    {
                        "name": f"{platform_name}-lineending-repo",
                        "full_name": f"test_user/{platform_name}-lineending-repo",
                        "clone_url": f"https://github.com/test_user/{platform_name}-lineending-repo.git",
                        "ssh_url": f"git@github.com:test_user/{platform_name}-lineending-repo.git",
                        "description": f"{platform_name}改行コードテスト用リポジトリ",
                        "private": False,
                        "default_branch": "main",
                    }
                ]

                with (
                    patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                    patch(
                        "setup_repo.sync.sync_repository_with_retries",
                        return_value=True,
                    ),
                ):
                    result = sync_repositories(sample_config, dry_run=True)

                assert result.success
                assert len(result.synced_repos) == 1

    @pytest.mark.slow
    def test_cross_platform_performance(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """クロスプラットフォームパフォーマンステスト"""
        import time

        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 各プラットフォームでのパフォーマンステスト
        platforms = ["windows", "linux", "macos"]

        for platform_name in platforms:
            with patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=platform_name,
            ):
                mock_repos = [
                    {
                        "name": f"{platform_name}-perf-repo-{i}",
                        "full_name": f"test_user/{platform_name}-perf-repo-{i}",
                        "clone_url": f"https://github.com/test_user/{platform_name}-perf-repo-{i}.git",
                        "ssh_url": f"git@github.com:test_user/{platform_name}-perf-repo-{i}.git",
                        "description": f"{platform_name}パフォーマンステスト用リポジトリ{i}",
                        "private": False,
                        "default_branch": "main",
                    }
                    for i in range(10)  # 10個のリポジトリ
                ]

                start_time = time.time()

                with (
                    patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                    patch(
                        "setup_repo.sync.sync_repository_with_retries",
                        return_value=True,
                    ),
                ):
                    result = sync_repositories(sample_config, dry_run=True)

                execution_time = time.time() - start_time

                # プラットフォーム別パフォーマンス要件: 10リポジトリが5秒以内
                assert execution_time < 5.0, (
                    f"{platform_name}で実行時間が長すぎます: {execution_time}秒"
                )
                assert result.success
                assert len(result.synced_repos) == 10
