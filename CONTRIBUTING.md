# 🤝 コントリビューションガイド

Setup-Repositoryプロジェクトへのコントリビューションをありがとうございます！このガイドでは、プロジェクトに貢献するための手順とコード品質基準について説明します。

## 📋 目次

- [開発環境のセットアップ](#開発環境のセットアップ)
- [コード品質基準](#コード品質基準)
- [Pre-commit設定](#pre-commit設定)
- [テスト要件](#テスト要件)
- [プルリクエストガイドライン](#プルリクエストガイドライン)
- [コーディング規約](#コーディング規約)

## 🚀 開発環境のセットアップ

### 1. 前提条件

- Python 3.9以上
- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (推奨パッケージマネージャー)

### 2. プロジェクトのクローンとセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository

# 自動開発環境セットアップ（推奨）
uv run python scripts/setup-dev-environment.py
```

#### 手動セットアップ（必要に応じて）

```bash
# 開発依存関係をインストール
uv sync --dev

# Pre-commitフックをセットアップ
uv run python scripts/setup-pre-commit.py

# VS Code設定を手動適用（プラットフォーム固有）
cp vscode-templates/linux/settings.json .vscode/settings.json  # Linux
cp vscode-templates/windows/settings.json .vscode/settings.json  # Windows
cp vscode-templates/wsl/settings.json .vscode/settings.json  # WSL
```

### 3. 設定ファイルの準備

```bash
# 設定テンプレートをコピー
cp config.json.template config.local.json

# 必要に応じて個人設定を編集
nano config.local.json
```

## 🛡️ コード品質基準

このプロジェクトでは、高いコード品質を維持するために以下のツールと基準を採用しています。

### 必須品質チェック

1. **Ruff** - リンティングとフォーマッティング
2. **BasedPyright** - 静的型チェック
3. **Pytest** - テストカバレッジ80%以上
4. **Bandit** - セキュリティ脆弱性チェック
5. **Safety** - 既知の脆弱性チェック

### 品質基準詳細

#### 1. Ruffリンティング基準

- **対象ルール**: E, F, W, I, N, UP, B, A, C4, T20, SIM, TCH
- **行長**: 120文字
- **インポート**: isortルールに従った自動整理
- **禁止事項**: print文の使用（T201 - 厳格）

#### 2. BasedPyright / Pyright 型チェック基準

**現在の段階（プロダクト段階）:**
- 厳格な型チェック
- 未型付け関数定義の禁止
- Any型の使用制限

#### 3. テストカバレッジ基準

- **最低カバレッジ**: 80%
- **測定対象**: src/setup_repo/
- **除外対象**: テストファイル、__pycache__、デバッグコード
- **レポート形式**: HTML、XML、ターミナル出力

#### 4. セキュリティ基準

**Bandit設定:**
- 対象: src/ディレクトリ
- 除外: テスト関連のassert使用、必要なsubprocess使用
- 重要度: 中レベル以上の脆弱性は修正必須

**Safety設定:**
- 既知の脆弱性データベースとの照合
- 重大な脆弱性は即座に修正

### 品質チェック実行

#### 統合品質チェック

```bash
# 全品質チェックを実行
uv run ruff check . && uv run ruff format . && uv run basedpyright src/ && uv run pytest

# Makefileを使用（利用可能な場合）
make quality-gate
```

#### 個別品質チェック

```bash
# リンティング
uv run ruff check .                    # エラー検出
uv run ruff check . --fix              # 自動修正付き

# フォーマッティング
uv run ruff format .                   # コードフォーマット

# 型チェック
uv run basedpyright src/                       # 静的型チェック

# テスト + カバレッジ
uv run pytest --cov=src/setup_repo    # カバレッジ付きテスト
uv run pytest --cov-fail-under=80     # カバレッジ品質ゲート

# セキュリティチェック
uv run bandit -r src/                  # セキュリティ脆弱性チェック
uv run safety scan                     # 既知の脆弱性チェック
```

#### CI/CD品質ゲート

プルリクエストでは以下の品質ゲートを通過する必要があります：

1. **Ruffリンティング**: エラー0件
2. **BasedPyright型チェック**: エラー0件
3. **テストカバレッジ**: 80%以上
4. **セキュリティチェック**: 重大な脆弱性0件
5. **全テスト**: 100%通過

### 品質チェック自動化

#### Pre-commitフック

コミット時に自動実行される品質チェック：

```bash
# Pre-commitフックをインストール
uv run pre-commit install

# 手動実行
uv run pre-commit run --all-files
```

**実行される内容:**
- Ruffリンティング（自動修正付き）
- **BasedPyright**: 型チェック（src/ディレクトリのみ）
- Banditセキュリティチェック
- 基本ファイルチェック（末尾改行、空白削除等）
- 単体テスト実行
- Safety脆弱性チェック

## 🔧 Pre-commit設定

Pre-commitフックを使用することで、コミット前に自動的に品質チェックが実行されます。

### セットアップ

```bash
# 自動セットアップ（推奨）
uv run python scripts/setup-pre-commit.py

# または手動セットアップ
uv run pre-commit install
```

### Pre-commitフック内容

- **Ruff**: リンティングと自動修正
- **Ruff Format**: コードフォーマッティング
- **BasedPyright / Pyright**: 型チェック（src/ディレクトリのみ）
- **基本チェック**: ファイル末尾、行末空白、YAML/JSON構文
- **Pytest**: 単体テスト実行

### 使用方法

```bash
# 手動実行
uv run pre-commit run --all-files

# 特定フックのみ実行
uv run pre-commit run ruff

# 緊急時のスキップ（非推奨）
git commit --no-verify
```

## 🧪 テスト要件

### テスト構造

```
tests/
├── unit/           # 単体テスト（高速、モック使用）
├── integration/    # 統合テスト（実際のファイル操作）
└── fixtures/       # テストデータ
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 単体テストのみ
uv run pytest tests/unit/ -v

# カバレッジ付き実行
uv run pytest --cov=src/setup_repo --cov-report=html

# 高速テストのみ（CIで使用）
uv run pytest -m "not slow"
```

### テスト要件

- **カバレッジ**: 80%以上
- **テストマーカー**: `unit`, `integration`, `slow`を適切に使用
- **モック**: 外部依存関係は適切にモック化
- **命名**: `test_`で始まる関数名

## 📝 プルリクエストガイドライン

### 1. ブランチ命名規則

```
feature/機能名          # 新機能
bugfix/バグ修正内容     # バグ修正
hotfix/緊急修正内容     # 緊急修正
refactor/リファクタ内容 # リファクタリング
```

### 2. コミットメッセージ

```
種類: 簡潔な説明

詳細な説明（必要に応じて）

- 変更点1
- 変更点2

Fixes #issue番号
```

**種類の例:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント更新
- `style`: フォーマット変更
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: その他の変更

### 3. プルリクエスト前チェックリスト

- [ ] 全品質チェックが通過している
- [ ] テストカバレッジが基準を満たしている
- [ ] 新機能にはテストが追加されている
- [ ] ドキュメントが更新されている（必要に応じて）
- [ ] CHANGELOG.mdが更新されている（重要な変更の場合）

### 4. プルリクエストテンプレート

```markdown
## 概要
この変更の概要を説明してください。

## 変更内容
- [ ] 新機能追加
- [ ] バグ修正
- [ ] リファクタリング
- [ ] ドキュメント更新
- [ ] テスト追加・修正

## テスト
- [ ] 既存テストが全て通過
- [ ] 新しいテストを追加
- [ ] カバレッジ基準を満たしている

## 関連Issue
Fixes #issue番号
```

## 📐 コーディング規約

### 1. 命名規則

- **ファイル・関数・変数**: `snake_case`
- **クラス**: `PascalCase`
- **定数**: `UPPER_SNAKE_CASE`
- **プライベート**: `_leading_underscore`

### 2. 型ヒント

```python
# 必須: 関数の引数と戻り値に型ヒント
def process_config(config: Dict[str, Any]) -> bool:
    """設定を処理する"""
    pass

# 推奨: 変数の型ヒント（複雑な場合）
repos: List[Dict[str, str]] = []
```

### 3. ドキュメント

```python
def example_function(param1: str, param2: int) -> bool:
    """
    関数の説明

    Args:
        param1: パラメータ1の説明
        param2: パラメータ2の説明

    Returns:
        bool: 成功した場合True

    Raises:
        ValueError: 無効な値の場合
    """
    pass
```

### 4. エラーハンドリング

```python
# 具体的な例外を使用
try:
    result = risky_operation()
except FileNotFoundError as e:
    logger.error(f"ファイルが見つかりません: {e}")
    return False
except PermissionError as e:
    logger.error(f"権限エラー: {e}")
    return False
```

### 5. ログ出力

```python
import logging

# print()は禁止、loggingを使用
logger = logging.getLogger(__name__)

def example():
    logger.info("処理を開始します")
    logger.debug("デバッグ情報")
    logger.warning("警告メッセージ")
    logger.error("エラーが発生しました")
```

## 📈 品質基準の設定

### 品質基準の目安

**BasedPyright / Pyright 設定:**
- 完全なstrict設定
- `disallow_any_* = true`（全設定）
- `warn_unreachable = true`
- `strict_equality = true`

**テストカバレッジ:**
- 最低基準: 80%
- 目標: 90%

**Ruff設定:**
- 全ルール適用
- カスタムルールの追加

**セキュリティ:**
- SAST（Static Application Security Testing）統合
- 依存関係の自動脆弱性監視
- セキュリティコードレビュー必須

### 品質基準の例外処理

以下の場合に限り、品質基準の一時的な緩和を認めます：

1. **緊急バグ修正**: セキュリティ脆弱性の即座の修正
2. **外部依存関係**: サードパーティライブラリの制約
3. **レガシーコード**: 段階的リファクタリング中のコード

**例外申請プロセス:**
1. GitHub Issueで例外理由を説明
2. メンテナーによる承認
3. 修正期限の設定（通常1-2週間）
4. 追跡用ラベルの付与

## 🆘 ヘルプとサポート

### 質問やサポートが必要な場合

1. [GitHub Issues](https://github.com/scottlz0310/Setup-Repository/issues)で質問を投稿
2. 既存のIssueを検索して重複を避ける
3. 問題の再現手順を詳細に記載

### 開発環境の問題

```bash
# 環境をクリーンアップ
uv clean

# 依存関係を再インストール
uv sync --dev

# Pre-commitを再セットアップ
uv run python scripts/setup-pre-commit.py
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。コントリビューションを行うことで、あなたの変更もMITライセンスの下で公開されることに同意したものとみなされます。

---

ご質問やご提案がございましたら、お気軽にIssueを作成してください。皆様のコントリビューションをお待ちしています！ 🚀
