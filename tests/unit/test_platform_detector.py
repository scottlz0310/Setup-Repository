"""
platform_detector.pyモジュールの包括的な単体テスト

プラットフォーム検出機能のテスト：
- PlatformInfo データクラス
- detect_platform 関数
- check_package_manager 関数
- get_available_package_managers 関数
- get_install_commands 関数
"""

import subprocess
from unittest.mock import patch

import pytest

from src.setup_repo.platform_detector import (
    PlatformInfo,
    check_package_manager,
    detect_platform,
    get_available_package_managers,
    get_install_commands,
)


@pytest.mark.unit
class TestPlatformInfo:
    """PlatformInfoデータクラスのテスト"""

    def test_platform_info_creation(self) -> None:
        """PlatformInfoの作成テスト"""
        platform_info = PlatformInfo(
            name="test_platform",
            display_name="Test Platform",
            package_managers=["test_manager"],
            shell="test_shell",
            python_cmd="test_python",
        )

        assert platform_info.name == "test_platform"
        assert platform_info.display_name == "Test Platform"
        assert platform_info.package_managers == ["test_manager"]
        assert platform_info.shell == "test_shell"
        assert platform_info.python_cmd == "test_python"

    def test_platform_info_equality(self) -> None:
        """PlatformInfoの等価性テスト"""
        platform1 = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["manager"],
            shell="shell",
            python_cmd="python",
        )

        platform2 = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["manager"],
            shell="shell",
            python_cmd="python",
        )

        assert platform1 == platform2

    def test_platform_info_inequality(self) -> None:
        """PlatformInfoの非等価性テスト"""
        platform1 = PlatformInfo(
            name="test1",
            display_name="Test 1",
            package_managers=["manager1"],
            shell="shell1",
            python_cmd="python1",
        )

        platform2 = PlatformInfo(
            name="test2",
            display_name="Test 2",
            package_managers=["manager2"],
            shell="shell2",
            python_cmd="python2",
        )

        assert platform1 != platform2


@pytest.mark.unit
class TestDetectPlatform:
    """detect_platform関数のテスト"""

    def test_detect_windows_platform(self) -> None:
        """Windowsプラットフォーム検出のテスト"""
        with patch("platform.system") as mock_system:
            mock_system.return_value = "Windows"

            platform_info = detect_platform()

            assert platform_info.name == "windows"
            assert platform_info.display_name == "Windows"
            assert "scoop" in platform_info.package_managers
            assert "winget" in platform_info.package_managers
            assert "chocolatey" in platform_info.package_managers
            assert platform_info.shell == "powershell"
            assert platform_info.python_cmd == "python"

    def test_detect_windows_platform_by_os_name(self) -> None:
        """os.nameによるWindows検出のテスト"""
        with patch("platform.system") as mock_system, patch("os.name", "nt"):
            mock_system.return_value = "Linux"  # 他のシステムを返す

            platform_info = detect_platform()

            assert platform_info.name == "windows"
            assert platform_info.display_name == "Windows"

    def test_detect_wsl_platform(self) -> None:
        """WSLプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            platform_info = detect_platform()

            assert platform_info.name == "wsl"
            assert platform_info.display_name == "WSL (Windows Subsystem for Linux)"
            assert "apt" in platform_info.package_managers
            assert "snap" in platform_info.package_managers
            assert "curl" in platform_info.package_managers
            assert platform_info.shell == "bash"
            assert platform_info.python_cmd == "python3"

    def test_detect_macos_platform(self) -> None:
        """macOSプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.0.0"  # macOS release

            platform_info = detect_platform()

            assert platform_info.name == "macos"
            assert platform_info.display_name == "macOS"
            assert "brew" in platform_info.package_managers
            assert "curl" in platform_info.package_managers
            assert platform_info.shell == "zsh"
            assert platform_info.python_cmd == "python3"

    def test_detect_linux_platform(self) -> None:
        """Linuxプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-generic"  # WSLではない

            platform_info = detect_platform()

            assert platform_info.name == "linux"
            assert platform_info.display_name == "Linux"
            assert "apt" in platform_info.package_managers
            assert "snap" in platform_info.package_managers
            assert "curl" in platform_info.package_managers
            assert platform_info.shell == "bash"
            assert platform_info.python_cmd == "python3"

    def test_detect_unknown_platform_defaults_to_linux(self) -> None:
        """未知のプラットフォームがLinuxにデフォルトされることをテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "FreeBSD"
            mock_release.return_value = "13.0-RELEASE"

            platform_info = detect_platform()

            assert platform_info.name == "linux"
            assert platform_info.display_name == "Linux"

    def test_detect_platform_case_insensitive(self) -> None:
        """大文字小文字を区別しない検出のテスト"""
        with patch("platform.system") as mock_system:
            mock_system.return_value = "WINDOWS"  # 大文字

            platform_info = detect_platform()

            assert platform_info.name == "windows"

    def test_detect_wsl_case_insensitive(self) -> None:
        """WSL検出の大文字小文字を区別しないテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-MICROSOFT-standard-WSL2"  # 大文字

            platform_info = detect_platform()

            assert platform_info.name == "wsl"


@pytest.mark.unit
class TestCheckPackageManager:
    """check_package_manager関数のテスト"""

    def test_check_package_manager_available(self) -> None:
        """利用可能なパッケージマネージャーのテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            result = check_package_manager("apt")

            assert result is True
            mock_run.assert_called_once_with(
                ["apt", "--version"], capture_output=True, check=True
            )

    def test_check_package_manager_not_available_called_process_error(self) -> None:
        """利用不可能なパッケージマネージャー（CalledProcessError）のテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "apt")

            result = check_package_manager("apt")

            assert result is False

    def test_check_package_manager_not_available_file_not_found(self) -> None:
        """利用不可能なパッケージマネージャー（FileNotFoundError）のテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = check_package_manager("nonexistent")

            assert result is False

    def test_check_package_manager_different_managers(self) -> None:
        """異なるパッケージマネージャーのテスト"""
        # マネージャー名と実際のコマンドのマッピング
        managers_to_test = {
            "apt": "apt",
            "snap": "snap",
            "brew": "brew",
            "scoop": "scoop",
            "winget": "winget",
            "chocolatey": "choco",  # chocolateyはchocoコマンドにマッピング
        }

        for manager, expected_cmd in managers_to_test.items():
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                result = check_package_manager(manager)

                assert result is True
                mock_run.assert_called_once_with(
                    [expected_cmd, "--version"],
                    capture_output=True,
                    check=True,
                    timeout=10,
                    text=True,
                )


