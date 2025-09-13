"""互換性チェック機能のテスト."""

import platform
import sys

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestCompatibility:
    """互換性チェック機能のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()

    @pytest.mark.unit
    def test_python_version_compatibility(self):
        """Pythonバージョン互換性チェックのテスト."""

        # Python版本兼容性检查函数
        def check_python_compatibility(required_version, current_version=None):
            if current_version is None:
                current_version = sys.version_info

            required_parts = [int(x) for x in required_version.split(".")]
            current_parts = current_version[: len(required_parts)]

            # バージョン比較
            for req, cur in zip(required_parts, current_parts):
                if cur > req:
                    return True, f"Python {'.'.join(map(str, current_parts))} is compatible"
                elif cur < req:
                    return False, f"Python {'.'.join(map(str, current_parts))} is too old, requires {required_version}+"

            return True, f"Python {'.'.join(map(str, current_parts))} meets minimum requirement"

        # テストケース
        test_cases = [
            ("3.9", (3, 10, 0), True),  # 新しいバージョン
            ("3.9", (3, 9, 0), True),  # 最小バージョン
            ("3.9", (3, 8, 5), False),  # 古いバージョン
            ("3.11", (3, 12, 1), True),  # 十分新しい
        ]

        # Python互換性チェックテスト
        for required, current, expected_compatible in test_cases:
            is_compatible, message = check_python_compatibility(required, current)
            assert is_compatible == expected_compatible

    @pytest.mark.unit
    def test_platform_compatibility(self):
        """プラットフォーム互換性チェックのテスト."""

        # プラットフォーム互換性チェック関数
        def check_platform_compatibility(supported_platforms, current_platform=None):
            if current_platform is None:
                current_platform = platform.system()

            # プラットフォーム名の正規化
            platform_mapping = {
                "Windows": ["Windows", "win32", "cygwin"],
                "Linux": ["Linux", "linux", "linux2"],
                "Darwin": ["Darwin", "macOS", "osx"],
            }

            # 現在のプラットフォームが対応リストに含まれるかチェック
            for supported in supported_platforms:
                if supported in platform_mapping:
                    if current_platform in platform_mapping[supported]:
                        return True, f"Platform {current_platform} is supported"
                elif supported.lower() == current_platform.lower():
                    return True, f"Platform {current_platform} is supported"

            return False, f"Platform {current_platform} is not supported. Supported: {supported_platforms}"

        # テストケース
        test_cases = [
            (["Windows", "Linux", "Darwin"], "Windows", True),
            (["Linux", "Darwin"], "Windows", False),
            (["Windows"], "Linux", False),
            (["Windows", "Linux", "Darwin"], "Darwin", True),
        ]

        # プラットフォーム互換性チェックテスト
        for supported, current, expected_compatible in test_cases:
            is_compatible, message = check_platform_compatibility(supported, current)
            assert is_compatible == expected_compatible

    @pytest.mark.unit
    def test_dependency_compatibility(self):
        """依存関係互換性チェックのテスト."""

        # 依存関係互換性チェック関数
        def check_dependency_compatibility(requirements, installed_packages):
            incompatible = []
            missing = []

            for requirement in requirements:
                package_name = requirement["name"]
                required_version = requirement["version"]

                if package_name not in installed_packages:
                    missing.append(package_name)
                    continue

                installed_version = installed_packages[package_name]

                # バージョン比較（簡単な実装）
                if not version_satisfies(installed_version, required_version):
                    incompatible.append(
                        {"package": package_name, "required": required_version, "installed": installed_version}
                    )

            return {
                "compatible": len(incompatible) == 0 and len(missing) == 0,
                "missing": missing,
                "incompatible": incompatible,
            }

        def version_satisfies(installed, required):
            # 簡単なバージョン比較（実際はより複雑）
            if required.startswith(">="):
                return installed >= required[2:]
            elif required.startswith("=="):
                return installed == required[2:]
            elif required.startswith(">"):
                return installed > required[1:]
            return True

        # テストデータ
        requirements = [
            {"name": "requests", "version": ">=2.25.0"},
            {"name": "numpy", "version": ">=1.20.0"},
            {"name": "flask", "version": "==2.0.1"},
        ]

        installed_packages = {
            "requests": "2.26.0",
            "numpy": "1.19.5",  # 古いバージョン
            "flask": "2.0.1",
            # 'pandas' is missing
        }

        # 依存関係互換性チェックテスト
        result = check_dependency_compatibility(requirements, installed_packages)
        assert result["compatible"] is False
        assert "numpy" in [pkg["package"] for pkg in result["incompatible"]]

    @pytest.mark.unit
    def test_architecture_compatibility(self):
        """アーキテクチャ互換性チェックのテスト."""

        # アーキテクチャ互換性チェック関数
        def check_architecture_compatibility(supported_archs, current_arch=None):
            if current_arch is None:
                current_arch = platform.machine()

            # アーキテクチャ名の正規化
            arch_mapping = {
                "x86_64": ["x86_64", "AMD64", "x64"],
                "i386": ["i386", "i686", "x86"],
                "arm64": ["arm64", "aarch64", "ARM64"],
                "armv7l": ["armv7l", "armv7", "arm"],
            }

            # 現在のアーキテクチャが対応リストに含まれるかチェック
            for supported in supported_archs:
                if supported in arch_mapping:
                    if current_arch in arch_mapping[supported]:
                        return True, f"Architecture {current_arch} is supported"
                elif supported.lower() == current_arch.lower():
                    return True, f"Architecture {current_arch} is supported"

            return False, f"Architecture {current_arch} is not supported. Supported: {supported_archs}"

        # テストケース
        test_cases = [
            (["x86_64", "arm64"], "x86_64", True),
            (["x86_64"], "aarch64", False),
            (["x86_64", "arm64"], "AMD64", True),  # 正規化テスト
        ]

        # アーキテクチャ互換性チェックテスト
        for supported, current, expected_compatible in test_cases:
            is_compatible, message = check_architecture_compatibility(supported, current)
            assert is_compatible == expected_compatible

    @pytest.mark.unit
    def test_feature_compatibility(self):
        """機能互換性チェックのテスト."""

        # 機能互換性チェック関数
        def check_feature_compatibility(required_features, available_features):
            missing_features = []
            incompatible_features = []

            for feature in required_features:
                feature_name = feature["name"]
                required_version = feature.get("version")

                if feature_name not in available_features:
                    missing_features.append(feature_name)
                    continue

                available_feature = available_features[feature_name]
                if required_version and available_feature.get("version"):
                    if not version_compatible(available_feature["version"], required_version):
                        incompatible_features.append(
                            {
                                "feature": feature_name,
                                "required": required_version,
                                "available": available_feature["version"],
                            }
                        )

            return {
                "compatible": len(missing_features) == 0 and len(incompatible_features) == 0,
                "missing": missing_features,
                "incompatible": incompatible_features,
            }

        def version_compatible(available, required):
            # 簡単なバージョン互換性チェック
            return available >= required

        # テストデータ
        required_features = [
            {"name": "ssl", "version": "1.1.1"},
            {"name": "sqlite", "version": "3.35.0"},
            {"name": "zlib"},  # バージョン指定なし
        ]

        available_features = {
            "ssl": {"version": "1.1.1"},
            "sqlite": {"version": "3.34.0"},  # 古いバージョン
            "zlib": {"version": "1.2.11"},
        }

        # 機能互換性チェックテスト
        result = check_feature_compatibility(required_features, available_features)
        assert result["compatible"] is False
        assert "sqlite" in [feat["feature"] for feat in result["incompatible"]]

    @pytest.mark.unit
    def test_environment_compatibility(self):
        """環境互換性チェックのテスト."""

        # 環境互換性チェック関数
        def check_environment_compatibility(requirements, current_env):
            issues = []

            # 環境変数チェック
            if "env_vars" in requirements:
                for var in requirements["env_vars"]:
                    if var not in current_env.get("env_vars", {}):
                        issues.append(f"Missing environment variable: {var}")

            # パス存在チェック
            if "required_paths" in requirements:
                for path in requirements["required_paths"]:
                    if path not in current_env.get("available_paths", []):
                        issues.append(f"Required path not found: {path}")

            # 権限チェック
            if "permissions" in requirements:
                for perm in requirements["permissions"]:
                    if perm not in current_env.get("permissions", []):
                        issues.append(f"Missing permission: {perm}")

            return {"compatible": len(issues) == 0, "issues": issues}

        # テストデータ
        requirements = {
            "env_vars": ["PATH", "HOME"],
            "required_paths": ["/usr/bin", "/tmp"],
            "permissions": ["read", "write"],
        }

        current_env = {
            "env_vars": {"PATH": "/usr/bin:/bin", "USER": "test"},  # HOME missing
            "available_paths": ["/usr/bin", "/home"],  # /tmp missing
            "permissions": ["read", "write", "execute"],
        }

        # 環境互換性チェックテスト
        result = check_environment_compatibility(requirements, current_env)
        assert result["compatible"] is False
        assert len(result["issues"]) == 2  # HOME and /tmp missing

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有の互換性チェック")
    def test_unix_compatibility(self):
        """Unix固有の互換性チェックテスト."""

        # Unix固有の互換性チェック
        def check_unix_compatibility():
            compatibility_info = {
                "shell_available": True,  # /bin/sh exists
                "posix_compliant": True,
                "signal_support": True,
                "fork_support": True,
                "file_permissions": True,
            }

            issues = []
            if not compatibility_info["posix_compliant"]:
                issues.append("System is not POSIX compliant")
            if not compatibility_info["signal_support"]:
                issues.append("Signal handling not supported")

            return {"compatible": len(issues) == 0, "issues": issues, "features": compatibility_info}

        # Unix互換性チェックテスト
        result = check_unix_compatibility()
        assert result["compatible"] is True
        assert result["features"]["posix_compliant"] is True

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有の互換性チェック")
    def test_windows_compatibility(self):
        """Windows固有の互換性チェックテスト."""

        # Windows固有の互換性チェック
        def check_windows_compatibility():
            compatibility_info = {
                "powershell_available": True,
                "cmd_available": True,
                "wmi_support": True,
                "registry_access": True,
                "service_control": True,
            }

            issues = []
            if not compatibility_info["powershell_available"]:
                issues.append("PowerShell not available")
            if not compatibility_info["registry_access"]:
                issues.append("Registry access not available")

            return {"compatible": len(issues) == 0, "issues": issues, "features": compatibility_info}

        # Windows互換性チェックテスト
        result = check_windows_compatibility()
        assert result["compatible"] is True
        assert result["features"]["powershell_available"] is True

    @pytest.mark.unit
    def test_backward_compatibility(self):
        """後方互換性チェックのテスト."""

        # 後方互換性チェック関数
        def check_backward_compatibility(current_version, supported_versions):
            # バージョンを数値に変換
            def version_to_tuple(version):
                return tuple(map(int, version.split(".")))

            current_tuple = version_to_tuple(current_version)

            compatible_versions = []
            for version in supported_versions:
                version_tuple = version_to_tuple(version)
                # メジャーバージョンが同じで、マイナーバージョンが以下
                if version_tuple[0] == current_tuple[0] and version_tuple <= current_tuple:
                    compatible_versions.append(version)

            return {
                "compatible": len(compatible_versions) > 0,
                "compatible_versions": compatible_versions,
                "current_version": current_version,
            }

        # テストケース
        current_version = "2.1.0"
        supported_versions = ["1.0.0", "1.5.0", "2.0.0", "2.1.0", "3.0.0"]

        # 後方互換性チェックテスト
        result = check_backward_compatibility(current_version, supported_versions)
        assert result["compatible"] is True
        assert "2.0.0" in result["compatible_versions"]
        assert "2.1.0" in result["compatible_versions"]
        assert "3.0.0" not in result["compatible_versions"]  # 新しいメジャーバージョン

    @pytest.mark.unit
    def test_compatibility_report_generation(self):
        """互換性レポート生成のテスト."""

        # 互換性レポート生成関数
        def generate_compatibility_report(checks):
            report = {
                "timestamp": "2024-12-01T10:00:00Z",
                "platform": self.platform_info.name,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "overall_compatible": True,
                "checks": {},
                "issues": [],
                "recommendations": [],
            }

            for check_name, check_result in checks.items():
                report["checks"][check_name] = check_result

                if not check_result.get("compatible", True):
                    report["overall_compatible"] = False
                    if "issues" in check_result:
                        report["issues"].extend(check_result["issues"])

                    # 推奨事項の生成
                    if check_name == "python_version":
                        report["recommendations"].append("Upgrade Python to a supported version")
                    elif check_name == "dependencies":
                        report["recommendations"].append("Update incompatible dependencies")
                    elif check_name == "platform":
                        report["recommendations"].append("Use a supported platform")

            return report

        # テストデータ
        checks = {
            "python_version": {"compatible": True},
            "dependencies": {"compatible": False, "issues": ["numpy version too old"]},
            "platform": {"compatible": True},
        }

        # 互換性レポート生成テスト
        report = generate_compatibility_report(checks)
        assert report["overall_compatible"] is False
        assert len(report["issues"]) == 1
        assert len(report["recommendations"]) == 1
        assert "Update incompatible dependencies" in report["recommendations"]
