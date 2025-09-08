"""プラットフォーム検出とツール管理"""
import os
import platform
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    """プラットフォーム情報"""
    name: str
    display_name: str
    package_managers: List[str]
    shell: str
    python_cmd: str


def detect_platform() -> PlatformInfo:
    """現在のプラットフォームを詳細検出"""
    system = platform.system().lower()
    
    if system == "windows" or os.name == "nt":
        return PlatformInfo(
            name="windows",
            display_name="Windows",
            package_managers=["scoop", "winget", "chocolatey"],
            shell="powershell",
            python_cmd="python"
        )
    elif "microsoft" in platform.release().lower():
        return PlatformInfo(
            name="wsl",
            display_name="WSL (Windows Subsystem for Linux)",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3"
        )
    elif system == "darwin":
        return PlatformInfo(
            name="macos",
            display_name="macOS",
            package_managers=["brew", "curl"],
            shell="zsh",
            python_cmd="python3"
        )
    else:
        return PlatformInfo(
            name="linux",
            display_name="Linux",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3"
        )


def check_package_manager(manager: str) -> bool:
    """パッケージマネージャーの利用可能性をチェック"""
    try:
        subprocess.run([manager, "--version"], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_available_package_managers(platform_info: PlatformInfo) -> List[str]:
    """利用可能なパッケージマネージャーを取得"""
    available = []
    for manager in platform_info.package_managers:
        if check_package_manager(manager):
            available.append(manager)
    return available


def get_install_commands(platform_info: PlatformInfo) -> Dict[str, List[str]]:
    """プラットフォーム別のインストールコマンドを取得"""
    commands = {
        "windows": {
            "scoop": ["scoop install uv", "scoop install gh"],
            "winget": ["winget install --id=astral-sh.uv", "winget install --id=GitHub.cli"],
            "chocolatey": ["choco install uv", "choco install gh"],
            "pip": ["pip install uv"]
        },
        "wsl": {
            "snap": ["sudo snap install --classic uv", "sudo snap install gh"],
            "apt": ["sudo apt update && sudo apt install -y gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"]
        },
        "linux": {
            "snap": ["sudo snap install --classic uv", "sudo snap install gh"],
            "apt": ["sudo apt update && sudo apt install -y gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"]
        },
        "macos": {
            "brew": ["brew install uv", "brew install gh"],
            "curl": ["curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "pip": ["pip install uv"]
        }
    }
    
    return commands.get(platform_info.name, {})