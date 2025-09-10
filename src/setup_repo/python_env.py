#!/usr/bin/env python3
"""Python環境セットアップモジュール"""

import shutil
import subprocess
from pathlib import Path

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
                subprocess.run(
                    ["uv", "lock"], cwd=repo_path, check=True, capture_output=True
                )
            subprocess.run(
                ["uv", "venv"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["uv", "sync"], cwd=repo_path, check=True, capture_output=True
            )
        elif (repo_path / "requirements.txt").exists():
            subprocess.run(
                ["uv", "venv"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["uv", "pip", "install", "-r", "requirements.txt"],
                cwd=repo_path,
                check=True,
                capture_output=True,
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
        subprocess.run(
            ["python3", "-m", "venv", str(venv_path)], check=True, capture_output=True
        )

        pip_path = venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = venv_path / "Scripts" / "pip.exe"

        subprocess.run(
            [str(pip_path), "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )

        if (repo_path / "requirements.txt").exists():
            subprocess.run(
                [str(pip_path), "install", "-r", "requirements.txt"],
                check=True,
                capture_output=True,
            )

        print(f"   ✅ {repo_name}: venv環境セットアップ完了")
        return True

    except subprocess.CalledProcessError:
        print(f"   ❌ {repo_name}: venv環境セットアップ失敗")
        return False