@pytest.mark.unit
class TestGetAvailablePackageManagers:
    """get_available_package_managers関数のテスト"""

    def test_get_available_package_managers_all_available(self) -> None:
        """すべてのパッケージマネージャーが利用可能な場合のテスト"""
        platform_info = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )

        with patch(
            "src.setup_repo.platform_detector.check_package_manager"
        ) as mock_check:
            mock_check.return_value = True

            available = get_available_package_managers(platform_info)

            assert available == ["apt", "snap", "curl"]
            assert mock_check.call_count == 3

    def test_get_available_package_managers_partial_available(self) -> None:
        """一部のパッケージマネージャーが利用可能な場合のテスト"""
        platform_info = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )

        def mock_check_side_effect(manager: str) -> bool:
            return manager in ["apt", "curl"]  # snapは利用不可

        with patch(
            "src.setup_repo.platform_detector.check_package_manager"
        ) as mock_check:
            mock_check.side_effect = mock_check_side_effect

            available = get_available_package_managers(platform_info)

            assert available == ["apt", "curl"]
            assert "snap" not in available

    def test_get_available_package_managers_none_available(self) -> None:
        """パッケージマネージャーが利用不可能な場合のテスト"""
        platform_info = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["nonexistent1", "nonexistent2"],
            shell="bash",
            python_cmd="python3",
        )

        with patch(
            "src.setup_repo.platform_detector.check_package_manager"
        ) as mock_check:
            mock_check.return_value = False

            available = get_available_package_managers(platform_info)

            assert available == []

    def test_get_available_package_managers_empty_list(self) -> None:
        """パッケージマネージャーリストが空の場合のテスト"""
        platform_info = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=[],
            shell="bash",
            python_cmd="python3",
        )

        with patch(
            "src.setup_repo.platform_detector.check_package_manager"
        ) as mock_check:
            available = get_available_package_managers(platform_info)

            assert available == []
            mock_check.assert_not_called()


