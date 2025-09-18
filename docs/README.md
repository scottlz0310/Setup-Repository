# 📚 Setup Repository ドキュメント

このディレクトリには、Setup Repositoryプロジェクトの各種ドキュメントが整理されています。

## 📁 ディレクトリ構造

### 📖 メインドキュメント（ルートレベル）

ユーザー・開発者向けの主要ドキュメント：

- **[setup-guide.md](setup-guide.md)** - セットアップガイド（ユーザー向け）
- **[architecture.md](architecture.md)** - システムアーキテクチャ設計書
- **[migration-guide.md](migration-guide.md)** - バージョン移行ガイド
- **[release-management.md](release-management.md)** - リリース管理手順
- **[testing-strategy.md](testing-strategy.md)** - テスト戦略・方針
- **[ci-cd-compliance.md](ci-cd-compliance.md)** - CI/CD準拠ガイド

### 🏗️ ADR（Architecture Decision Records）

設計判断の記録：

- **[adr/001-project-architecture.md](adr/001-project-architecture.md)** - プロジェクトアーキテクチャ決定記録

### 🔒 内部ドキュメント（internal/）

プロジェクト内部のポリシー・例外事項：

- **[internal/multiplatform-test-policy.md](internal/multiplatform-test-policy.md)** - マルチプラットフォームテストポリシー
- **[internal/security-exceptions.md](internal/security-exceptions.md)** - セキュリティ例外事項
- **[internal/rules_summary.md](internal/rules_summary.md)** - 開発ルール要約

### 📦 開発アーカイブ（dev-archive/）

開発過程で作成された作業ドキュメント（参考用）：

#### API・設定関連
- **api-changes.md** - API変更履歴
- **configuration-consistency.md** - 設定一貫性チェック
- **dependency-analysis-results.md** - 依存関係分析結果

#### セキュリティ関連
- **codeql-fixes-2025-01-27.md** - CodeQL修正記録
- **codeql-fixes-summary.md** - CodeQL修正要約
- **codeql-security-fixes.md** - セキュリティ修正記録
- **security-fix-plan.md** - セキュリティ修正計画

#### テスト関連
- **multiplatform-test-integration-progress.md** - マルチプラットフォームテスト統合進捗
- **test-fix-plan.md** - テスト修正計画
- **test-refactoring-plan.md** - テストリファクタリング計画

#### 開発プロセス関連
- **development-checklist.md** - 開発チェックリスト
- **development-prompt.md** - 開発プロンプト
- **phase1-completion-summary.md** - Phase1完了要約
- **phase2-timeout-analysis.md** - Phase2タイムアウト分析
- **refactoring-guidelines.md** - リファクタリングガイドライン
- **technical-debt.md** - 技術債務記録

#### ワークフロー関連
- **workflow_consolidation_plan.md** - ワークフロー統合計画（重複）
- **workflow-consolidation-plan.md** - ワークフロー統合計画
- **workflow-dependency-mapping.md** - ワークフロー依存関係マッピング

#### その他
- **coverage-integration-plan.md** - カバレッジ統合計画

## 📋 ドキュメント利用ガイド

### 🎯 目的別ドキュメント選択

**新規ユーザー**:
1. [setup-guide.md](setup-guide.md) - 基本セットアップ
2. [architecture.md](architecture.md) - システム理解

**開発者**:
1. [architecture.md](architecture.md) - システム設計理解
2. [testing-strategy.md](testing-strategy.md) - テスト方針
3. [adr/](adr/) - 設計判断の背景

**メンテナー**:
1. [release-management.md](release-management.md) - リリース手順
2. [ci-cd-compliance.md](ci-cd-compliance.md) - CI/CD運用
3. [internal/](internal/) - 内部ポリシー

**移行作業**:
1. [migration-guide.md](migration-guide.md) - バージョン移行
2. [dev-archive/](dev-archive/) - 過去の作業記録（参考）

### 🔄 ドキュメント更新ルール

1. **メインドキュメント**: 機能変更時は必ず更新
2. **ADR**: 重要な設計判断時に追加
3. **内部ドキュメント**: ポリシー変更時に更新
4. **開発アーカイブ**: 基本的に更新不要（履歴保持）

### 📝 ドキュメント作成ガイドライン

- **日本語**: プロジェクトルールに従い日本語で記述
- **Markdown**: 標準的なMarkdown記法を使用
- **構造化**: 見出し・リスト・表を適切に使用
- **リンク**: 関連ドキュメント間の相互リンクを設置

## 🔍 検索・参照

特定の情報を探す場合：

1. **機能・使い方** → [setup-guide.md](setup-guide.md)
2. **設計・構造** → [architecture.md](architecture.md)
3. **テスト** → [testing-strategy.md](testing-strategy.md)
4. **リリース** → [release-management.md](release-management.md)
5. **過去の作業** → [dev-archive/](dev-archive/)
6. **内部ルール** → [internal/](internal/)

---

📅 **最終更新**: 2025-01-18
🏷️ **バージョン**: v1.1.0対応
