"""プラットフォーム検出とツール管理"""

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class PlatformInfo:
    """プラットフォーム情報"""

    name: str
    display_name: str
    package_managers: list[str]
    shell: str
    python_cmd: str


def detect_platform() -> PlatformInfo:
    """現在のプラットフォームを詳細検出"""
    system = platform.system().lower()

    # CI環境での追加チェック
    is_ci = os.environ.get("CI", "").lower() == "true"
    github_actions = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    runner_os = os.environ.get("RUNNER_OS", "").lower()

    # GitHub Actionsでの信頼性向上のため、RUNNER_OSも考慮
    if system == "windows" or os.name == "nt" or runner_os == "windows":
        # Windows環境の詳細検出
        shell = "powershell"
        if github_actions:
            # GitHub ActionsのWindows環境では特別な設定
            shell = "powershell"
            # Windows環境でのPATH設定確認
            _log_windows_path_info()

        return PlatformInfo(
            name="windows",
            display_name="Windows" + (" (GitHub Actions)" if github_actions else ""),
            package_managers=["scoop", "winget", "chocolatey"],
            shell=shell,
            python_cmd="python",
        )
    elif system == "linux":
        # Linux環境でWSLをチェック
        is_wsl = False

        # 方法1: platform.release()でMicrosoftをチェック
        if "microsoft" in platform.release().lower():
            is_wsl = True

        # 方法2: /proc/versionファイルでWSLをチェック
        if not is_wsl and os.path.exists("/proc/version"):
            try:
                with open("/proc/version", encoding="utf-8") as f:
                    version_info = f.read().lower()
                    if "microsoft" in version_info or "wsl" in version_info:
                        is_wsl = True
            except (FileNotFoundError, PermissionError, OSError):
                pass

        # 方法3: /proc/sys/kernel/osreleaseでチェック
        if not is_wsl and os.path.exists("/proc/sys/kernel/osrelease"):
            try:
                with open("/proc/sys/kernel/osrelease", encoding="utf-8") as f:
                    osrelease_info = f.read().lower()
                    if "microsoft" in osrelease_info or "wsl" in osrelease_info:
                        is_wsl = True
            except (FileNotFoundError, PermissionError, OSError):
                pass

        # CI環境ではWSLをLinuxとして扱う
        if is_wsl and is_ci:
            return PlatformInfo(
                name="linux",
                display_name="Linux (WSL in CI)" + (" (GitHub Actions)" if github_actions else ""),
                package_managers=["apt", "snap", "curl"],
                shell="bash",
                python_cmd="python3",
            )
        elif is_wsl:
            return PlatformInfo(
                name="wsl",
                display_name="WSL (Windows Subsystem for Linux)",
                package_managers=["apt", "snap", "curl"],
                shell="bash",
                python_cmd="python3",
            )

        # 通常のLinux環境として処理
        if github_actions:
            # GitHub ActionsのLinux環境での特別な設定
            _log_linux_path_info()

        return PlatformInfo(
            name="linux",
            display_name="Linux" + (" (GitHub Actions)" if github_actions else ""),
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )
    elif system == "darwin" or runner_os == "macos":
        if github_actions:
            # GitHub ActionsのmacOS環境での特別な設定
            _log_macos_path_info()

        return PlatformInfo(
            name="macos",
            display_name="macOS" + (" (GitHub Actions)" if github_actions else ""),
            package_managers=["brew", "curl"],
            shell="zsh",
            python_cmd="python3",
        )
    else:
        # Linux環境（デフォルト）
        if github_actions:
            # GitHub ActionsのLinux環境での特別な設定
            _log_linux_path_info()

        return PlatformInfo(
            name="linux",
            display_name="Linux" + (" (GitHub Actions)" if github_actions else ""),
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )


