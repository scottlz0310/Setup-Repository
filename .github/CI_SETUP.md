# CI/CD セットアップガイド

このドキュメントでは、Setup-RepositoryプロジェクトのGitHub Actions CI/CDパイプラインの設定と使用方法について説明します。

## ワークフロー概要

### 1. メインCI/CDパイプライン (`ci.yml`)

- **トリガー**: プッシュ、プルリクエスト、手動実行
- **Python バージョン**: 3.9, 3.10, 3.11, 3.12, 3.13
- **実行内容**:
  - Ruffによるリンティングとフォーマットチェック
  - MyPyによる型チェック
  - Pytestによるテスト実行とカバレッジ測定
  - クロスプラットフォームテスト
  - セキュリティスキャン
  - パッケージビルド

### 2. 拡張マトリックステスト (`ci-matrix.yml`)

- **トリガー**: 毎日午前2時（UTC）、手動実行
- **対象OS**: Ubuntu 20.04/22.04, Windows 2019/2022, macOS 12/13
- **目的**: より包括的な環境でのテスト実行

### 3. テストレポート (`test-report.yml`)

- **トリガー**: CI/CDパイプライン完了後
- **機能**: テスト結果の集約とPRへのコメント投稿

## 必要な設定

### GitHub Secrets

以下のシークレットを設定してください：

```
CODECOV_TOKEN          # Codecovアップロード用（オプション）
```

### GitHub Variables

以下の変数を設定できます：

```
PYTHON_DEFAULT_VERSION # デフォルトPythonバージョン（デフォルト: 3.11）
MIN_COVERAGE_THRESHOLD # 最低カバレッジ閾値（デフォルト: 80）
```

## ローカルでのCI環境再現

### 1. 基本的な品質チェック

```bash
# 依存関係インストール
uv sync --dev

# リンティング
uv run ruff check .
uv run ruff format --check .

# 型チェック
uv run mypy src/

# テスト実行
uv run pytest tests/ --cov=src/setup_repo --cov-fail-under=80
```

### 2. 複数Pythonバージョンでのテスト

```bash
# Python 3.9でのテスト
uv venv --python 3.9
uv sync --dev
uv run pytest tests/

# Python 3.13でのテスト
uv venv --python 3.13
uv sync --dev
uv run pytest tests/
```

### 3. パッケージビルドテスト

```bash
# パッケージビルド
uv build

# ビルド成果物の確認
ls -la dist/
```

## CI/CDパイプラインの最適化

### キャッシュ戦略

- **UV依存関係**: `~/.cache/uv`と`.venv`をキャッシュ
- **キャッシュキー**: OS、Pythonバージョン、`uv.lock`のハッシュ値
- **復元キー**: 段階的なフォールバック

### 並列実行

- **マトリックス戦略**: 複数のPythonバージョンとOSで並列実行
- **fail-fast**: `false`に設定して全ての組み合わせをテスト
- **max-parallel**: リソース使用量を制御

### アーティファクト管理

- **テスト結果**: JUnit XML形式で保存
- **カバレッジレポート**: XML、HTML形式で保存
- **ビルド成果物**: wheel、tarballを保存
- **保存期間**: 30日間（GitHub標準）

## トラブルシューティング

### よくある問題

1. **UV インストール失敗**
   ```bash
   # 解決方法: 最新バージョンを使用
   uses: astral-sh/setup-uv@v3
   ```

2. **依存関係解決エラー**
   ```bash
   # 解決方法: ロックファイルを更新
   uv lock --upgrade
   ```

3. **テストタイムアウト**
   ```bash
   # 解決方法: タイムアウト設定を追加
   timeout-minutes: 30
   ```

### デバッグ方法

1. **詳細ログの有効化**
   ```yaml
   - name: Enable debug logging
     run: echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV
   ```

2. **SSH デバッグセッション**
   ```yaml
   - name: Setup tmate session
     uses: mxschmitt/action-tmate@v3
     if: failure()
   ```

## パフォーマンス監視

### メトリクス

- **ビルド時間**: 各ジョブの実行時間を監視
- **テスト実行時間**: テストスイートの実行時間
- **キャッシュヒット率**: 依存関係キャッシュの効率性

### 最適化のヒント

1. **依存関係の最小化**: 必要最小限の依存関係のみインストール
2. **テストの並列化**: `pytest-xdist`を使用した並列テスト実行
3. **キャッシュの活用**: 適切なキャッシュ戦略でビルド時間短縮

## セキュリティ考慮事項

### 権限管理

- **GITHUB_TOKEN**: 読み取り専用権限を使用
- **シークレット**: 必要最小限のシークレットのみ設定
- **フォーク**: フォークからのPRでは制限された権限

### 脆弱性スキャン

- **Safety**: Python依存関係の脆弱性チェック
- **CodeQL**: コード品質とセキュリティ分析（将来実装予定）
- **Dependabot**: 依存関係の自動更新（将来実装予定）

## 今後の拡張予定

1. **セキュリティスキャンの強化**
2. **Dependabotの統合**
3. **自動リリース管理**
4. **パフォーマンステストの追加**
5. **コード品質メトリクスの可視化**
