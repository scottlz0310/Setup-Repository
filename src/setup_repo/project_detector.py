"""プロジェクトタイプ自動検出機能"""

from pathlib import Path


class ProjectDetector:
    """プロジェクトタイプを自動検出するクラス"""

    # ファイル存在による検出ルール
    DETECTION_RULES = {
        "python": {
            "files": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
            "extensions": [".py"],
            "directories": ["src", "tests", "__pycache__"],
        },
        "node": {
            "files": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
            ],
            "extensions": [".js", ".ts", ".jsx", ".tsx"],
            "directories": ["node_modules", "src", "dist"],
        },
        "rust": {
            "files": ["Cargo.toml", "Cargo.lock"],
            "extensions": [".rs"],
            "directories": ["src", "target"],
        },
        "go": {
            "files": ["go.mod", "go.sum"],
            "extensions": [".go"],
            "directories": ["cmd", "pkg", "internal"],
        },
        "java": {
            "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "extensions": [".java", ".kt", ".scala"],
            "directories": ["src/main", "src/test", "target", "build"],
        },
        "csharp": {
            "files": ["*.csproj", "*.sln", "packages.config"],
            "extensions": [".cs", ".vb"],
            "directories": ["bin", "obj"],
        },
    }

    # 特殊ツール検出
    TOOL_DETECTION = {
        "uv": ["uv.lock", "pyproject.toml"],
        "vscode": [".vscode/settings.json", ".vscode/launch.json"],
        "docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "git": [".git", ".gitignore"],
    }

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)

    def detect_project_types(self) -> set[str]:
        """プロジェクトタイプを検出"""
        detected_types = set()

        for project_type, rules in self.DETECTION_RULES.items():
            if self._check_project_type(rules):
                detected_types.add(project_type)

        return detected_types

    def detect_tools(self) -> set[str]:
        """使用ツールを検出"""
        detected_tools = set()

        for tool, indicators in self.TOOL_DETECTION.items():
            if any(self._path_exists(indicator) for indicator in indicators):
                detected_tools.add(tool)

        return detected_tools

    def get_recommended_templates(self) -> list[str]:
        """推奨テンプレート一覧を取得"""
        templates = ["common"]  # 常に共通テンプレートを含める

        # プロジェクトタイプベースのテンプレート
        project_types = self.detect_project_types()
        templates.extend(project_types)

        # ツールベースのテンプレート
        tools = self.detect_tools()
        templates.extend(tools)

        return list(dict.fromkeys(templates))  # 重複除去

    def _check_project_type(self, rules: dict) -> bool:
        """プロジェクトタイプの検出ルールをチェック"""
        # ファイル存在チェック（ワイルドカード対応）
        for file_pattern in rules.get("files", []):
            if not file_pattern.strip():  # 空文字列チェック
                continue
            if "*" in file_pattern:
                if list(self.repo_path.glob(file_pattern)):
                    return True
            elif self._path_exists(file_pattern):
                return True

        # 拡張子チェック
        extensions = rules.get("extensions", [])
        if extensions and self._has_files_with_extensions(extensions):
            return True

        # ディレクトリ存在チェック
        return bool(any(self._path_exists(directory) for directory in rules.get("directories", [])))

    def _path_exists(self, path_str: str) -> bool:
        """パスの存在確認（パストラバーサル対策）"""
        from .security_helpers import safe_path_join

        try:
            # 安全なパス結合を使用
            safe_path = safe_path_join(self.repo_path, path_str)
            return safe_path.exists()
        except ValueError:
            return False

    def _has_files_with_extensions(self, extensions: list[str]) -> bool:
        """指定拡張子のファイルが存在するかチェック"""
        return any(list(self.repo_path.rglob(f"*{ext}")) for ext in extensions)

    def analyze_project(self) -> dict:
        """プロジェクト分析結果を返す"""
        return {
            "project_types": list(self.detect_project_types()),
            "tools": list(self.detect_tools()),
            "recommended_templates": self.get_recommended_templates(),
        }