def check_package_manager(manager: str) -> bool:
    """パッケージマネージャーの利用可能性をチェック"""
    try:
        # マネージャー固有のチェックコマンド
        check_commands = {
            "scoop": ["scoop", "--version"],
            "winget": ["winget", "--version"],
            "chocolatey": ["choco", "--version"],
            "brew": ["brew", "--version"],
            "apt": ["apt", "--version"],
            "snap": ["snap", "--version"],
            "curl": ["curl", "--version"],
            "pip": ["pip", "--version"],
            "uv": ["uv", "--version"],
        }

        cmd = check_commands.get(manager, [manager, "--version"])

        # CI環境では短いタイムアウトを使用
        timeout = 5 if _is_ci_environment() else 10

        # タイムアウト付きで実行
        result = subprocess.run(cmd, capture_output=True, check=True, timeout=timeout, text=True)

        # 出力が空でないことを確認
        return bool(result.stdout.strip() or result.stderr.strip())

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as e:
        # CI環境では詳細なエラー情報をログ出力
        if _is_ci_environment():
            _log_package_manager_check_failure(manager, e)
        return False


def check_module_availability(module_name: str) -> dict[str, Any]:
    """モジュールの可用性を詳細にチェック"""
    result: dict[str, Any] = {
        "available": False,
        "import_error": None,
        "version": None,
        "location": None,
        "platform_specific": False,
    }

    try:
        # モジュールのインポートを試行
        module = __import__(module_name)
        result["available"] = True

        # バージョン情報を取得（可能な場合）
        if hasattr(module, "__version__"):
            result["version"] = module.__version__
        elif hasattr(module, "version"):
            result["version"] = module.version

        # モジュールの場所を取得
        if hasattr(module, "__file__"):
            result["location"] = module.__file__

        # プラットフォーム固有モジュールかどうかを判定
        platform_specific_modules = ["fcntl", "msvcrt", "winsound", "termios"]
        result["platform_specific"] = module_name in platform_specific_modules

    except ImportError as e:
        result["import_error"] = str(e)
        result["platform_specific"] = module_name in [
            "fcntl",
            "msvcrt",
            "winsound",
            "termios",
        ]

    return result


def _is_ci_environment() -> bool:
    """CI環境かどうかを判定（内部関数）"""
    return (
        os.environ.get("CI", "").lower() == "true"
        or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        or os.environ.get("CONTINUOUS_INTEGRATION", "").lower() == "true"
    )


def _is_precommit_environment() -> bool:
    """precommit環境かどうかを判定（内部関数）"""
    return os.environ.get("PRE_COMMIT", "") == "1"


def _log_windows_path_info() -> None:
    """Windows環境でのPATH情報をログ出力"""
    if not _is_ci_environment():
        return

    print("::group::Windows PATH診断")
    path_env = os.environ.get("PATH", "")
    path_dirs = path_env.split(os.pathsep)

    print(f"PATH エントリ数: {len(path_dirs)}")

    # uvが含まれているかチェック
    uv_paths = [p for p in path_dirs if "uv" in p.lower()]
    if uv_paths:
        print(f"UV関連PATH: {uv_paths}")
    else:
        print("⚠️ UV関連のPATHが見つかりません")

    # PowerShellの実行ポリシーをチェック
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-ExecutionPolicy"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(f"PowerShell実行ポリシー: {result.stdout.strip()}")
    except Exception as e:
        print(f"PowerShell実行ポリシーチェック失敗: {e}")

    print("::endgroup::")


def _log_macos_path_info() -> None:
    """macOS環境でのPATH情報をログ出力"""
    if not _is_ci_environment():
        return

    print("::group::macOS PATH診断")
    path_env = os.environ.get("PATH", "")
    path_dirs = path_env.split(os.pathsep)

    print(f"PATH エントリ数: {len(path_dirs)}")

    # Homebrewパスをチェック
    brew_paths = [p for p in path_dirs if "brew" in p.lower() or "/opt/homebrew" in p or "/usr/local" in p]
    if brew_paths:
        print(f"Homebrew関連PATH: {brew_paths}")

    # シェル情報をチェック
    shell = os.environ.get("SHELL", "")
    print(f"現在のシェル: {shell}")

    print("::endgroup::")


