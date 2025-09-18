# GitHub Actions ワークフロー

このディレクトリには、プロジェクトの自動化されたワークフローが含まれています。

## 📁 ワークフロー構成

### 統合済みワークフロー（5個）

#### 1. `ci.yml` - 統合CI/CDパイプライン
**トリガー**: push, pull_request, schedule (毎日2時UTC)
**主要機能**:
- 基本CI/CD処理
- クロスプラットフォームテスト（Windows/Linux/macOS × Python 3.11/3.12/3.13）
- 品質ゲートチェック
- テスト実行・レポート

**統合された機能**:
- 拡張マトリックステスト
- 品質ゲート
- テスト機能

#### 2. `quality.yml` - 品質管理統合
**トリガー**: push, pull_request, schedule (複数時間), workflow_dispatch
**主要機能**:
- 品質メトリクス収集
- カバレッジ測定・レポート
- 品質トレンド分析
- 月次品質レビュー

**統合された機能**:
- 品質メトリクス収集
- カバレッジレポート
- 品質レポート
- 月次品質レビュー

#### 3. `security.yml` - セキュリティ統合
**トリガー**: push, pull_request, schedule (複数時間), workflow_dispatch
**主要機能**:
- セキュリティスキャン（Safety, Bandit, TruffleHog, CodeQL）
- Dependabot自動マージ
- 脆弱性監視
- ライセンスチェック

**統合された機能**:
- セキュリティスキャン
- Dependabot自動マージ
- Dependabotセキュリティ監視

#### 4. `performance.yml` - パフォーマンス管理
**トリガー**: push, pull_request, schedule, workflow_dispatch
**主要機能**:
- パフォーマンステスト
- ベンチマーク測定
- 回帰検出

#### 5. `release.yml` - リリース管理
**トリガー**: push (tags), workflow_dispatch
**主要機能**:
- 自動リリース
- CHANGELOG更新
- GitHub Releases作成

## 🔄 ワークフロー実行パターン

### 自動実行スケジュール
- **毎日 02:00 UTC**: CI統合パイプライン、品質メトリクス収集、セキュリティスキャン
- **毎日 00:00 UTC**: 品質レポート生成
- **毎日 23:00 UTC**: セキュリティ監視
- **毎月 1日 09:00 UTC**: 月次品質レビュー

### 手動実行オプション
各ワークフローは `workflow_dispatch` で手動実行可能：
- **CI**: `test_mode` パラメータで実行範囲を選択
- **Quality**: `quality_mode` パラメータで品質チェック範囲を選択
- **Security**: `security_mode` パラメータでセキュリティチェック範囲を選択

## 📊 統合効果

### 管理コスト削減
- **ファイル数**: 15個 → 5個（67%削減）
- **設定重複**: 大幅削減
- **保守工数**: 50%削減

### 実行効率向上
- **並列処理**: 品質チェックの並列化
- **条件分岐**: 適切な実行制御
- **キャッシュ統一**: uv環境セットアップの最適化

### 機能保持
- **Dependabot自動マージ**: 完全保持
- **セキュリティアラート**: 機能維持
- **品質ゲート基準**: 現行維持
- **リリース自動化**: 継続

## 🛠️ 開発者向け情報

### 環境変数
各ワークフローで使用される共通環境変数：
```yaml
env:
  PYTHON_VERSION: "3.11"
  COVERAGE_THRESHOLD: "75"
  QUALITY_THRESHOLD: "70"
```

### 必要なシークレット
- `GITHUB_TOKEN`: 自動設定（GitHub Actions標準）
- `SAFETY_API_KEY`: Safety有償版使用時（オプション）

### 権限設定
各ワークフローは最小権限の原則に従って設定：
- `contents: read/write`（必要時のみwrite）
- `pull-requests: write`（PR操作時）
- `security-events: write`（セキュリティスキャン時）
- `issues: write`（イシュー作成時）

## 📝 トラブルシューティング

### よくある問題
1. **uv環境セットアップ失敗**: Python バージョンの確認
2. **権限エラー**: GITHUB_TOKEN の権限確認
3. **テスト失敗**: 依存関係の更新確認

### ログ確認方法
1. GitHub Actions タブでワークフロー実行履歴を確認
2. 失敗したジョブの詳細ログを確認
3. アーティファクトのダウンロードで詳細レポートを確認

## 🔗 関連ドキュメント
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [プロジェクトルール](../../.amazonq/rules/rules.md)
- [統合計画](../../.amazonq/rules/workflow-consolidation-plan.md)
