# 開発プロンプト

## 🎯 プロジェクト概要

クロスプラットフォーム対応のGitHubリポジトリセットアップ・同期ツールの開発。包括的なコード品質管理、CI/CDパイプライン、自動依存関係管理を統合したモダンなPythonプロジェクト。

## 📋 開発要件

### 基本方針
- **日本語優先**: 応答、ドキュメント、コメントは日本語で記述
- **最小実装**: 要件を満たす最小限のコードで実装（冗長性を避ける）
- **責務分離**: 各モジュール・関数は単一の責務を持つ
- **マルチプラットフォーム**: Windows、Linux、macOS対応

### 技術スタック
- **Python**: 3.9+、型ヒント必須
- **パッケージ管理**: uv（仮想環境・依存関係）
- **テスト**: pytest（実環境テスト優先）
- **品質管理**: ruff（リント・フォーマット）、mypy（型チェック）
- **CI/CD**: GitHub Actions

## 🧪 テスト戦略

### マルチプラットフォームテスト方針
```python
# プラットフォーム固有テストの例
import platform
import pytest

def test_windows_specific():
    if platform.system() != "Windows":
        pytest.skip("Windows環境でのみ実行")
    # Windows固有のテスト

# ヘルパー関数活用
from tests.multiplatform.helpers import verify_current_platform

def test_with_helper():
    platform_info = verify_current_platform()
    # プラットフォーム情報を活用したテスト
```

### テスト分類
- **単体テスト**: `tests/unit/` - 個別機能のテスト
- **統合テスト**: `tests/integration/` - 機能間連携のテスト
- **マルチプラットフォーム**: `tests/multiplatform/` - プラットフォーム固有テスト

## 🛡️ 品質管理

### 必須チェック
```bash
# 品質チェック実行
uv run ruff check .          # リンティング
uv run ruff format .         # フォーマッティング
uv run mypy src/             # 型チェック
uv run pytest               # テスト実行
uv run safety check          # セキュリティチェック
```

### カバレッジ目標
- 全プラットフォーム共通機能: **95%以上**
- プラットフォーム固有機能: **各環境で90%以上**
- 統合テスト: **主要ワークフローの85%以上**

## 📁 プロジェクト構造

```
Setup-Repository/
├── src/setup_repo/          # メインコード
├── tests/                   # テストコード
│   ├── unit/               # 単体テスト
│   ├── integration/        # 統合テスト
│   └── multiplatform/      # マルチプラットフォームテスト
├── docs/                   # ドキュメント
├── scripts/                # 補助スクリプト
└── pyproject.toml          # 設定統合
```

## 🚀 開発ワークフロー

### 1. 環境セットアップ
```bash
uv venv                     # 仮想環境作成
uv sync --dev              # 依存関係インストール
uv run python scripts/setup-pre-commit.py  # Pre-commit設定
```

### 2. 実装・テスト
```bash
# 実装後の品質チェック
uv run ruff check . && uv run ruff format . && uv run mypy src/ && uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src/setup_repo --cov-report=html
```

### 3. リリース
```bash
make quality-gate           # 品質ゲート
make version-bump TYPE=patch  # バージョン更新
git push origin main && git push origin --tags  # リリース
```

## 🎯 実装ガイドライン

### コーディング規約
- **PEP 8準拠**: 行長88文字、型ヒント必須
- **日本語docstring**: 関数・クラスの説明は日本語
- **ログ使用**: print禁止、loggingモジュール使用
- **エラーハンドリング**: 適切な例外処理

### 禁止事項
- print関数によるデバッグ出力
- `--system`フラグの使用（CI以外）
- モックに依存したテスト設計
- 英語への自動切り替え

### 推奨パターン
```python
# 型ヒント付きの関数定義
def setup_repository(config: Dict[str, Any]) -> bool:
    """リポジトリセットアップを実行する。

    Args:
        config: 設定辞書

    Returns:
        bool: セットアップ成功時True

    Raises:
        SetupError: セットアップ失敗時
    """
    logger.info("リポジトリセットアップを開始")
    # 実装
```

## 🔧 開発支援ツール

### Pre-commit設定
- **自動品質チェック**: コミット前にruff、mypy、pytest実行
- **自動修正**: フォーマット・リント問題の自動修正

### VS Code統合
- **推奨拡張機能**: Python、Ruff、MyPy統合
- **自動設定**: 保存時フォーマット、リアルタイム型チェック

### CI/CD統合
- **GitHub Actions**: 全プラットフォームでの自動テスト
- **品質ゲート**: リリース前の自動品質チェック
- **セキュリティスキャン**: 脆弱性・シークレット検出

## 📊 成果指標

### 品質メトリクス
- **テストカバレッジ**: 90%以上維持
- **CI成功率**: 95%以上
- **セキュリティスコア**: 脆弱性ゼロ維持

### パフォーマンス
- **CI実行時間**: 10分以内
- **テスト実行時間**: 5分以内
- **セットアップ時間**: 2分以内

## 🎯 開発プロンプト例

### 新機能実装時
```
以下の要件で新機能を実装してください：

1. 機能概要: [具体的な機能説明]
2. 入力/出力: [型ヒント付きで明記]
3. プラットフォーム対応: [Windows/Linux/macOS対応要否]
4. テスト要件: [単体・統合テストの範囲]
5. セキュリティ考慮: [セキュリティ要件]

実装方針：
- 最小限のコードで要件を満たす
- マルチプラットフォームテスト方針に準拠
- ヘルパー関数を活用した実装
- 日本語でのドキュメント・コメント
```

### バグ修正時
```
以下のバグを修正してください：

1. 問題の詳細: [具体的な問題説明]
2. 再現手順: [ステップバイステップ]
3. 期待される動作: [正しい動作の説明]
4. 影響範囲: [プラットフォーム・機能への影響]

修正方針：
- 根本原因の特定と修正
- 回帰テストの追加
- 関連機能への影響確認
- セキュリティ影響の評価
```