def _log_linux_path_info() -> None:
    """Linux環境でのPATH情報をログ出力"""
    if not _is_ci_environment():
        return

    print("::group::Linux PATH診断")
    path_env = os.environ.get("PATH", "")
    path_dirs = path_env.split(os.pathsep)

    print(f"PATH エントリ数: {len(path_dirs)}")

    # 一般的なLinuxパスをチェック
    common_paths = ["/usr/bin", "/usr/local/bin", "/bin", "/snap/bin"]
    for common_path in common_paths:
        if common_path in path_dirs:
            print(f"✅ {common_path} が PATH に含まれています")
        else:
            print(f"⚠️ {common_path} が PATH に含まれていません")

    print("::endgroup::")


def _log_package_manager_check_failure(manager: str, error: Exception) -> None:
    """パッケージマネージャーチェック失敗をログ出力"""
    error_type = type(error).__name__
    error_msg = str(error)

    print(f"::debug::パッケージマネージャー '{manager}' チェック失敗: {error_type} - {error_msg}")

    # プラットフォーム固有のアドバイス（簡易版）
    system = platform.system().lower()
    if system == "windows" and manager == "uv":
        print("::warning::Windows環境でuvが見つかりません。PowerShellでPATHを確認してください。")
    elif system == "darwin" and manager == "brew":
        print("::warning::macOS環境でHomebrewが見つかりません。Homebrewをインストールしてください。")
    elif system == "linux" and manager in ["apt", "snap"]:
        print(f"::warning::Linux環境で{manager}が見つかりません。パッケージマネージャーが利用可能か確認してください。")


def get_available_package_managers(platform_info: PlatformInfo) -> list[str]:
    """利用可能なパッケージマネージャーを取得"""
    available = []
    for manager in platform_info.package_managers:
        if check_package_manager(manager):
            available.append(manager)
    return available


def get_install_commands(platform_info: PlatformInfo) -> dict[str, list[str]]:
    """プラットフォーム別のインストールコマンドを取得"""
    commands = {
        "windows": {
            "scoop": ["scoop install uv", "scoop install gh"],
            "winget": [
                "winget install --id=astral-sh.uv",
                "winget install --id=GitHub.cli",
            ],
            "chocolatey": ["choco install uv", "choco install gh"],
            "pip": ["pip install uv"],
        },
        "wsl": {
            "snap": ["sudo snap install --classic uv", "sudo snap install gh"],
            "apt": ["sudo apt update && sudo apt install -y gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"],
        },
        "linux": {
            "snap": ["sudo snap install --classic uv", "sudo snap install gh"],
            "apt": ["sudo apt update && sudo apt install -y gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"],
        },
        "macos": {
            "brew": ["brew install uv", "brew install gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"],
        },
    }

    return commands.get(platform_info.name, {})