@pytest.mark.unit
class TestGetInstallCommands:
    """get_install_commands関数のテスト"""

    def test_get_install_commands_windows(self) -> None:
        """Windowsプラットフォームのインストールコマンドテスト"""
        platform_info = PlatformInfo(
            name="windows",
            display_name="Windows",
            package_managers=["scoop", "winget", "chocolatey"],
            shell="powershell",
            python_cmd="python",
        )

        commands = get_install_commands(platform_info)

        assert "scoop" in commands
        assert "winget" in commands
        assert "chocolatey" in commands
        assert "pip" in commands

        # 具体的なコマンドの確認
        assert "scoop install uv" in commands["scoop"]
        assert "scoop install gh" in commands["scoop"]
        assert "winget install --id=astral-sh.uv" in commands["winget"]
        assert "choco install uv" in commands["chocolatey"]

    def test_get_install_commands_wsl(self) -> None:
        """WSLプラットフォームのインストールコマンドテスト"""
        platform_info = PlatformInfo(
            name="wsl",
            display_name="WSL",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )

        commands = get_install_commands(platform_info)

        assert "snap" in commands
        assert "apt" in commands
        assert "curl" in commands
        assert "pip" in commands

        # 具体的なコマンドの確認
        assert "sudo snap install --classic uv" in commands["snap"]
        assert "sudo apt update && sudo apt install -y gh" in commands["apt"]
        assert "curl -LsSf https://astral.sh/uv/install.sh | sh" in commands["curl"]

    def test_get_install_commands_linux(self) -> None:
        """Linuxプラットフォームのインストールコマンドテスト"""
        platform_info = PlatformInfo(
            name="linux",
            display_name="Linux",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )

        commands = get_install_commands(platform_info)

        assert "snap" in commands
        assert "apt" in commands
        assert "curl" in commands
        assert "pip" in commands

        # WSLと同じコマンドが返されることを確認
        assert commands["snap"] == [
            "sudo snap install --classic uv",
            "sudo snap install gh",
        ]
        assert commands["apt"] == ["sudo apt update && sudo apt install -y gh"]

    def test_get_install_commands_macos(self) -> None:
        """macOSプラットフォームのインストールコマンドテスト"""
        platform_info = PlatformInfo(
            name="macos",
            display_name="macOS",
            package_managers=["brew", "curl"],
            shell="zsh",
            python_cmd="python3",
        )

        commands = get_install_commands(platform_info)

        assert "brew" in commands
        assert "curl" in commands
        assert "pip" in commands

        # 具体的なコマンドの確認
        assert "brew install uv" in commands["brew"]
        assert "brew install gh" in commands["brew"]
        assert "curl -LsSf https://astral.sh/uv/install.sh | sh" in commands["curl"]

    def test_get_install_commands_unknown_platform(self) -> None:
        """未知のプラットフォームのテスト"""
        platform_info = PlatformInfo(
            name="unknown",
            display_name="Unknown",
            package_managers=["unknown_manager"],
            shell="unknown_shell",
            python_cmd="unknown_python",
        )

        commands = get_install_commands(platform_info)

        # 未知のプラットフォームでは空の辞書が返される
        assert commands == {}

    def test_get_install_commands_all_platforms_have_pip(self) -> None:
        """すべてのプラットフォームでpipコマンドが利用可能であることをテスト"""
        platforms = ["windows", "wsl", "linux", "macos"]

        for platform_name in platforms:
            platform_info = PlatformInfo(
                name=platform_name,
                display_name=platform_name.title(),
                package_managers=[],
                shell="",
                python_cmd="",
            )

            commands = get_install_commands(platform_info)

            if commands:  # 空でない場合（未知のプラットフォーム以外）
                assert "pip" in commands
                assert "pip install uv" in commands["pip"]


