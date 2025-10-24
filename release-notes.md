# 🚀 Setup Repository v1.3.9

## 📋 変更内容

### ✨ 新機能
- print関数を修正して出力をフラッシュするように変更
- SSH接続の事前検証機能を追加
- Windows環境でGitHubの公開ホストキーを直接追加
- アーカイブされたリポジトリをスキップする機能を追加

### 🔄 変更
- refactor: simplify GitHub Actions workflows
- Refactor cross-platform compatibility tests to use fixtures

### 🐛 修正
- CI/CDパイプラインから拡張マトリックステストとスケジュールを削除
- fix(tests): Windows環境での並列テスト実行時のクラッシュを修正
- PythonバージョンとCLIフレームワークの情報を更新
- Windows環境でのCLIヘルプテストのUnicodeEncodeErrorを修正
- pytest実行時のWindows環境でのstdout/stderrバッファdetach問題を修正
- Windows環境でキャプチャを完全に無効化
- Windows環境でのpytestプラグイン重複登録エラーを修正
- Windows環境でのpytestバッファ問題を修正
- Ruffのlintエラーを修正 - ci-platform-diagnostics.py
- pytest プラグインの重複登録エラーを修正
- 全プラットフォームでの出力バッファリングを無効化
- ssh-keyscanのstderrを無視してstdoutのみ処理
- Windows版ssh-keyscanに対応
- known_hostsのGitHubエントリを強制的に更新
- ホストキー追加を初回のみ実行するように改善
- ssh-keyscanのエラーハンドリングを改善
- Windows環境でのSSH接続失敗を修正
- Windows環境でのUnicodeエンコーディング問題を改善
- cli.pyにmain関数を追加してグローバルツール対応

### 🔧 その他
- chore: Ruffのバージョンをv0.13.3からv0.14.0に更新
- perf: pytest-xdist並列実行を有効化してテスト実行時間を34秒から11秒に改善
- docs: グローバルツールインストール方法を追加
- docs: ブランチクリーンナップの事前準備を追記
- 🚀 リリース v1.3.8 準備完了

## 📦 インストール方法

### 🐍 Pythonパッケージとして
```bash
pip install setup-repository
```

### 📥 ソースからインストール
```bash
git clone https://github.com/scottlz0310/Setup-Repository.git
cd Setup-Repository
uv sync --dev
uv run main.py setup
```

## 🔧 使用方法

```bash
# 初期セットアップ
setup-repo setup

# リポジトリ同期
setup-repo sync

# ドライランモード
setup-repo sync --dry-run
```

## 🌐 サポートプラットフォーム

- ✅ Windows (Scoop, Winget, Chocolatey)
- ✅ Linux (Snap, APT)
- ✅ WSL (Linux互換)
- ✅ macOS (Homebrew)

## 🐍 Python要件

- Python 3.11以上
- 対応バージョン: 3.11, 3.12, 3.13

---

**完全な変更履歴**: [CHANGELOG.md](https://github.com/scottlz0310/Setup-Repository/blob/main/CHANGELOG.md)
