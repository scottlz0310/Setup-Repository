#!/usr/bin/env python3
"""セキュリティ設定統一管理ヘルパー

pyproject.tomlからセキュリティ関連設定を読み込み、
pre-commitフックとCI/CDワークフローで統一的に使用する。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def load_security_config(config_path: Path = None) -> Dict:
    """pyproject.tomlからセキュリティ設定を読み込み"""
    if config_path is None:
        config_path = Path("pyproject.toml")
    
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    
    return {
        "bandit": config.get("tool", {}).get("bandit", {}),
        "coverage": config.get("tool", {}).get("coverage", {}),
        "security": config.get("tool", {}).get("security", {}),
        "security_deps": config.get("dependency-groups", {}).get("security", []),
        "ruff": config.get("tool", {}).get("ruff", {}),
    }


def get_bandit_config() -> Dict:
    """Bandit設定を取得"""
    config = load_security_config()
    bandit_config = config["bandit"]
    
    return {
        "exclude_dirs": bandit_config.get("exclude_dirs", ["tests", "venv", ".venv"]),
        "skips": bandit_config.get("skips", []),
        "severity": bandit_config.get("severity", "medium"),
        "confidence": bandit_config.get("confidence", "medium"),
    }


def get_coverage_threshold() -> float:
    """カバレッジ閾値を取得"""
    config = load_security_config()
    return config["coverage"].get("report", {}).get("fail_under", 70.0)


def get_security_tools() -> List[str]:
    """利用可能なセキュリティツールリストを取得"""
    config = load_security_config()
    
    # pyproject.tomlから必須・オプションツールを取得
    security_config = config.get("security", {})
    required_tools = security_config.get("required_tools", ["bandit", "safety"])
    optional_tools = security_config.get("optional_tools", ["trufflehog", "pip-licenses"])
    
    return required_tools + optional_tools


def get_ruff_security_rules() -> List[str]:
    """Ruffのセキュリティ関連ルールを取得"""
    config = load_security_config()
    ruff_config = config["ruff"]
    
    lint_config = ruff_config.get("lint", {})
    selected_rules = lint_config.get("select", [])
    
    # セキュリティ関連ルールを抽出
    security_rules = []
    for rule in selected_rules:
        if rule in ["B", "S", "T20"]:  # bandit, security, print禁止
            security_rules.append(rule)
    
    return security_rules


def generate_bandit_args() -> List[str]:
    """Bandit実行用引数を生成"""
    config = get_bandit_config()
    
    args = ["-r", "src/", "-f", "json"]
    
    if config["exclude_dirs"]:
        args.extend(["--exclude", ",".join(config["exclude_dirs"])])
    
    if config["skips"]:
        args.extend(["--skip", ",".join(config["skips"])])
    
    return args


def generate_safety_args() -> List[str]:
    """Safety実行用引数を生成"""
    return ["check", "--json", "--output", "safety-report.json"]


def generate_trufflehog_args() -> List[str]:
    """TruffleHog実行用引数を生成"""
    return ["git", "file://.", "--json", "--output", "trufflehog-report.json"]


def get_license_check_args() -> List[str]:
    """pip-licenses実行用引数を生成"""
    return ["--format=json", "--output-file=licenses-report.json"]


def main():
    """設定情報を出力"""
    import json
    
    try:
        config_info = {
            "bandit": get_bandit_config(),
            "coverage_threshold": get_coverage_threshold(),
            "security_tools": get_security_tools(),
            "ruff_security_rules": get_ruff_security_rules(),
            "bandit_args": generate_bandit_args(),
            "safety_args": generate_safety_args(),
            "trufflehog_args": generate_trufflehog_args(),
            "license_check_args": get_license_check_args(),
        }
        
        print(json.dumps(config_info, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()