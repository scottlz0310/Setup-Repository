"""
CI環境検出とシステム情報収集機能

このモジュールは、CI/CD環境の検出、システム情報の収集、
依存関係情報の取得機能を提供します。
"""

import json
import os
import subprocess
import sys
from typing import Any


class CIEnvironmentInfo:
    """CI環境情報を収集するクラス"""

    @staticmethod
    def detect_ci_environment() -> str:
        """CI環境を検出"""
        if os.getenv("GITHUB_ACTIONS") == "true":
            return "github_actions"
        elif os.getenv("GITLAB_CI"):
            return "gitlab_ci"
        elif os.getenv("JENKINS_URL"):
            return "jenkins"
        elif os.getenv("CIRCLECI"):
            return "circleci"
        elif os.getenv("TRAVIS"):
            return "travis"
        elif os.getenv("CI"):
            return "generic_ci"
        else:
            return "local"

    @staticmethod
    def is_ci_environment() -> bool:
        """CI環境かどうかを判定"""
        return CIEnvironmentInfo.detect_ci_environment() != "local"

    @staticmethod
    def get_github_actions_info() -> dict[str, Any]:
        """GitHub Actions環境情報を取得"""
        return {
            "runner_os": os.getenv("RUNNER_OS"),
            "runner_arch": os.getenv("RUNNER_ARCH"),
            "github_workflow": os.getenv("GITHUB_WORKFLOW"),
            "github_action": os.getenv("GITHUB_ACTION"),
            "github_actor": os.getenv("GITHUB_ACTOR"),
            "github_repository": os.getenv("GITHUB_REPOSITORY"),
            "github_ref": os.getenv("GITHUB_REF"),
            "github_sha": os.getenv("GITHUB_SHA"),
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "github_run_number": os.getenv("GITHUB_RUN_NUMBER"),
            "github_job": os.getenv("GITHUB_JOB"),
            "github_step_summary": os.getenv("GITHUB_STEP_SUMMARY"),
        }

    @staticmethod
    def get_ci_metadata() -> dict[str, Any]:
        """CI環境のメタデータを取得"""
        ci_type = CIEnvironmentInfo.detect_ci_environment()

        if ci_type == "github_actions":
            return CIEnvironmentInfo.get_github_actions_info()
        elif ci_type == "gitlab_ci":
            return {
                "gitlab_ci": os.getenv("GITLAB_CI"),
                "ci_job_id": os.getenv("CI_JOB_ID"),
                "ci_job_name": os.getenv("CI_JOB_NAME"),
                "ci_pipeline_id": os.getenv("CI_PIPELINE_ID"),
                "ci_commit_sha": os.getenv("CI_COMMIT_SHA"),
                "ci_commit_ref_name": os.getenv("CI_COMMIT_REF_NAME"),
            }
        else:
            return {"ci_type": ci_type}

    @staticmethod
    def collect_environment_vars() -> dict[str, str]:
        """CI関連の環境変数を収集"""
        ci_prefixes = ["GITHUB_", "CI_", "RUNNER_", "GITLAB_", "JENKINS_"]
        ci_vars = ["TRAVIS", "CIRCLECI"]  # 単体の環境変数名

        result: dict[str, str] = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in ci_prefixes) or key in ci_vars:
                result[key] = value

        return result

    @staticmethod
    def get_system_info() -> dict[str, Any]:
        """システム情報を取得"""
        try:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

            # Git情報を取得
            git_info = {}
            try:
                from .security_helpers import safe_subprocess_run

                git_commit_result = safe_subprocess_run(
                    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
                )
                git_info["commit"] = git_commit_result.stdout.strip()

                git_branch_result = safe_subprocess_run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=10
                )
                git_info["branch"] = git_branch_result.stdout.strip()

            except (subprocess.CalledProcessError, FileNotFoundError):
                git_info = {"commit": "unknown", "branch": "unknown"}

            return {
                "python_version": python_version,
                "platform": sys.platform,
                "architecture": (os.uname().machine if hasattr(os, "uname") else "unknown"),
                "working_directory": os.getcwd(),
                "git_info": git_info,
                "environment_variables": CIEnvironmentInfo.collect_environment_vars(),
                "ci_type": CIEnvironmentInfo.detect_ci_environment(),
            }
        except Exception as e:
            return {"error": f"システム情報取得エラー: {str(e)}"}

    @staticmethod
    def get_dependency_info() -> dict[str, Any]:
        """依存関係情報を取得"""
        try:
            # uv環境情報
            uv_info = {}
            try:
                from .security_helpers import safe_subprocess_run

                uv_result = safe_subprocess_run(["uv", "--version"], capture_output=True, text=True, timeout=10)
                uv_info["version"] = uv_result.stdout.strip()

                # 仮想環境情報
                if "VIRTUAL_ENV" in os.environ:
                    uv_info["virtual_env"] = os.environ["VIRTUAL_ENV"]

            except (subprocess.CalledProcessError, FileNotFoundError):
                uv_info["error"] = "uv not found"

            # Python パッケージ情報
            packages_info = {}
            try:
                from .security_helpers import safe_subprocess_run

                pip_result = safe_subprocess_run(
                    [sys.executable, "-m", "pip", "list", "--format=json"], capture_output=True, text=True, timeout=30
                )
                packages = json.loads(pip_result.stdout)
                packages_info = {pkg["name"]: pkg["version"] for pkg in packages}

            except (subprocess.CalledProcessError, json.JSONDecodeError):
                packages_info["error"] = "パッケージ情報取得エラー"

            return {"uv_info": uv_info, "packages": packages_info}

        except Exception as e:
            return {"error": f"依存関係情報取得エラー: {str(e)}"}
