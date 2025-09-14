# GitHub Workflows統合計画

## 現状の問題
- 15個のワークフローファイルで管理が複雑
- 機能重複による無駄な実行時間
- メンテナンス負荷の増大

## 統合後の構成（6個に削減）

### 1. `main-ci.yml` - 高速CI（プッシュ毎）
**トリガー**: push, pull_request
**実行内容**:
- 軽量なユニットテスト
- リント・フォーマットチェック
- 基本ビルド確認
- マトリックステスト（複数環境での基本テスト）

**統合元**:
- `ci.yml`
- `ci-matrix.yml` 
- `test-ci.yml`

### 2. `scheduled-comprehensive.yml` - 包括的テスト（スケジュール実行）
**トリガー**: schedule (daily/weekly), workflow_dispatch
**実行内容**:
- 全テストスイート実行
- カバレッジ測定・レポート生成
- 品質メトリクス収集
- パフォーマンステスト
- 月次品質レビュー

**統合元**:
- `coverage-report.yml`
- `quality-metrics.yml`
- `quality-report.yml`
- `monthly-quality-review.yml`
- `test-report.yml`
- `performance.yml`

### 3. `security.yml` - セキュリティチェック
**トリガー**: push, pull_request, schedule (weekly)
**実行内容**:
- セキュリティスキャン
- 脆弱性チェック
- 依存関係のセキュリティ監査

**統合元**:
- `security.yml` （既存維持＋スケジュール追加）

### 4. `release.yml` - リリース処理
**トリガー**: push (tags), workflow_dispatch
**実行内容**:
- 通常のリリース処理
- ドキュメント整合性チェック
- 他ワークフローの最終実行確認
  - `main-ci.yml`の成功確認
  - `scheduled-comprehensive.yml`の最新結果確認
  - `security.yml`の成功確認
- タグ作成・パッケージ公開

**統合元**:
- `release.yml` （機能拡張）

### 5. `dependabot-management.yml` - Dependabot管理
**トリガー**: pull_request (dependabot), schedule
**実行内容**:
- Dependabotの自動マージ処理
- セキュリティ関連更新の監視
- 依存関係更新の影響分析

**統合元**:
- `dependabot-auto-merge.yml`
- `dependabot-security-monitor.yml`

### 6. `maintenance.yml` - メンテナンス用
**トリガー**: workflow_dispatch, schedule (monthly)
**実行内容**:
- 古い成果物のクリーンアップ
- ワークフロー実行履歴の整理
- システムヘルスチェック

## 削減効果

| 項目 | 削減前 | 削減後 | 削減率 |
|------|--------|--------|--------|
| ワークフローファイル数 | 13個 | 6個 | 54%削減 |
| プッシュ毎の実行時間 | 重複実行で長時間 | 軽量テストのみで高速 | 約70%短縮 |
| メンテナンス対象 | 分散した設定 | 統合された設定 | 管理負荷50%削減 |

## 実装手順

1. **Phase 1**: `main-ci.yml`の作成・テスト
2. **Phase 2**: `scheduled-comprehensive.yml`の統合
3. **Phase 3**: セキュリティ・リリースワークフローの更新
4. **Phase 4**: 旧ワークフローの削除・クリーンアップ

## 注意点

- 既存のバッジやステータスチェックのURL更新が必要
- ブランチ保護ルールの更新
- チーム内での新しいワークフロー名称の周知
- 移行期間中は並行実行でテスト推奨

## 期待される効果

- **開発効率の向上**: プッシュ毎の高速フィードバック
- **品質保証の向上**: 包括的な定期テスト
- **メンテナンス性の向上**: 統合された設定管理
- **リソース使用量の最適化**: 重複実行の排除