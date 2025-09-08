# 🚀 リポジトリセットアップツール

クロスプラットフォーム対応のGitHubリポジトリセットアップ・同期ツールです。

## 📦 推奨: モダンパッケージマネージャーでuvをインストール

**Linux/WSL:**
```bash
sudo snap install --classic uv
```

**Windows:**
```powershell
scoop install uv
# または
winget install uv
```

## 🏃‍♂️ クイックスタート

1. **初期セットアップ**
   ```bash
   uv run main.py setup
   ```

2. **設定の編集**
   ```bash
   # 必要に応じて個人設定を編集
   nano config.local.json
   ```

3. **リポジトリ同期実行**
   ```bash
   uv run main.py sync
   # 実行内容確認
   uv run main.py sync --dry-run
   ```

## ⚙️ 設定ファイル

- `config.json.template` - 設定テンプレート（リポジトリで管理）
- `config.local.json` - 個人設定（gitで除外）

## 📚 ドキュメント

- [🚀 詳細セットアップガイド](docs/setup-guide.md)
- [🔧 トラブルシューティング](docs/setup-guide.md#🔍-トラブルシューティング)

## ✨ メリット

- ✅ 全プラットフォーム対応の単一コードベース
- ✅ 個人設定をgitから除外
- ✅ 簡単な設定管理
- ✅ プラットフォーム間で一貫した動作
- 🔧 モダンなパッケージマネージャー対応
- 🌐 日本語インターフェース

## 🧪 開発・テスト

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 単体テストのみ実行
uv run pytest tests/unit/ -v

# 統合テストのみ実行
uv run pytest tests/integration/ -v

# カバレッジ付きテスト実行
uv run pytest --cov=src/setup_repo --cov-report=html

# 特定のマーカーでテスト実行
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"
```

### コード品質チェック

```bash
# リンティング
uv run ruff check .

# フォーマッティング
uv run ruff format .

# 型チェック
uv run mypy src/

# 全品質チェック実行
uv run ruff check . && uv run ruff format . && uv run mypy src/ && uv run pytest
```

### 開発依存関係のインストール

```bash
# 開発依存関係を含む全依存関係をインストール
uv sync --dev
```

