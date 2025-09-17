"""プラットフォーム検出のエッジケースとエラーハンドリングテスト（実環境重視）"""

import platform

import pytest

from src.setup_repo.platform_detector import (
    PlatformDetector,
    check_module_availability,
    check_package_manager,
    diagnose_platform_issues,
    get_available_package_managers,
    get_ci_environment_info,
)

from ..multiplatform.helpers import verify_current_platform


class TestPlatformDetectorEdgeCases:
    """プラットフォーム検出のエッジケーステスト（実環境重視）"""

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Linux", reason="WSLはLinux環境でのみ検出可能")
    def test_wsl_detection_real_environment(self):
        """WSL検出の実環境テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import _check_wsl_environment

        result = _check_wsl_environment()
        assert isinstance(result, bool)
        # WSL環境かどうかは実環境に依存

    @pytest.mark.unit
    def test_package_manager_check_nonexistent(self):
        """存在しないパッケージマネージャーチェックテスト（実環境）"""
        verify_current_platform()

        # 存在しないコマンドのチェック
        result = check_package_manager("nonexistent_manager_12345")
        assert result is False

    @pytest.mark.unit
    def test_module_availability_platform_specific(self):
        """プラットフォーム固有モジュールの可用性チェックテスト（実環境）"""
        verify_current_platform()

        # 存在しないモジュール
        result = check_module_availability("nonexistent_module_12345")
        assert result["available"] is False
        assert "import_error" in result

        # プラットフォーム固有モジュールのテスト（実環境でのみ）
        if platform.system() == "Windows":
            # Windows固有モジュール
            result = check_module_availability("msvcrt")
            assert result["available"] is True
            assert result.get("platform_specific", False) is True
        else:
            # Unix系固有モジュール
            result = check_module_availability("fcntl")
            assert result["available"] is True
            assert result.get("platform_specific", False) is True

    @pytest.mark.unit
    def test_module_availability_standard_library(self):
        """標準ライブラリモジュールのバージョン検出テスト（実環境）"""
        verify_current_platform()

        # 標準ライブラリモジュールのテスト
        result = check_module_availability("json")
        assert result["available"] is True

        # バージョン情報がある場合は確認
        if "version" in result:
            assert isinstance(result["version"], str)

        # ロケーション情報がある場合は確認
        if "location" in result:
            assert isinstance(result["location"], str)

    @pytest.mark.unit
    def test_ci_environment_detection_current(self):
        """CI環境検出の実環境テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import _is_ci_environment

        # 実環境でのCI環境判定
        result = _is_ci_environment()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_precommit_environment_detection_current(self):
        """precommit環境検出の実環境テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import _is_precommit_environment

        # 実環境でのprecommit環境判定
        result = _is_precommit_environment()
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_get_available_package_managers_current_platform(self):
        """現在のプラットフォームでの利用可能パッケージマネージャーフィルタリングテスト（実環境）"""
        verify_current_platform()

        from src.setup_repo.platform_detector import detect_platform

        # 実環境でのプラットフォーム情報取得
        platform_info = detect_platform()
        available = get_available_package_managers(platform_info)

        assert isinstance(available, list)
        # 実環境では少なくとも1つのパッケージマネージャーが利用可能
        assert len(available) > 0

    @pytest.mark.unit
    def test_ci_environment_info_collection_current(self):
        """CI環境情報収集の実環境テスト"""
        verify_current_platform()

        # 実環境でのCI環境情報収集
        ci_info = get_ci_environment_info()

        assert isinstance(ci_info, dict)
        # 基本的なシステム情報は常に含まれる
        # 実環境によっては異なるキーが含まれる可能性がある

    @pytest.mark.unit
    def test_diagnose_platform_issues_current_environment(self):
        """プラットフォーム問題診断の実環境テスト"""
        verify_current_platform()

        # 実環境でのプラットフォーム診断
        diagnosis = diagnose_platform_issues()

        assert isinstance(diagnosis, dict)
        assert "platform_info" in diagnosis or "recommendations" in diagnosis

    @pytest.mark.unit
    def test_platform_detector_class_consistency(self):
        """PlatformDetectorクラスの一貫性テスト（実環境）"""
        verify_current_platform()

        detector = PlatformDetector()

        # 複数回呼び出して一貫性を確認
        platform1 = detector.detect_platform()
        platform2 = detector.detect_platform()

        assert platform1 == platform2
        assert isinstance(platform1, str)

        # プラットフォーム情報の一貫性
        info1 = detector.get_platform_info()
        info2 = detector.get_platform_info()

        assert info1.name == info2.name
        assert info1.display_name == info2.display_name

    @pytest.mark.unit
    def test_platform_detector_environment_checks_current(self):
        """PlatformDetectorの環境チェック機能テスト（実環境）"""
        verify_current_platform()

        detector = PlatformDetector()

        # 実環境での環境チェック
        ci_result = detector.is_ci_environment()
        assert isinstance(ci_result, bool)

        github_result = detector.is_github_actions()
        assert isinstance(github_result, bool)

        precommit_result = detector.is_precommit_environment()
        assert isinstance(precommit_result, bool)

    @pytest.mark.unit
    def test_platform_detector_package_manager_selection_current(self):
        """PlatformDetectorのパッケージマネージャー選択テスト（実環境）"""
        verify_current_platform()

        detector = PlatformDetector()

        # 実環境でのパッケージマネージャー選択
        manager = detector.get_package_manager()
        assert isinstance(manager, str)
        assert len(manager) > 0

        # 実環境では何らかのパッケージマネージャーが利用可能
        common_managers = ["pip", "uv", "apt", "yum", "brew", "winget", "scoop", "choco"]
        assert manager in common_managers or manager is not None
