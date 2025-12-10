"""プロジェクトタイプ自動検出機能（スコアリングシステム）"""

from pathlib import Path
from typing import Any, TypedDict


class FileCountConfig(TypedDict, total=False):
    """ファイル数スコア設定"""

    extensions: list[str]
    score_per_file: float
    max_score: float
    exclude_dirs: list[str]


class ScoringRule(TypedDict, total=False):
    """スコアリングルール"""

    primary_files: dict[str, int]
    secondary_files: dict[str, int]
    file_count: FileCountConfig
    directories: dict[str, int]
    threshold: int


class ProjectAnalysisResult(TypedDict):
    """プロジェクト分析結果"""

    project_types: list[str]
    scores: dict[str, dict[str, Any]]
    tools: list[str]
    recommended_templates: list[str]


class ProjectDetector:
    """プロジェクトタイプを自動検出するクラス（スコアリング方式）"""

    # スコアリングベースの検出ルール
    SCORING_RULES: dict[str, ScoringRule] = {
        "python": {
            "primary_files": {  # 強い証拠（プロジェクト定義ファイル）
                "pyproject.toml": 10,
                "setup.py": 8,
                "setup.cfg": 7,
            },
            "secondary_files": {  # 中程度の証拠（依存関係ファイル）
                "requirements.txt": 3,
                "Pipfile": 3,
                "Pipfile.lock": 2,
                "uv.lock": 3,
                "poetry.lock": 3,
            },
            "file_count": {  # ファイル数ボーナス
                "extensions": [".py"],
                "score_per_file": 0.5,  # 1ファイルあたり0.5点
                "max_score": 10,  # 最大10点まで
                "exclude_dirs": ["__pycache__", ".venv", "venv", "env"],
            },
            "directories": {  # ディレクトリ存在
                "__pycache__": 2,
                ".venv": 2,
                "venv": 2,
                ".pytest_cache": 1,
            },
            "threshold": 10,  # 10点以上でプロジェクトと判定
        },
        "node": {
            "primary_files": {
                "package.json": 10,
                "package-lock.json": 5,
                "yarn.lock": 5,
                "pnpm-lock.yaml": 5,
            },
            "secondary_files": {
                "tsconfig.json": 3,
                ".npmrc": 2,
                ".yarnrc": 2,
            },
            "file_count": {
                "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"],
                "score_per_file": 0.5,
                "max_score": 10,
                "exclude_dirs": ["node_modules", "dist", "build", ".next"],
            },
            "directories": {
                "node_modules": 3,
                "src": 1,
                "dist": 1,
                "build": 1,
            },
            "threshold": 10,
        },
        "rust": {
            "primary_files": {
                "Cargo.toml": 10,
                "Cargo.lock": 5,
            },
            "secondary_files": {
                "rust-toolchain.toml": 2,
                "rust-toolchain": 2,
            },
            "file_count": {
                "extensions": [".rs"],
                "score_per_file": 1.0,
                "max_score": 10,
                "exclude_dirs": ["target"],
            },
            "directories": {
                "src": 2,
                "target": 2,
            },
            "threshold": 10,
        },
        "go": {
            "primary_files": {
                "go.mod": 10,
                "go.sum": 5,
            },
            "secondary_files": {
                "go.work": 3,
            },
            "file_count": {
                "extensions": [".go"],
                "score_per_file": 1.0,
                "max_score": 10,
                "exclude_dirs": ["vendor"],
            },
            "directories": {
                "cmd": 2,
                "pkg": 2,
                "internal": 2,
                "vendor": 1,
            },
            "threshold": 10,
        },
        "java": {
            "primary_files": {
                "pom.xml": 10,
                "build.gradle": 10,
                "build.gradle.kts": 10,
            },
            "secondary_files": {
                "settings.gradle": 3,
                "settings.gradle.kts": 3,
                "gradle.properties": 2,
            },
            "file_count": {
                "extensions": [".java", ".kt", ".scala"],
                "score_per_file": 0.5,
                "max_score": 10,
                "exclude_dirs": ["target", "build", ".gradle"],
            },
            "directories": {
                "src/main": 3,
                "src/test": 2,
                "target": 1,
                "build": 1,
            },
            "threshold": 10,
        },
        "csharp": {
            "primary_files": {
                "*.sln": 10,
                "*.csproj": 10,
            },
            "secondary_files": {
                "packages.config": 3,
                "nuget.config": 2,
            },
            "file_count": {
                "extensions": [".cs", ".vb"],
                "score_per_file": 0.5,
                "max_score": 10,
                "exclude_dirs": ["bin", "obj"],
            },
            "directories": {
                "bin": 2,
                "obj": 2,
            },
            "threshold": 10,
        },
    }

    # 特殊ツール検出
    TOOL_DETECTION: dict[str, list[str]] = {
        "uv": ["uv.lock", "pyproject.toml"],
        "vscode": [".vscode/settings.json", ".vscode/launch.json"],
        "docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "git": [".git", ".gitignore"],
    }

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = Path(repo_path)
        self._file_count_cache: dict[str, int] = {}  # ファイル数のキャッシュ

    def detect_project_types(self) -> list[str]:
        """
        プロジェクトタイプを検出（スコアリング方式）

        各プロジェクトタイプのスコアを計算し、閾値以上のものをすべて返す。
        複数のプロジェクトタイプが検出される場合（例：node + python）、
        スコアが高い順に返される。

        Returns:
            検出されたプロジェクトタイプのリスト（スコアの高い順）
        """
        scores = {}

        for project_type, rules in self.SCORING_RULES.items():
            score = self._calculate_score(project_type, rules)
            threshold: int = rules.get("threshold", 10)  # type: ignore[assignment]

            if score >= threshold:
                scores[project_type] = score

        # スコアの高い順にソート
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [project_type for project_type, _ in sorted_types]

    def _calculate_score(self, project_type: str, rules: ScoringRule) -> float:
        """
        プロジェクトタイプのスコアを計算

        Args:
            project_type: プロジェクトタイプ名
            rules: スコアリングルール

        Returns:
            計算されたスコア
        """
        total_score = 0.0

        # 1. プライマリファイル（強い証拠）
        primary_files = rules.get("primary_files", {})
        for file_pattern, score in primary_files.items():
            if self._check_file_pattern(file_pattern):
                total_score += score

        # 2. セカンダリファイル（中程度の証拠）
        secondary_files = rules.get("secondary_files", {})
        for file_pattern, score in secondary_files.items():
            if self._check_file_pattern(file_pattern):
                total_score += score

        # 3. ファイル数ボーナス
        file_count_config = rules.get("file_count", {})
        if file_count_config:
            file_count_score = self._calculate_file_count_score(file_count_config)
            total_score += file_count_score

        # 4. ディレクトリ存在
        directories = rules.get("directories", {})
        for directory, score in directories.items():
            if self._path_exists(directory):
                total_score += score

        return total_score

    def _calculate_file_count_score(self, config: FileCountConfig) -> float:
        """
        ファイル数ベースのスコアを計算

        Args:
            config: ファイル数スコア設定

        Returns:
            計算されたスコア（max_scoreでキャップ）
        """
        extensions = config.get("extensions", [])
        score_per_file = config.get("score_per_file", 0.5)
        max_score = config.get("max_score", 10)
        exclude_dirs = config.get("exclude_dirs", [])

        total_files = 0
        for ext in extensions:
            # キャッシュをチェック
            cache_key = f"{ext}:{','.join(exclude_dirs)}"
            if cache_key in self._file_count_cache:
                total_files += self._file_count_cache[cache_key]
            else:
                count = self._count_files_with_extension(ext, exclude_dirs)
                self._file_count_cache[cache_key] = count
                total_files += count

        # スコア計算（最大値でキャップ）
        score = min(total_files * score_per_file, max_score)
        return score

    def _count_files_with_extension(self, extension: str, exclude_dirs: list[str]) -> int:
        """
        指定拡張子のファイル数をカウント（除外ディレクトリを考慮）

        Args:
            extension: ファイル拡張子（例: ".py"）
            exclude_dirs: 除外するディレクトリのリスト

        Returns:
            ファイル数
        """
        count = 0
        try:
            for file_path in self.repo_path.rglob(f"*{extension}"):
                # 除外ディレクトリに含まれているかチェック
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                count += 1
                # パフォーマンス対策：1000ファイル以上はカウントしない
                if count >= 1000:
                    break
        except (OSError, PermissionError):
            pass
        return count

    def _check_file_pattern(self, file_pattern: str) -> bool:
        """
        ファイルパターンの存在をチェック（ワイルドカード対応）

        Args:
            file_pattern: ファイルパターン（例: "*.csproj", "package.json"）

        Returns:
            ファイルが存在すればTrue
        """
        if "*" in file_pattern:
            # ワイルドカードパターンは再帰的に探索する（例: "*.csproj" がサブフォルダに存在する場合）
            try:
                return bool(list(self.repo_path.rglob(file_pattern)))
            except (OSError, ValueError):
                return False
        else:
            # 通常のファイル
            return self._path_exists(file_pattern)

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

    def _path_exists(self, path_str: str) -> bool:
        """パスの存在確認（パストラバーサル対策）"""
        from .security_helpers import safe_path_join

        try:
            # 安全なパス結合を使用
            safe_path = safe_path_join(self.repo_path, path_str)
            return safe_path.exists()
        except ValueError:
            return False

    def analyze_project(self) -> ProjectAnalysisResult:
        """
        プロジェクト分析結果を返す（詳細情報付き）

        Returns:
            分析結果の辞書（プロジェクトタイプ、スコア、ツール、推奨テンプレート）
        """
        # 各プロジェクトタイプのスコアを計算
        scores: dict[str, dict[str, Any]] = {}
        for project_type, rules in self.SCORING_RULES.items():
            score = self._calculate_score(project_type, rules)
            if score > 0:  # スコアが0より大きいもののみ記録
                threshold: int = rules.get("threshold", 10)  # type: ignore[assignment]
                scores[project_type] = {
                    "score": score,
                    "threshold": threshold,
                    "detected": score >= threshold,
                }

        return ProjectAnalysisResult(
            project_types=self.detect_project_types(),
            scores=scores,
            tools=list(self.detect_tools()),
            recommended_templates=self.get_recommended_templates(),
        )