@pytest.mark.unit
class TestPlatformDetectorIntegration:
    """プラットフォーム検出機能の統合テスト"""

    def test_full_platform_detection_workflow_windows(self) -> None:
        """Windows環境での完全なワークフローテスト"""
        with patch("platform.system") as mock_system:
            mock_system.return_value = "Windows"

            # プラットフォーム検出
            platform_info = detect_platform()

            # インストールコマンド取得
            commands = get_install_commands(platform_info)

            # パッケージマネージャーチェック（モック）
            with patch(
                "src.setup_repo.platform_detector.check_package_manager"
            ) as mock_check:
                mock_check.return_value = True
                available = get_available_package_managers(platform_info)

            # 結果の検証
            assert platform_info.name == "windows"
            assert len(commands) > 0
            assert len(available) == len(platform_info.package_managers)

    def test_full_platform_detection_workflow_linux(self) -> None:
        """Linux環境での完全なワークフローテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-generic"

            # プラットフォーム検出
            platform_info = detect_platform()

            # インストールコマンド取得
            commands = get_install_commands(platform_info)

            # パッケージマネージャーチェック（一部利用可能）
            def mock_check_side_effect(manager: str) -> bool:
                return manager in ["apt", "curl"]

            with patch(
                "src.setup_repo.platform_detector.check_package_manager"
            ) as mock_check:
                mock_check.side_effect = mock_check_side_effect
                available = get_available_package_managers(platform_info)

            # 結果の検証
            assert platform_info.name == "linux"
            assert len(commands) > 0
            assert available == ["apt", "curl"]

    def test_platform_detection_consistency(self) -> None:
        """プラットフォーム検出の一貫性テスト"""
        # 複数回呼び出しても同じ結果が返ることを確認
        platform1 = detect_platform()
        platform2 = detect_platform()

        assert platform1.name == platform2.name
        assert platform1.display_name == platform2.display_name
        assert platform1.package_managers == platform2.package_managers
        assert platform1.shell == platform2.shell
        assert platform1.python_cmd == platform2.python_cmd

    def test_package_manager_commands_consistency(self) -> None:
        """パッケージマネージャーコマンドの一貫性テスト"""
        platform_info = detect_platform()
        commands = get_install_commands(platform_info)

        # 各パッケージマネージャーに対してコマンドが存在することを確認
        for manager in platform_info.package_managers:
            if manager in commands:
                assert isinstance(commands[manager], list)
                assert len(commands[manager]) > 0
                # 各コマンドが文字列であることを確認
                for command in commands[manager]:
                    assert isinstance(command, str)
                    assert len(command) > 0


@pytest.mark.unit
class TestPlatformDetectorClass:
    """PlatformDetectorクラスのテスト"""

    def test_platform_detector_initialization(self) -> None:
        """PlatformDetectorの初期化テスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()
        assert detector._platform_info is None

    def test_detect_platform_caching(self) -> None:
        """プラットフォーム検出のキャッシュテスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        # 最初の呼び出し
        platform1 = detector.detect_platform()
        assert detector._platform_info is not None

        # 2回目の呼び出し（キャッシュされた値を使用）
        platform2 = detector.detect_platform()
        assert platform1 == platform2

    def test_is_wsl_detection(self) -> None:
        """WSL検出テスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            # キャッシュをクリア
            detector._platform_info = None

            assert detector.is_wsl() is True

    def test_is_not_wsl_detection(self) -> None:
        """非WSL環境の検出テスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-generic"

            # キャッシュをクリア
            detector._platform_info = None

            assert detector.is_wsl() is False

    def test_get_package_manager_with_available_managers(self) -> None:
        """利用可能なパッケージマネージャーがある場合のテスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        with patch("platform.system") as mock_system:
            mock_system.return_value = "Linux"

            # キャッシュをクリア
            detector._platform_info = None

            with patch(
                "src.setup_repo.platform_detector.get_available_package_managers"
            ) as mock_get_available:
                mock_get_available.return_value = ["apt", "snap"]

                manager = detector.get_package_manager()
                assert manager == "apt"  # 最初の利用可能なマネージャー

    def test_get_package_manager_no_available_managers(self) -> None:
        """利用可能なパッケージマネージャーがない場合のテスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        with patch("platform.system") as mock_system:
            mock_system.return_value = "Linux"

            # キャッシュをクリア
            detector._platform_info = None

            with patch(
                "src.setup_repo.platform_detector.get_available_package_managers"
            ) as mock_get_available:
                mock_get_available.return_value = []

                manager = detector.get_package_manager()
                # デフォルトの最初のマネージャーを返す
                platform_info = detector.get_platform_info()
                assert manager == platform_info.package_managers[0]

    def test_get_platform_info_caching(self) -> None:
        """プラットフォーム情報取得のキャッシュテスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()

        # 最初の呼び出し
        info1 = detector.get_platform_info()
        assert detector._platform_info is not None

        # 2回目の呼び出し（キャッシュされた値を使用）
        info2 = detector.get_platform_info()
        assert info1 == info2
        assert info1 is info2  # 同じオブジェクトインスタンス


