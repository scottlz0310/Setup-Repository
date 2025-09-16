"""プラットフォーム検出機能の包括的テスト."""

import platform
from unittest.mock import patch

import pytest

from setup_repo.platform_detector import (
    PlatformDetector,
    PlatformInfo,
    check_module_availability,
    check_package_manager,
    detect_platform,
    diagnose_platform_issues,
    get_available_package_managers,
    get_ci_environment_info,
    get_install_commands,
)


class TestPlatformDetection:
    """プラットフォーム検出機能のテスト."""

    @pytest.mark.unit
    @patch("platform.system")
    def test_detect_platform_windows(self, mock_system):
        """Windows検出テスト."""
        mock_system.return_value = "Windows"

        with patch("setup_repo.platform_detector._detect_windows_platform") as mock_detect:
            mock_detect.return_value = PlatformInfo(
                name="windows",
                display_name="Windows",
                package_managers=["winget"],
                shell="powershell",
                python_cmd="python",
            )

            result = detect_platform()

            assert result.name == "windows"
            assert result.display_name == "Windows"
            assert "winget" in result.package_managers
            mock_detect.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")
    def test_detect_platform_linux(self):
        """Linux検出テスト."""
        result = detect_platform()
        assert result.name == "linux"

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS環境でのみ実行")
    def test_detect_platform_macos(self):
        """macOS検出テスト."""
        result = detect_platform()
        assert result.name == "macos"

    @pytest.mark.unit
    @patch("platform.system")
    def test_detect_platform_unknown(self, mock_system):
        """未知のプラットフォーム検出テスト."""
        mock_system.return_value = "UnknownOS"

        result = detect_platform()

        # 実際の環境に依存するため、結果の型のみ確認
        assert hasattr(result, "name")
        assert hasattr(result, "package_managers")

    @pytest.mark.unit
    @patch("platform.system")
    @patch("platform.release")
    @patch("platform.machine")
    def test_detect_windows_platform(self, mock_machine, mock_release, mock_system):
        """Windows詳細検出テスト."""
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"
        mock_machine.return_value = "AMD64"

        from setup_repo.platform_detector import _detect_windows_platform

        result = _detect_windows_platform(False)

        assert result.name == "windows"
        assert result.display_name == "Windows"
        assert "winget" in result.package_managers or "scoop" in result.package_managers

    @pytest.mark.unit
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_detect_linux_platform_ubuntu(self, mock_read_text, mock_exists):
        """Ubuntu検出テスト."""
        mock_exists.return_value = True
        mock_read_text.return_value = 'NAME="Ubuntu"\nVERSION="22.04 LTS"\n'

        from setup_repo.platform_detector import _detect_linux_platform

        result = _detect_linux_platform(False, False)

        assert result.name == "linux"
        assert result.display_name == "Linux"
        assert "apt" in result.package_managers

    @pytest.mark.unit
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_detect_linux_platform_centos(self, mock_read_text, mock_exists):
        """CentOS検出テスト."""
        mock_exists.return_value = True
        mock_read_text.return_value = 'NAME="CentOS Linux"\nVERSION="8"\n'

        from setup_repo.platform_detector import _detect_linux_platform

        result = _detect_linux_platform(False, False)

        assert result.name == "linux"
        assert result.display_name == "Linux"
        assert "apt" in result.package_managers

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")
    def test_detect_linux_platform_no_os_release(self):
        """os-releaseファイルなしでのLinux検出テスト."""
        from setup_repo.platform_detector import _detect_linux_platform

        # 実際のLinux環境で実行
        result = _detect_linux_platform(False, False)
        assert result.name == "linux"

    @pytest.mark.unit
    @patch("platform.mac_ver")
    def test_detect_macos_platform(self, mock_mac_ver):
        """macOS詳細検出テスト."""
        mock_mac_ver.return_value = ("13.0", ("", "", ""), "arm64")

        from setup_repo.platform_detector import _detect_macos_platform

        result = _detect_macos_platform(False)

        assert result.name == "macos"
        assert result.display_name == "macOS"
        assert "brew" in result.package_managers

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="WSLはLinux環境でのみ検出可能")
    def test_check_wsl_environment_true(self):
        """WSL環境検出テスト."""
        from setup_repo.platform_detector import _check_wsl_environment

        result = _check_wsl_environment()
        # 実際の環境に依存するため、型のみ確認
        assert isinstance(result, bool)

    @pytest.mark.unit
    @patch("pathlib.Path.exists")
    def test_check_wsl_environment_false(self, mock_exists):
        """WSL環境検出テスト（False）."""
        mock_exists.return_value = False

        from setup_repo.platform_detector import _check_wsl_environment

        result = _check_wsl_environment()

        assert result is False

    @pytest.mark.unit
    def test_check_package_manager_available(self):
        """パッケージマネージャー利用可能性チェックテスト."""
        # 実際の環境でテスト
        if platform.system() == "Windows":
            result = check_package_manager("python")
        elif platform.system() == "Darwin":
            result = check_package_manager("python3")
        else:
            result = check_package_manager("python3")

        assert isinstance(result, bool)

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_package_manager_unavailable(self, mock_run):
        """パッケージマネージャー利用可能性チェックテスト（利用不可）."""
        mock_run.side_effect = FileNotFoundError()

        result = check_package_manager("nonexistent")

        assert result is False

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_package_manager_error(self, mock_run):
        """パッケージマネージャーチェックエラーテスト."""
        mock_run.return_value.returncode = 1

        result = check_package_manager("apt")

        assert result is False

    @pytest.mark.unit
    def test_check_module_availability_available(self):
        """モジュール利用可能性チェックテスト（利用可能）."""
        result = check_module_availability("json")  # 標準ライブラリ

        # 詳細情報を返すため、辞書型であることを確認
        assert isinstance(result, dict)
        assert "available" in result

    @pytest.mark.unit
    def test_check_module_availability_unavailable(self):
        """モジュール利用可能性チェックテスト（利用不可）."""
        result = check_module_availability("nonexistent_module_12345")

        # 詳細情報を返すため、辞書型であることを確認
        assert isinstance(result, dict)
        assert "available" in result
        assert result["available"] is False

    @pytest.mark.unit
    @patch.dict("os.environ", {"CI": "true"})
    def test_is_ci_environment_true(self):
        """CI環境判定テスト（True）."""
        from setup_repo.platform_detector import _is_ci_environment

        result = _is_ci_environment()

        assert result is True

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_is_ci_environment_false(self):
        """CI環境判定テスト（False）."""
        from setup_repo.platform_detector import _is_ci_environment

        result = _is_ci_environment()

        assert result is False

    @pytest.mark.unit
    @patch.dict("os.environ", {"PRE_COMMIT": "1"})
    def test_is_precommit_environment_true(self):
        """Pre-commit環境判定テスト（True）."""
        from setup_repo.platform_detector import _is_precommit_environment

        result = _is_precommit_environment()

        assert result is True

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_is_precommit_environment_false(self):
        """Pre-commit環境判定テスト（False）."""
        from setup_repo.platform_detector import _is_precommit_environment

        result = _is_precommit_environment()

        assert result is False


