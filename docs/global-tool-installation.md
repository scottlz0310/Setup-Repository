# グローバルツールインストールガイド

## 🌍 概要

`setup-repo`をグローバルツールとしてインストールすることで、任意のリポジトリでブランチクリーンナップ機能を使用できます。

## 📦 インストール

### GitHubから直接インストール

```bash
# 最新版をインストール
uv tool install git+https://github.com/scottlz0310/Setup-Repository.git

# 特定のバージョンをインストール
uv tool install git+https://github.com/scottlz0310/Setup-Repository.git@v1.3.8
```

### ローカルからインストール

```bash
# このリポジトリをクローン済みの場合
cd /path/to/Setup-Repository
uv tool install .
```

## 🚀 使い方

インストール後、任意のGitリポジトリで`setup-repo`コマンドが使用できます：

```bash
# 任意のリポジトリに移動
cd /path/to/your/project

# リモート状態を同期（必須）
git fetch --prune

# ブランチクリーンナップ
setup-repo cleanup list --merged
setup-repo cleanup clean --merged --dry-run
setup-repo cleanup clean --merged -y
```

## 🧹 ブランチクリーンナップ機能

### 基本コマンド

```bash
# ブランチ一覧
setup-repo cleanup list                    # 全リモートブランチ
setup-repo cleanup list --merged           # マージ済みブランチ
setup-repo cleanup list --stale --days 90  # 90日以上更新なし

# マージ済みブランチ削除
setup-repo cleanup clean --merged --dry-run  # 確認
setup-repo cleanup clean --merged -y         # 実行

# 古いブランチ削除
setup-repo cleanup clean --stale --days 90 --dry-run  # 確認
setup-repo cleanup clean --stale --days 90 -y         # 実行
```

### オプション

- `--merged`: マージ済みブランチを対象
- `--stale`: 古いブランチを対象
- `--days N`: 古いブランチの日数閾値（デフォルト: 90）
- `--base-branch`: ベースブランチ指定（デフォルト: origin/main）
- `--dry-run`: 実行内容を表示のみ
- `-y, --yes`: 確認なしで実行
- `--repo-path`: リポジトリパス指定（デフォルト: カレントディレクトリ）

## 🔄 更新・アンインストール

```bash
# 更新
uv tool upgrade setup-repository

# アンインストール
uv tool uninstall setup-repository

# インストール済みツール一覧
uv tool list
```

## 💡 使用例

### 複数リポジトリのクリーンナップ

```bash
# スクリプト例
for repo in ~/workspace/*; do
  if [ -d "$repo/.git" ]; then
    echo "🧹 Cleaning: $repo"
    cd "$repo"
    git fetch --prune
    setup-repo cleanup clean --merged -y
  fi
done
```

### エイリアス設定

```bash
# ~/.bashrc または ~/.zshrc に追加
alias branch-cleanup='git fetch --prune && setup-repo cleanup clean --merged --dry-run'
alias branch-cleanup-run='git fetch --prune && setup-repo cleanup clean --merged -y'
```

## 🆘 トラブルシューティング

**Q: コマンドが見つからない**

```bash
# uvのツールパスを確認
uv tool list

# パスを追加（必要に応じて）
export PATH="$HOME/.local/bin:$PATH"
```

**Q: 古いバージョンがインストールされている**

```bash
# 再インストール
uv tool uninstall setup-repository
uv tool install git+https://github.com/scottlz0310/Setup-Repository.git
```
