# 🤝 コントリビューションガイド

このプロジェクトへの貢献を歓迎します！

## 🚀 開発環境のセットアップ

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/scottlz0310/Setup-Repository.git
   cd Setup-Repository
   ```

2. **開発環境をセットアップ**
   ```bash
   python first-setup.py
   ```

3. **開発用依存関係をインストール**
   ```bash
   pip install -e ".[dev]"
   ```

## 📝 コーディング規約

- **Python**: PEP 8準拠
- **フォーマット**: Black使用
- **型ヒント**: 必須
- **コメント**: 日本語推奨

## 🧪 テスト

```bash
# テスト実行
pytest

# コードフォーマットとリント
ruff format
ruff check

# 型チェック
mypy repo-sync.py
```

## 📋 プルリクエスト

1. フィーチャーブランチを作成
2. 変更を実装
3. テストを追加/更新
4. プルリクエストを作成

## 🐛 バグレポート

GitHubのIssuesでバグを報告してください。以下の情報を含めてください：

- OS/プラットフォーム
- Pythonバージョン
- エラーメッセージ
- 再現手順