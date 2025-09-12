#!/usr/bin/env python3
"""uv自動インストールモジュール"""

import shutil
import subprocess


def ensure_uv() -> bool:
    """uvが利用可能かチェック、なければ自動インストール"""
    if shutil.which("uv"):
        print("🔍 uv を発見しました")
        return True

    print("⬇️ uv をインストール中...")

    # pipxを試す
    if shutil.which("pipx"):
        try:
            subprocess.run(["pipx", "install", "uv"], check=True, capture_output=True)
            print("✅ pipx で uv をインストールしました")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️  pipx インストール失敗: {e}, pip を試します")

    # pip --userを試す
    python_cmd = shutil.which("python3") or shutil.which("python")
    if python_cmd:
        try:
            subprocess.run(
                [python_cmd, "-m", "pip", "install", "--user", "uv"],
                check=True,
                capture_output=True,
            )
            print("✅ pip --user で uv をインストールしました")
            print("   ~/.local/bin を PATH に追加してください")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️  pip --user インストール失敗: {e}")

    print("❌ uv の自動インストールに失敗しました")
    return False