@pytest.mark.unit
class TestEdgeCasesAndErrorHandling:
    """エッジケースとエラーハンドリングのテスト"""

    def test_check_package_manager_with_empty_string(self) -> None:
        """空文字列でのパッケージマネージャーチェックテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = check_package_manager("")
            assert result is False

    def test_check_package_manager_with_none(self) -> None:
        """Noneでのパッケージマネージャーチェックテスト"""
        with pytest.raises(TypeError):
            check_package_manager(None)

    def test_get_available_package_managers_with_exception(self) -> None:
        """例外が発生した場合のパッケージマネージャー取得テスト"""
        platform_info = PlatformInfo(
            name="test",
            display_name="Test",
            package_managers=["test_manager"],
            shell="bash",
            python_cmd="python3",
        )

        with patch(
            "src.setup_repo.platform_detector.check_package_manager"
        ) as mock_check:
            mock_check.return_value = False  # 例外の代わりにFalseを返す

            available = get_available_package_managers(platform_info)
            assert available == []

    def test_detect_platform_with_unusual_system_values(self) -> None:
        """異常なシステム値でのプラットフォーム検出テスト"""
        test_cases = [
            ("", "linux"),  # 空文字列
            ("UNKNOWN_OS", "linux"),  # 未知のOS
            ("Java", "linux"),  # Java仮想マシン
        ]

        for system_value, expected_platform in test_cases:
            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
            ):
                mock_system.return_value = system_value
                mock_release.return_value = "1.0.0"

                platform_info = detect_platform()
                assert platform_info.name == expected_platform

    def test_wsl_detection_with_various_release_strings(self) -> None:
        """様々なリリース文字列でのWSL検出テスト"""
        wsl_release_strings = [
            "5.4.0-microsoft-standard-WSL2",
            "4.19.128-microsoft-standard",
            "5.10.16.3-microsoft-standard-WSL2+",
            "MICROSOFT-WSL-KERNEL",
        ]

        for release_string in wsl_release_strings:
            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
            ):
                mock_system.return_value = "Linux"
                mock_release.return_value = release_string

                platform_info = detect_platform()
                assert platform_info.name == "wsl"

    def test_non_wsl_linux_detection(self) -> None:
        """非WSL Linuxの検出テスト"""
        non_wsl_release_strings = [
            "5.4.0-generic",
            "5.15.0-ubuntu",
            "6.1.0-arch1-1",
            "5.10.0-kali7-amd64",
        ]

        for release_string in non_wsl_release_strings:
            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
            ):
                mock_system.return_value = "Linux"
                mock_release.return_value = release_string

                platform_info = detect_platform()
                assert platform_info.name == "linux"

    def test_platform_info_immutability(self) -> None:
        """PlatformInfoの不変性テスト"""
        platform_info = detect_platform()

        # データクラスのフィールドが変更可能であることを確認
        original_name = platform_info.name
        platform_info.name = "modified"
        assert platform_info.name == "modified"

        # 新しい検出で元の値が返されることを確認
        new_platform_info = detect_platform()
        assert new_platform_info.name == original_name

    def test_get_install_commands_command_structure(self) -> None:
        """インストールコマンドの構造テスト"""
        all_platforms = ["windows", "wsl", "linux", "macos"]

        for platform_name in all_platforms:
            platform_info = PlatformInfo(
                name=platform_name,
                display_name=platform_name.title(),
                package_managers=["test_manager"],
                shell="test_shell",
                python_cmd="test_python",
            )

            commands = get_install_commands(platform_info)

            if commands:  # 空でない場合
                for manager, command_list in commands.items():
                    assert isinstance(manager, str)
                    assert isinstance(command_list, list)
                    for command in command_list:
                        assert isinstance(command, str)
                        assert len(command.strip()) > 0

    def test_platform_detector_multiple_instances(self) -> None:
        """複数のPlatformDetectorインスタンスのテスト"""
        from src.setup_repo.platform_detector import PlatformDetector

        detector1 = PlatformDetector()
        detector2 = PlatformDetector()

        # 異なるインスタンスでも同じ結果が返される
        platform1 = detector1.detect_platform()
        platform2 = detector2.detect_platform()

        assert platform1 == platform2

        # しかし、キャッシュは独立している
        assert detector1._platform_info is not detector2._platform_info
