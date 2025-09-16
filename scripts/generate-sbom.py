#!/usr/bin/env python3
"""
SBOM (Software Bill of Materials) 生成スクリプト

ルール6.2「依存監査・SBOM・ライセンス」に従って、
CycloneDX形式のSBOMを定期的に生成します。
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def run_command(cmd: list[str]) -> str:
    """コマンドを実行して結果を返す"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=Path(__file__).parent.parent)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"コマンド実行エラー: {' '.join(cmd)}")
        print(f"エラー: {e.stderr}")
        sys.exit(1)


def get_dependencies() -> list[dict[str, Any]]:
    """uv lockファイルから依存関係を取得"""
    try:
        # uv export でrequirements.txt形式で出力
        deps_output = run_command(["uv", "export", "--format", "requirements-txt"])

        dependencies = []
        for line in deps_output.strip().split("\n"):
            if line and not line.startswith("#") and "==" in line:
                # パッケージ名とバージョンを分離
                name, version = line.split("==", 1)
                # 追加の制約を削除
                version = version.split(";")[0].split(" ")[0]
                dependencies.append({"name": name.strip(), "version": version.strip(), "type": "library"})

        return dependencies
    except Exception as e:
        print(f"依存関係取得エラー: {e}")
        return []


def generate_cyclone_dx_sbom() -> dict[str, Any]:
    """CycloneDX形式のSBOMを生成"""
    dependencies = get_dependencies()

    # プロジェクト情報を取得
    try:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)

        project_info = pyproject.get("project", {})
        project_name = project_info.get("name", "setup-repository")
        project_version = project_info.get("version", "1.0.0")
    except Exception:
        project_name = "setup-repository"
        project_version = "1.0.0"

    # CycloneDX SBOM構造
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{project_name}-{datetime.now(UTC).isoformat()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "tools": [{"vendor": "setup-repository", "name": "generate-sbom.py", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "bom-ref": f"{project_name}@{project_version}",
                "name": project_name,
                "version": project_version,
            },
        },
        "components": [],
    }

    # 依存関係をコンポーネントとして追加
    for dep in dependencies:
        component = {
            "type": "library",
            "bom-ref": f"{dep['name']}@{dep['version']}",
            "name": dep["name"],
            "version": dep["version"],
            "scope": "required",
        }
        sbom["components"].append(component)

    return sbom


def main():
    """メイン処理"""
    print("SBOM生成を開始...")

    # 出力ディレクトリを作成
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # SBOM生成
    sbom = generate_cyclone_dx_sbom()

    # ファイル出力
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    sbom_file = output_dir / f"sbom_cyclonedx_{timestamp}.json"

    with open(sbom_file, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2, ensure_ascii=False)

    # 最新版のシンボリックリンクを作成
    latest_file = output_dir / "sbom_latest.json"
    if latest_file.exists():
        latest_file.unlink()

    try:
        latest_file.symlink_to(sbom_file.name)
    except OSError:
        # Windowsでシンボリックリンクが作成できない場合はコピー
        import shutil

        shutil.copy2(sbom_file, latest_file)

    print(f"SBOM生成完了: {sbom_file}")
    print(f"コンポーネント数: {len(sbom['components'])}")
    print(f"最新版: {latest_file}")


if __name__ == "__main__":
    main()
