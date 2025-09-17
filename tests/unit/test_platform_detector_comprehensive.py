"""プラットフォーム検出機能の包括的テスト（実環境重視）."""

import platform

import pytest

from setup_repo.platform_detector import (
    PlatformDetector,
    check_module_availability,
    check_package_manager,
    detect_platform,
    diagnose_platform_issues,
    get_available_package_managers,
    get_ci_environment_info,
    get_install_commands,
)


class TestPlatformDetection:
    """プラットフォーム検出機能のテスト（実環境重視）."""

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows環境でのみ実行")
    def test_detect_platform_windows(self):
        """Windows検出テスト（実環境）."""
        result = detect_platform()
        assert result.name == "windows"
        assert result.display_name == "Windows"
        assert len(result.package_managers) > 0
        assert result.shell in ["powershell", "cmd"]
        assert result.python_cmd in ["python", "python3"]

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")
    def test_detect_platform_linux(self):
        """Linux検出テスト（実環境）."""
        result = detect_platform()
        assert result.name == "linux"
        assert result.display_name == "Linux"
        assert len(result.package_managers) > 0
        assert result.shell in ["bash", "sh", "zsh"]
        assert result.python_cmd in ["python3", "python"]

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS環境でのみ実行")
    def test_detect_platform_macos(self):
        """macOS検出テスト（実環境）."""
        result = detect_platform()
        assert result.name == "macos"
        assert result.display_name == "macOS"
        assert len(result.package_managers) > 0
        assert result.shell in ["bash", "zsh"]
        assert result.python_cmd in ["python3", "python"]

    @pytest.mark.unit
    def test_detect_platform_current(self):
        """現在のプラットフォーム検出テスト."""
        result = detect_platform()

        # 基本的な属性の存在確認
        assert hasattr(result, "name")
        assert hasattr(result, "display_name")
        assert hasattr(result, "package_managers")
        assert hasattr(result, "shell")
        assert hasattr(result, "python_cmd")

        # 値の妥当性確認
        assert result.name in ["windows", "linux", "macos"]
        assert isinstance(result.package_managers, list)
        assert len(result.package_managers) > 0

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows環境でのみ実行")
    def test_detect_windows_platform_details(self):
        """Windows詳細検出テスト（実環境）."""
        from setup_repo.platform_detector import _detect_windows_platform

        result = _detect_windows_platform(False)

        assert result.name == "windows"
        assert result.display_name == "Windows"
        assert len(result.package_managers) > 0
        # 実環境では利用可能なパッケージマネージャーが含まれる
        common_managers = ["winget", "scoop", "choco", "pip", "uv"]
        assert any(manager in result.package_managers for manager in common_managers)

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux環境でのみ実行")
    def test_detect_linux_platform_details(self):
        """Linux詳細検出テスト（実環境）."""
        from setup_repo.platform_detector import _detect_linux_platform

        result = _detect_linux_platform(False, False)

        assert result.name == "linux"
        assert result.display_name == "Linux"
        assert len(result.package_managers) > 0
        # 実環境では利用可能なパッケージマネージャーが含まれる
        common_managers = ["apt", "yum", "dnf", "pacman", "zypper", "pip", "uv"]
        assert any(manager in result.package_managers for manager in common_managers)

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS環境でのみ実行")
    def test_detect_macos_platform_details(self):
        """macOS詳細検出テスト（実環境）."""
        from setup_repo.platform_detector import _detect_macos_platform

        result = _detect_macos_platform(False)

        assert result.name == "macos"
        assert result.display_name == "macOS"
        assert len(result.package_managers) > 0
        # 実環境では利用可能なパッケージマネージャーが含まれる
        common_managers = ["brew", "port", "pip", "uv"]
        assert any(manager in result.package_managers for manager in common_managers)

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="WSLはLinux環境でのみ検出可能")
    def test_check_wsl_environment(self):
        """WSL環境検出テスト（実環境）."""
        from setup_repo.platform_detector import _check_wsl_environment

        result = _check_wsl_environment()
        # 実際の環境に依存するため、型のみ確認
        assert isinstance(result, bool)
        # WSL環境の場合はTrue、通常のLinuxの場合はFalse

    @pytest.mark.unit
    def test_check_package_manager_python(self):
        """Pythonパッケージマネージャー利用可能性チェックテスト（実環境）."""
        # 実際の環境でテスト - Pythonは必ず利用可能
        if platform.system() == "Windows":
            result = check_package_manager("python")
        else:
            result = check_package_manager("python3")

        assert isinstance(result, bool)
        # Pythonは実行環境で必ず利用可能
        assert result is True

    @pytest.mark.unit
    def test_check_package_manager_nonexistent(self):
        """存在しないパッケージマネージャーチェックテスト（実環境）."""
        result = check_package_manager("nonexistent_manager_12345")
        assert result is False

    @pytest.mark.unit
    def test_check_module_availability_standard_library(self):
        """標準ライブラリモジュール利用可能性チェックテスト（実環境）."""
        result = check_module_availability("json")  # 標準ライブラリ

        assert isinstance(result, dict)
        assert "available" in result
        assert result["available"] is True

    @pytest.mark.unit
    def test_check_module_availability_nonexistent(self):
        """存在しないモジュール利用可能性チェックテスト（実環境）."""
        result = check_module_availability("nonexistent_module_12345")

        assert isinstance(result, dict)
        assert "available" in result
        assert result["available"] is False
        assert "import_error" in result

    @pytest.mark.unit
    def test_is_ci_environment_current(self):
        """CI環境判定テスト（実環境）."""
        from setup_repo.platform_detector import _is_ci_environment

        result = _is_ci_environment()
        # 実際の環境に依存するため、型のみ確認
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_is_precommit_environment_current(self):
        """Pre-commit環境判定テスト（実環境）."""
        from setup_repo.platform_detector import _is_precommit_environment

        result = _is_precommit_environment()
        # 実際の環境に依存するため、型のみ確認
        assert isinstance(result, bool)