def get_ci_environment_info() -> dict[str, str]:
    """CI環境の詳細情報を取得"""
    ci_info = {}

    # GitHub Actions環境変数
    github_vars = [
        "GITHUB_ACTIONS",
        "GITHUB_WORKFLOW",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_JOB",
        "GITHUB_ACTION",
        "RUNNER_OS",
        "RUNNER_ARCH",
        "RUNNER_NAME",
    ]

    for var in github_vars:
        value = os.environ.get(var)
        if value:
            ci_info[var] = value

    # システム情報
    ci_info.update(
        {
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "platform_machine": platform.machine(),
            "platform_processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        }
    )

    return ci_info


def diagnose_platform_issues() -> dict[str, Any]:
    """プラットフォーム関連の問題を診断"""
    diagnosis: dict[str, Any] = {
        "platform_info": None,
        "package_managers": {},
        "module_availability": {},
        "environment_variables": {},
        "path_issues": [],
        "ci_specific_issues": [],
        "recommendations": [],
    }

    try:
        # プラットフォーム情報を取得
        platform_info = detect_platform()
        diagnosis["platform_info"] = {
            "name": platform_info.name,
            "display_name": platform_info.display_name,
            "shell": platform_info.shell,
            "python_cmd": platform_info.python_cmd,
        }

        # パッケージマネージャーの状態をチェック
        for manager in platform_info.package_managers:
            diagnosis["package_managers"][manager] = {
                "available": check_package_manager(manager),
                "in_path": manager in os.environ.get("PATH", ""),
            }

        # プラットフォーム固有モジュールの可用性をチェック
        critical_modules = ["fcntl", "msvcrt", "subprocess", "pathlib", "platform"]
        for module_name in critical_modules:
            diagnosis["module_availability"][module_name] = check_module_availability(module_name)

        # 重要な環境変数をチェック
        important_vars = ["PATH", "PYTHONPATH", "HOME", "USERPROFILE"]
        if _is_ci_environment():
            important_vars.extend(["CI", "GITHUB_ACTIONS", "RUNNER_OS", "RUNNER_ARCH"])

        for var in important_vars:
            value = os.environ.get(var)
            if value:
                diagnosis["environment_variables"][var] = value[:100] + "..." if len(value) > 100 else value

        # PATH関連の問題をチェック
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        # 空のPATHエントリをチェック
        empty_paths = [i for i, path in enumerate(path_dirs) if not path.strip()]
        if empty_paths:
            diagnosis["path_issues"].append(f"空のPATHエントリが{len(empty_paths)}個あります")

        # 存在しないPATHディレクトリをチェック
        missing_paths = [path for path in path_dirs if path.strip() and not os.path.exists(path)]
        if missing_paths:
            diagnosis["path_issues"].append(f"存在しないPATHディレクトリが{len(missing_paths)}個あります")

        # CI環境固有の問題をチェック
        if _is_ci_environment():
            _diagnose_ci_specific_issues(diagnosis, platform_info)

        # 推奨事項を生成
        _generate_platform_recommendations(diagnosis, platform_info)

    except Exception as e:
        diagnosis["error"] = str(e)
        diagnosis["recommendations"].append(f"プラットフォーム診断中にエラーが発生しました: {e}")

    return diagnosis


def _diagnose_ci_specific_issues(diagnosis: dict[str, Any], platform_info: PlatformInfo) -> None:
    """CI環境固有の問題を診断"""
    ci_issues = []

    # GitHub Actions固有のチェック
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        runner_os = os.environ.get("RUNNER_OS", "").lower()
        detected_platform = platform_info.name

        # プラットフォーム検出の一貫性をチェック
        platform_mapping = {
            "windows": "windows",
            "linux": ["linux", "wsl"],  # LinuxはWSLも含む
            "macos": "macos",
        }

        expected_platforms = platform_mapping.get(runner_os)
        if expected_platforms:
            if isinstance(expected_platforms, str):
                expected_platforms = [expected_platforms]

            if detected_platform not in expected_platforms:
                ci_issues.append(
                    f"RUNNER_OS ({runner_os}) と検出されたプラットフォーム ({detected_platform}) が一致しません"
                )

        # Windows固有のCI問題
        if platform_info.name == "windows":
            # PowerShellの実行ポリシーをチェック
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-ExecutionPolicy"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    ci_issues.append("PowerShellの実行ポリシーが制限されている可能性があります")
            except Exception:
                ci_issues.append("PowerShellの実行ポリシーをチェックできませんでした")

        # macOS固有のCI問題
        elif platform_info.name == "macos":
            # Homebrewのパスをチェック
            path_env = os.environ.get("PATH", "")
            if "/opt/homebrew/bin" not in path_env and "/usr/local/bin" not in path_env:
                ci_issues.append("HomebrewのPATHが設定されていない可能性があります")

        # Linux固有のCI問題
        elif platform_info.name == "linux" and not os.path.exists("/var/lib/snapd"):
            ci_issues.append("snapdが利用できない可能性があります")

    # モジュール可用性の問題をチェック
    module_issues = []
    for module_name, module_info in diagnosis["module_availability"].items():
        if not module_info["available"] and not module_info["platform_specific"]:
            module_issues.append(f"必須モジュール '{module_name}' が利用できません")
        elif module_info["platform_specific"] and not module_info["available"]:
            # プラットフォーム固有モジュールの場合は警告レベル
            if (platform_info.name == "windows" and module_name == "fcntl") or (
                platform_info.name != "windows" and module_name == "msvcrt"
            ):
                # 期待される動作なので問題なし
                pass
            else:
                ci_issues.append(f"プラットフォーム固有モジュール '{module_name}' が期待通りに利用できません")

    diagnosis["ci_specific_issues"] = ci_issues


def _generate_platform_recommendations(diagnosis: dict[str, Any], platform_info: PlatformInfo) -> None:
    """プラットフォーム固有の推奨事項を生成"""
    recommendations = []

    # パッケージマネージャーの推奨事項
    available_managers = [m for m, info in diagnosis["package_managers"].items() if info["available"]]
    if not available_managers:
        if platform_info.name == "windows":
            recommendations.append(
                "Windowsでパッケージマネージャーが見つかりません。Scoopまたはwingetのインストールを検討してください。"
            )
        elif platform_info.name == "macos":
            recommendations.append(
                "macOSでパッケージマネージャーが見つかりません。"
                'Homebrewのインストールを検討してください: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            )
        elif platform_info.name == "linux":
            recommendations.append(
                "Linuxでパッケージマネージャーが見つかりません。apt、snap、またはcurlが利用可能か確認してください。"
            )

    # uv固有の推奨事項
    if not check_package_manager("uv"):
        if platform_info.name == "windows":
            recommendations.append(
                "WindowsでuvがPATHに見つかりません。"
                "PowerShellで 'scoop install uv' または"
                "手動インストールを実行してください。"
            )
        else:
            recommendations.append(
                "uvが見つかりません。curl -LsSf https://astral.sh/uv/install.sh | sh でインストールしてください。"
            )

    # CI環境固有の推奨事項
    if _is_ci_environment():
        if diagnosis["ci_specific_issues"]:
            recommendations.append("CI環境で問題が検出されました。GitHub Actionsワークフローの設定を確認してください。")

        # プラットフォーム固有のCI推奨事項
        if platform_info.name == "windows":
            recommendations.append(
                "Windows CI環境では、PowerShellスクリプトの実行ポリシーとPATH設定を確認してください。"
            )

    diagnosis["recommendations"] = recommendations


class PlatformDetector:
    """プラットフォーム検出クラス"""

    def __init__(self):
        self._platform_info = None

    def detect_platform(self) -> str:
        """プラットフォームを検出して名前を返す"""
        if self._platform_info is None:
            self._platform_info = detect_platform()
        return self._platform_info.name

    def is_wsl(self) -> bool:
        """WSL環境かどうかを判定"""
        return self.detect_platform() == "wsl"

    def is_ci_environment(self) -> bool:
        """CI環境かどうかを判定"""
        return _is_ci_environment()

    def is_precommit_environment(self) -> bool:
        """precommit環境かどうかを判定"""
        return _is_precommit_environment()

    def is_github_actions(self) -> bool:
        """GitHub Actions環境かどうかを判定"""
        return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

    def get_package_manager(self) -> str:
        """推奨パッケージマネージャーを取得"""
        if self._platform_info is None:
            self._platform_info = detect_platform()

        available_managers = get_available_package_managers(self._platform_info)
        if available_managers:
            return available_managers[0]  # 最初の利用可能なマネージャーを返す
        else:
            return self._platform_info.package_managers[0]  # デフォルトを返す

    def get_platform_info(self) -> PlatformInfo:
        """詳細なプラットフォーム情報を取得"""
        if self._platform_info is None:
            self._platform_info = detect_platform()
        return self._platform_info

    def diagnose_issues(self) -> dict[str, Any]:
        """プラットフォーム関連の問題を診断"""
        return diagnose_platform_issues()

    def get_ci_info(self) -> dict[str, str]:
        """CI環境の情報を取得"""
        return get_ci_environment_info()
