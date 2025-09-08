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

