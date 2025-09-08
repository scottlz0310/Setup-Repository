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
winget install --id=astral-sh.uv
```

## 🏃‍♂️ クイックスタート

1. **初期セットアップ**
   ```bash
   python first-setup.py
   # または
   ./first-setup.py
   ```

2. **設定の編集**
   ```bash
   # 必要に応じて個人設定を編集
   nano config.local.json
   ```

3. **リポジトリ同期実行**
   ```bash
   python repo-sync.py
   # または
   ./repo-sync.py
   ```

## ⚙️ 設定ファイル

- `config.json.template` - 設定テンプレート（リポジトリで管理）
- `config.local.json` - 個人設定（gitで除外）

## ✨ メリット

- ✅ 全プラットフォーム対応の単一コードベース
- ✅ 個人設定をgitから除外
- ✅ 簡単な設定管理
- ✅ プラットフォーム間で一貫した動作
- 🔧 モダンなパッケージマネージャー対応
- 🌐 日本語インターフェース