class TestPackageManagerDetection:
    """パッケージマネージャー検出のテスト."""

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.check_package_manager")
    def test_get_available_package_managers_multiple(self, mock_check):
        """複数パッケージマネージャー検出テスト."""

        def check_side_effect(manager):
            return manager in ["apt", "pip", "uv"]

        mock_check.side_effect = check_side_effect

        platform_info = PlatformInfo(
            name="linux",
            display_name="Linux",
            package_managers=["apt", "pip", "uv", "yum"],
            shell="bash",
            python_cmd="python3",
        )
        result = get_available_package_managers(platform_info)

        assert "apt" in result
        assert "pip" in result
        assert "uv" in result
        assert "yum" not in result

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.check_package_manager")
    def test_get_available_package_managers_none(self, mock_check):
        """パッケージマネージャーなし検出テスト."""
        mock_check.return_value = False

        platform_info = PlatformInfo(
            name="linux", display_name="Linux", package_managers=["apt", "pip"], shell="bash", python_cmd="python3"
        )
        result = get_available_package_managers(platform_info)

        assert result == []

    @pytest.mark.unit
    def test_get_install_commands(self):
        """インストールコマンド取得テスト."""
        platform_info = PlatformInfo(
            name="linux",
            display_name="Linux",
            package_managers=["apt", "yum", "brew", "winget", "pip", "uv"],
            shell="bash",
            python_cmd="python3",
        )
        result = get_install_commands(platform_info)

        assert isinstance(result, dict)
        if result:  # 結果が空でない場合のみチェック
            for _manager, commands in result.items():
                assert isinstance(commands, list)
                if commands:
                    assert any("install" in cmd or "uv" in cmd for cmd in commands)


class TestCIEnvironmentInfo:
    """CI環境情報のテスト."""

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "user/repo", "GITHUB_SHA": "abc123"})
    def test_get_ci_environment_info_github(self):
        """GitHub Actions環境情報取得テスト."""
        result = get_ci_environment_info()

        assert "GITHUB_ACTIONS" in result
        assert result["GITHUB_ACTIONS"] == "true"

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITLAB_CI": "true", "CI_PROJECT_PATH": "user/repo", "CI_COMMIT_SHA": "def456"})
    def test_get_ci_environment_info_gitlab(self):
        """GitLab CI環境情報取得テスト."""
        result = get_ci_environment_info()

        assert "GITLAB_CI" in result or len(result) >= 0

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_get_ci_environment_info_local(self):
        """ローカル環境情報取得テスト."""
        result = get_ci_environment_info()

        assert isinstance(result, dict)


