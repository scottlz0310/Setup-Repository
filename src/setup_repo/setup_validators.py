"""
セットアップ入力検証機能

このモジュールは、インタラクティブセットアップでの
ユーザー入力検証と前提条件チェック機能を提供します。
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from .config import get_github_token, get_github_user
from .platform_detector import PlatformDetector
from .security_helpers import safe_subprocess


class SetupValidator:
    """セットアップ検証クラス"""

    def __init__(self):
        self.platform_detector = PlatformDetector()
        self.platform_info = self.platform_detector.get_platform_info()
        self.errors: list[str] = []

    def get_errors(self) -> list[str]:
        """検証エラーのリストを取得"""
        return self.errors.copy()

    def clear_errors(self) -> None:
        """エラーリストをクリア"""
        self.errors.clear()


def validate_github_credentials() -> dict[str, Any]:
    """GitHub認証情報を検証"""
    username = get_github_user()
    token = get_github_token()

    return {
        "username": username,
        "token": token,
        "username_valid": bool(username),
        "token_valid": bool(token),
    }


def validate_directory_path(path: str) -> dict[str, Any]:
    """ディレクトリパスを検証"""
    if not path:
        return {
            "valid": False,
            "error": "パスが空です",
            "path": None,
        }

    try:
        directory = Path(path).expanduser().resolve()

        # 親ディレクトリが存在するかチェック
        if not directory.parent.exists():
            return {
                "valid": False,
                "error": f"親ディレクトリが存在しません: {directory.parent}",
                "path": directory,
            }

        # ディレクトリが作成可能かチェック
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                created = True
            except OSError as e:
                return {
                    "valid": False,
                    "error": f"ディレクトリを作成できません: {e}",
                    "path": directory,
                }
        else:
            created = False

        # 書き込み権限をチェック
        if not directory.is_dir():
            return {
                "valid": False,
                "error": "指定されたパスはディレクトリではありません",
                "path": directory,
            }

        # 簡単な書き込みテスト
        test_file = directory / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except OSError:
            return {
                "valid": False,
                "error": "ディレクトリに書き込み権限がありません",
                "path": directory,
            }

        return {
            "valid": True,
            "error": None,
            "path": directory,
            "created": created,
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"パス検証エラー: {e}",
            "path": None,
        }


def validate_setup_prerequisites() -> dict[str, Any]:
    """セットアップの前提条件を検証"""
    errors = []
    warnings = []

    # Python バージョンチェック
    python_version = sys.version_info
    if python_version < (3, 9):
        errors.append(f"Python 3.9以上が必要です (現在: {python_version[0]}.{python_version[1]})")

    # Git チェック
    git_available = False
    git_version = None
    try:
        result = safe_subprocess(["git", "--version"], capture_output=True, text=True, check=True)
        git_available = True
        git_version = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Git がインストールされていません")

    # uv チェック（警告のみ）
    uv_available = False
    uv_version = None
    try:
        result = safe_subprocess(["uv", "--version"], capture_output=True, text=True, check=True)
        uv_available = True
        uv_version = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        warnings.append("uv がインストールされていません（後でインストールされます）")

    # GitHub CLI チェック（警告のみ）
    gh_available = False
    gh_version = None
    try:
        result = safe_subprocess(["gh", "--version"], capture_output=True, text=True, check=True)
        gh_available = True
        gh_version = result.stdout.strip().split("\n")[0]  # 最初の行のみ
    except (subprocess.CalledProcessError, FileNotFoundError):
        warnings.append("GitHub CLI がインストールされていません（オプション）")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "python": {
            "version": f"{python_version[0]}.{python_version[1]}.{python_version[2]}",
            "valid": python_version >= (3, 9),
        },
        "git": {
            "available": git_available,
            "version": git_version,
        },
        "uv": {
            "available": uv_available,
            "version": uv_version,
        },
        "gh": {
            "available": gh_available,
            "version": gh_version,
        },
    }


def check_system_requirements() -> dict[str, Any]:
    """システム要件をチェック"""
    platform_detector = PlatformDetector()
    platform_info = platform_detector.get_platform_info()

    # 基本的なシステム情報
    system_info = {
        "platform": platform_info.name,
        "display_name": platform_info.display_name,
        "supported": True,  # 現在すべてのプラットフォームをサポート
    }

    # ディスク容量チェック（簡易）
    try:
        import shutil

        free_space = shutil.disk_usage(Path.home()).free
        # 最低1GB必要
        min_space = 1024 * 1024 * 1024  # 1GB
        system_info["disk_space"] = {
            "free_bytes": free_space,
            "free_gb": free_space / (1024 * 1024 * 1024),
            "sufficient": free_space >= min_space,
        }
    except Exception:
        system_info["disk_space"] = {
            "free_bytes": None,
            "free_gb": None,
            "sufficient": True,  # チェックできない場合は通す
        }

    # メモリ情報（可能な場合）
    try:
        import psutil

        memory = psutil.virtual_memory()
        system_info["memory"] = {
            "total_bytes": memory.total,
            "total_gb": memory.total / (1024 * 1024 * 1024),
            "available_bytes": memory.available,
            "available_gb": memory.available / (1024 * 1024 * 1024),
        }
    except ImportError:
        system_info["memory"] = None

    return system_info


def validate_user_input(
    prompt: str,
    input_type: str = "string",
    required: bool = True,
    default: Optional[str] = None,
) -> dict[str, Any]:
    """ユーザー入力を検証"""
    try:
        user_input = input(prompt).strip()

        # 空入力の処理
        if not user_input:
            if default is not None:
                user_input = default
            elif required:
                return {
                    "valid": False,
                    "value": None,
                    "error": "入力が必要です",
                }
            else:
                return {
                    "valid": True,
                    "value": None,
                    "error": None,
                }

        # 型別検証
        if input_type == "boolean":
            valid_yes = ["y", "yes", "はい", "true", "1"]
            valid_no = ["n", "no", "いいえ", "false", "0"]

            if user_input.lower() in valid_yes:
                return {"valid": True, "value": True, "error": None}
            elif user_input.lower() in valid_no:
                return {"valid": True, "value": False, "error": None}
            else:
                return {
                    "valid": False,
                    "value": None,
                    "error": "y/n で回答してください",
                }

        elif input_type == "path":
            return validate_directory_path(user_input)

        elif input_type == "string":
            return {
                "valid": True,
                "value": user_input,
                "error": None,
            }

        else:
            return {
                "valid": False,
                "value": None,
                "error": f"不明な入力タイプ: {input_type}",
            }

    except KeyboardInterrupt:
        return {
            "valid": False,
            "value": None,
            "error": "入力が中断されました",
        }
    except Exception as e:
        return {
            "valid": False,
            "value": None,
            "error": f"入力検証エラー: {e}",
        }


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """設定ファイルの内容を検証"""
    errors = []
    warnings = []

    # 必須フィールドのチェック
    required_fields = ["github_user", "github_token"]
    for field in required_fields:
        if field not in config or not config[field]:
            errors.append(f"必須フィールドが不足しています: {field}")

    # GitHub設定の検証
    if "github_user" in config:
        username = config["github_user"]
        if not isinstance(username, str) or len(username) < 1:
            errors.append("GitHub ユーザー名が無効です")
        elif not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", username):
            errors.append("GitHub ユーザー名の形式が無効です")

    if "github_token" in config:
        token = config["github_token"]
        if not isinstance(token, str):
            errors.append("GitHub トークンが無効です")
        elif len(token) < 10:  # 最小長チェック
            errors.append("GitHub トークンが短すぎます")

    # オプション設定の検証
    if "default_branch" in config:
        branch = config["default_branch"]
        if not isinstance(branch, str) or not branch:
            warnings.append("デフォルトブランチ名が無効です")

    if "auto_push" in config:
        auto_push = config["auto_push"]
        if not isinstance(auto_push, bool):
            warnings.append("auto_push は boolean 値である必要があります")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": config,
    }


def validate_environment() -> dict[str, Any]:
    """実行環境を検証"""
    errors = []
    warnings = []
    environment_info = {}

    # Python環境の検証
    python_info = {
        "version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
        "executable": sys.executable,
        "valid": sys.version_info >= (3, 9),
    }

    if not python_info["valid"]:
        errors.append(f"Python 3.9以上が必要です (現在: {python_info['version']})")

    environment_info["python"] = python_info

    # 作業ディレクトリの検証
    try:
        current_dir = Path.cwd()
        dir_info = {
            "path": str(current_dir),
            "exists": current_dir.exists(),
            "writable": current_dir.is_dir() and current_dir.stat().st_mode & 0o200,
        }

        if not dir_info["writable"]:
            errors.append("現在のディレクトリに書き込み権限がありません")  # type: ignore[unreachable]

        environment_info["working_directory"] = dir_info
    except Exception as e:
        errors.append(f"作業ディレクトリの検証に失敗: {e}")  # type: ignore[unreachable]

    # 環境変数の検証
    import os

    env_vars: dict[str, dict[str, object]] = {}
    important_vars = ["HOME", "PATH", "GITHUB_TOKEN"]

    for var in important_vars:
        value = os.environ.get(var)
        env_vars[var] = {
            "set": value is not None,
            "value": "***" if var == "GITHUB_TOKEN" and value else value,
        }

    environment_info["environment_variables"] = env_vars  # type: ignore[assignment]

    # ネットワーク接続の簡易チェック
    try:
        import socket

        socket.create_connection(("github.com", 443), timeout=5)
        network_available = True
    except OSError:
        network_available = False
        warnings.append("GitHub への接続ができません")

    environment_info["network"] = {"github_accessible": network_available}

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "environment": environment_info,
    }
