#!/usr/bin/env python3
"""Python環境セットアップモジュール"""

import subprocess
from pathlib import Path

from .security_helpers import safe_subprocess
from .uv_installer import ensure_uv


def has_python_project(repo_path: Path) -> bool:
    """Pythonプロジェクトかどうかを判定"""
    python_files = [
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "Pipfile",
        "setup.cfg",
        "poetry.lock",
    ]
    return any((repo_path / f).exists() for f in python_files)


def setup_python_environment(repo_path: Path, dry_run: bool = False) -> bool:
    """Python環境をセットアップ"""
    if not has_python_project(repo_path):
        return True

    repo_name = repo_path.name
    print(f"   🐍 {repo_name}: Python環境セットアップ中...")

    if dry_run:
        print(f"   ✅ {repo_name}: Python環境セットアップ予定")
        return True

    if ensure_uv():
        return _setup_with_uv(repo_path)
    else:
        return _setup_with_venv(repo_path)


def _setup_with_uv(repo_path: Path) -> bool:
    """uvを使用してPython環境をセットアップ"""
    repo_name = repo_path.name

    try:
        if (repo_path / "pyproject.toml").exists():
            if not (repo_path / "uv.lock").exists():
                safe_subprocess(["uv", "lock"], cwd=repo_path, check=True, capture_output=True, timeout=300)
            safe_subprocess(["uv", "venv"], cwd=repo_path, check=True, capture_output=True, timeout=300)
            safe_subprocess(["uv", "sync"], cwd=repo_path, check=True, capture_output=True, timeout=300)
        elif (repo_path / "requirements.txt").exists():
            safe_subprocess(["uv", "venv"], cwd=repo_path, check=True, capture_output=True, timeout=300)
            safe_subprocess(
                ["uv", "pip", "install", "-r", "requirements.txt"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                timeout=300,
            )

        print(f"   ✅ {repo_name}: uv環境セットアップ完了")
        return True

    except subprocess.CalledProcessError:
        return _setup_with_venv(repo_path)


def _setup_with_venv(repo_path: Path) -> bool:
    """標準venvを使用してPython環境をセットアップ"""
    repo_name = repo_path.name

    try:
        venv_path = repo_path / ".venv"
        # Windowsではpython3が存在しない場合があるため、pythonも試す
        python_cmd = "python3"
        try:
            safe_subprocess([python_cmd, "-m", "venv", str(venv_path)], check=True, capture_output=True, timeout=300)
        except (FileNotFoundError, OSError):
            python_cmd = "python"
            safe_subprocess([python_cmd, "-m", "venv", str(venv_path)], check=True, capture_output=True, timeout=300)

        pip_path = venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = venv_path / "Scripts" / "pip.exe"

        # pipパスが存在しない場合はエラー（CI環境ではスキップ）
        if not pip_path.exists():
            import os

            if os.environ.get("CI") or os.environ.get("PYTEST_CURRENT_TEST"):
                print(f"   ⚠️ {repo_name}: CI環境でのpipパス問題（スキップ）")
                return False
            raise FileNotFoundError(f"pip not found in venv: {pip_path}")

        safe_subprocess([str(pip_path), "install", "--upgrade", "pip"], check=True, capture_output=True, timeout=300)

        if (repo_path / "requirements.txt").exists():
            safe_subprocess(
                [str(pip_path), "install", "-r", "requirements.txt"],
                check=True,
                capture_output=True,
                timeout=300,
            )

        print(f"   ✅ {repo_name}: venv環境セットアップ完了")
        return True

    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        import os

        if os.environ.get("CI") or os.environ.get("PYTEST_CURRENT_TEST"):
            print(f"   ⚠️ {repo_name}: CI環境でのvenvセットアップエラー: {e}")
        else:
            print(f"   ❌ {repo_name}: venv環境セットアップ失敗")
        return False