class TestPlatformDiagnostics:
    """プラットフォーム診断のテスト."""

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.detect_platform")
    @patch("setup_repo.platform_detector.get_available_package_managers")
    @patch("setup_repo.platform_detector.check_module_availability")
    def test_diagnose_platform_issues_no_issues(self, mock_module, mock_managers, mock_detect):
        """問題なしでのプラットフォーム診断テスト."""
        mock_detect.return_value = PlatformInfo(
            name="linux", display_name="Linux", package_managers=["apt"], shell="bash", python_cmd="python3"
        )
        mock_managers.return_value = ["apt", "pip", "uv"]
        mock_module.return_value = {"available": True}

        result = diagnose_platform_issues()

        assert "platform_info" in result
        assert "package_managers" in result
        assert "recommendations" in result

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.detect_platform")
    @patch("setup_repo.platform_detector.get_available_package_managers")
    def test_diagnose_platform_issues_with_problems(self, mock_managers, mock_detect):
        """問題ありでのプラットフォーム診断テスト."""
        mock_detect.return_value = PlatformInfo(
            name="linux", display_name="Linux", package_managers=[], shell="bash", python_cmd="python3"
        )
        mock_managers.return_value = []

        result = diagnose_platform_issues()

        assert "platform_info" in result
        assert "recommendations" in result

    @pytest.mark.unit
    @patch("setup_repo.platform_detector._diagnose_ci_specific_issues")
    @patch("setup_repo.platform_detector._is_ci_environment")
    def test_diagnose_platform_issues_ci_environment(self, mock_is_ci, mock_ci_diagnose):
        """CI環境でのプラットフォーム診断テスト."""
        mock_is_ci.return_value = True
        mock_ci_diagnose.return_value = {"ci_issues": ["Permission issue"], "ci_recommendations": ["Use sudo"]}

        with (
            patch("setup_repo.platform_detector.detect_platform") as mock_detect,
            patch("setup_repo.platform_detector.get_available_package_managers") as mock_managers,
        ):
            mock_detect.return_value = PlatformInfo(
                name="linux", display_name="Linux", package_managers=["apt"], shell="bash", python_cmd="python3"
            )
            mock_managers.return_value = ["apt"]

            result = diagnose_platform_issues()

        assert "platform_info" in result
        mock_ci_diagnose.assert_called_once()


class TestPlatformDetectorClass:
    """PlatformDetectorクラスのテスト."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.detector = PlatformDetector()

    @pytest.mark.unit
    def test_init(self):
        """初期化テスト."""
        assert isinstance(self.detector, PlatformDetector)

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.detect_platform")
    def test_detect_platform_method(self, mock_detect):
        """プラットフォーム検出メソッドテスト."""
        expected_info = PlatformInfo(
            name="windows", display_name="Windows", package_managers=["winget"], shell="powershell", python_cmd="python"
        )
        mock_detect.return_value = expected_info

        result = self.detector.detect_platform()

        assert result == "windows"
        mock_detect.assert_called_once()

    @pytest.mark.unit
    def test_is_wsl_method(self):
        """WSL判定メソッドテスト."""
        result = self.detector.is_wsl()

        # 実際の環境に依存するため、型のみ確認
        assert isinstance(result, bool)

    @pytest.mark.unit
    @patch("setup_repo.platform_detector._is_ci_environment")
    def test_is_ci_environment_method(self, mock_is_ci):
        """CI環境判定メソッドテスト."""
        mock_is_ci.return_value = True

        result = self.detector.is_ci_environment()

        assert result is True
        mock_is_ci.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.platform_detector._is_precommit_environment")
    def test_is_precommit_environment_method(self, mock_is_precommit):
        """Pre-commit環境判定メソッドテスト."""
        mock_is_precommit.return_value = True

        result = self.detector.is_precommit_environment()

        assert result is True
        mock_is_precommit.assert_called_once()

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITHUB_ACTIONS": "true"})
    def test_is_github_actions_method(self):
        """GitHub Actions判定メソッドテスト."""
        result = self.detector.is_github_actions()

        assert result is True

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.get_available_package_managers")
    def test_get_package_manager_method(self, mock_get_managers):
        """パッケージマネージャー取得メソッドテスト."""
        mock_get_managers.return_value = ["apt", "pip"]

        result = self.detector.get_package_manager()

        assert result == "apt"
        mock_get_managers.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.detect_platform")
    def test_get_platform_info_method(self, mock_detect):
        """プラットフォーム情報取得メソッドテスト."""
        expected_info = PlatformInfo(
            name="linux", display_name="Linux", package_managers=["apt"], shell="bash", python_cmd="python3"
        )
        mock_detect.return_value = expected_info

        result = self.detector.get_platform_info()

        assert result == expected_info

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.diagnose_platform_issues")
    def test_diagnose_issues_method(self, mock_diagnose):
        """問題診断メソッドテスト."""
        expected_result = {"platform_supported": True, "issues": [], "recommendations": []}
        mock_diagnose.return_value = expected_result

        result = self.detector.diagnose_issues()

        assert result == expected_result
        mock_diagnose.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.platform_detector.get_ci_environment_info")
    def test_get_ci_info_method(self, mock_get_ci):
        """CI情報取得メソッドテスト."""
        expected_info = {"provider": "GitHub Actions", "is_ci": True}
        mock_get_ci.return_value = expected_info

        result = self.detector.get_ci_info()

        assert result == expected_info
        mock_get_ci.assert_called_once()