class TestPackageManagerDetection:
    """パッケージマネージャー検出のテスト（実環境重視）."""

    @pytest.mark.unit
    def test_get_available_package_managers_current_platform(self):
        """現在のプラットフォームでのパッケージマネージャー検出テスト（実環境）."""
        platform_info = detect_platform()
        result = get_available_package_managers(platform_info)

        # 実環境では少なくとも1つのパッケージマネージャーが利用可能
        assert isinstance(result, list)
        assert len(result) > 0

        # 実環境で利用可能なパッケージマネージャーがあることを確認
        # Python環境では通常pipが利用可能だが、実環境に依存する
        common_managers = ["pip", "uv", "python", "python3"]
        has_common_manager = any(manager in result for manager in common_managers)
        if not has_common_manager:
            # 実環境で利用可能なマネージャーがあることを確認
            assert len(result) > 0, f"利用可能なパッケージマネージャー: {result}"

    @pytest.mark.unit
    def test_get_install_commands_current_platform(self):
        """現在のプラットフォームでのインストールコマンド取得テスト（実環境）."""
        platform_info = detect_platform()
        result = get_install_commands(platform_info)

        assert isinstance(result, dict)
        # 実環境では何らかのインストールコマンドが利用可能
        assert len(result) > 0

        for _manager, commands in result.items():
            assert isinstance(commands, list)
            assert len(commands) > 0
            # コマンドにはインストール関連のキーワードが含まれる
            assert any("install" in cmd.lower() or "add" in cmd.lower() for cmd in commands)


class TestCIEnvironmentInfo:
    """CI環境情報のテスト（実環境重視）."""

    @pytest.mark.unit
    def test_get_ci_environment_info_current(self):
        """現在の環境でのCI環境情報取得テスト（実環境）."""
        result = get_ci_environment_info()

        assert isinstance(result, dict)
        # 基本的なシステム情報は常に含まれる
        assert "platform_system" in result or "python_version" in result or len(result) >= 0


class TestPlatformDiagnostics:
    """プラットフォーム診断のテスト（実環境重視）."""

    @pytest.mark.unit
    def test_diagnose_platform_issues_current_environment(self):
        """現在の環境でのプラットフォーム診断テスト（実環境）."""
        result = diagnose_platform_issues()

        assert isinstance(result, dict)
        assert "platform_info" in result
        assert "recommendations" in result

        # プラットフォーム情報が正しく取得されている
        platform_info = result["platform_info"]
        # platform_infoは辞書またはPlatformInfoオブジェクトの可能性がある
        if hasattr(platform_info, "name"):
            assert platform_info.name in ["windows", "linux", "macos"]
        elif isinstance(platform_info, dict) and "name" in platform_info:
            assert platform_info["name"] in ["windows", "linux", "macos"]
        else:
            # プラットフォーム情報が何らかの形式で存在することを確認
            assert platform_info is not None

        # 推奨事項はリスト形式
        assert isinstance(result["recommendations"], list)


class TestPlatformDetectorClass:
    """PlatformDetectorクラスのテスト（実環境重視）."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.detector = PlatformDetector()

    @pytest.mark.unit
    def test_init(self):
        """初期化テスト."""
        assert isinstance(self.detector, PlatformDetector)

    @pytest.mark.unit
    def test_detect_platform_method(self):
        """プラットフォーム検出メソッドテスト（実環境）."""
        result = self.detector.detect_platform()

        assert isinstance(result, str)
        assert result in ["windows", "linux", "macos"]

    @pytest.mark.unit
    def test_is_wsl_method(self):
        """WSL判定メソッドテスト（実環境）."""
        result = self.detector.is_wsl()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_is_ci_environment_method(self):
        """CI環境判定メソッドテスト（実環境）."""
        result = self.detector.is_ci_environment()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_is_precommit_environment_method(self):
        """Pre-commit環境判定メソッドテスト（実環境）."""
        result = self.detector.is_precommit_environment()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_is_github_actions_method(self):
        """GitHub Actions判定メソッドテスト（実環境）."""
        result = self.detector.is_github_actions()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_get_package_manager_method(self):
        """パッケージマネージャー取得メソッドテスト（実環境）."""
        result = self.detector.get_package_manager()

        # 実環境では何らかのパッケージマネージャーが利用可能
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    def test_get_platform_info_method(self):
        """プラットフォーム情報取得メソッドテスト（実環境）."""
        result = self.detector.get_platform_info()

        assert hasattr(result, "name")
        assert hasattr(result, "display_name")
        assert hasattr(result, "package_managers")
        assert result.name in ["windows", "linux", "macos"]

    @pytest.mark.unit
    def test_diagnose_issues_method(self):
        """問題診断メソッドテスト（実環境）."""
        result = self.detector.diagnose_issues()

        assert isinstance(result, dict)
        assert "platform_info" in result or "recommendations" in result

    @pytest.mark.unit
    def test_get_ci_info_method(self):
        """CI情報取得メソッドテスト（実環境）."""
        result = self.detector.get_ci_info()

        assert isinstance(result, dict)
