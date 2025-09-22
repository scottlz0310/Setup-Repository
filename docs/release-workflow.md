# 🚀 リリースワークフロー完全ガイド

## 📋 概要

このドキュメントでは、Setup Repositoryプロジェクトの完全自動化リリースワークフローについて詳しく説明します。

## 🎯 リリースフローの特徴

- **完全自動化**: ワンクリックで全工程自動実行
- **2つのトリガー**: 手動実行とタグプッシュ
- **自動補完**: 不足部分の自動生成・修正
- **重複回避**: 既存エントリは保持・日付のみ更新
- **Git履歴ベース**: Conventional Commitsから自動CHANGELOG生成

## 🔄 フローチャート

```mermaid
flowchart TD
    A[開発者] --> B{リリース方法選択}
    
    B -->|手動実行| C[CI画面でバージョン指定]
    B -->|タグプッシュ| D[git tag v1.0.0 && git push origin v1.0.0]
    
    C --> E[workflow_dispatch トリガー]
    D --> F[push tags トリガー]
    
    E --> G[version-check ジョブ]
    F --> G
    
    G --> H[バージョン情報抽出]
    H --> I[バージョン一貫性チェック]
    I --> J[quality-check ジョブ]
    
    J --> K[CI/CDテスト実行]
    K --> L[prepare-release ジョブ]
    
    L --> M{バージョン整合性OK?}
    M -->|No| N[自動修正: pyproject.toml, __init__.py]
    M -->|Yes| O[CHANGELOG自動生成・更新]
    N --> O
    
    O --> P[リリースノート生成]
    P --> Q{変更あり?}
    Q -->|Yes| R[自動コミット・プッシュ]
    Q -->|No| S[create-release ジョブ]
    R --> S
    
    S --> T[パッケージビルド]
    T --> U{手動実行?}
    U -->|Yes| V[タグ作成・プッシュ]
    U -->|No| W[GitHub Release作成]
    V --> W
    
    W --> X[アセット添付]
    X --> Y[post-release ジョブ]
    Y --> Z[リリースメトリクス記録]
    Z --> AA[🎉 リリース完了]
```

## 🚀 手動リリース（推奨）

### 使用方法

1. **GitHub Actions画面**に移動
2. **🚀 Release Management**ワークフローを選択
3. **「Run workflow」**をクリック
4. **パラメータ入力**:
   - `version`: リリースバージョン (例: 1.3.6)
   - `prerelease`: プレリリースフラグ (true/false)
5. **「Run workflow」**で実行

### 処理フロー

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant GH as GitHub Actions
    participant Repo as リポジトリ
    
    Dev->>GH: バージョン指定で実行
    GH->>Repo: バージョン整合性チェック
    
    alt バージョン不整合
        GH->>Repo: 自動修正 (pyproject.toml, __init__.py)
    end
    
    GH->>Repo: Git履歴からCHANGELOG生成
    GH->>Repo: リリースノート生成
    
    alt 変更あり
        GH->>Repo: 自動コミット・プッシュ
    end
    
    GH->>Repo: タグ作成・プッシュ
    GH->>GH: GitHub Release作成
    GH->>Dev: 🎉 リリース完了通知
```

## 🏷️ タグプッシュリリース

### 使用方法

```bash
# ローカルでタグ作成・プッシュ
git tag v1.3.6
git push origin v1.3.6
```

### 処理フロー

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant GH as GitHub Actions
    participant Repo as リポジトリ
    
    Dev->>Repo: git tag v1.3.6 && git push origin v1.3.6
    Repo->>GH: タグプッシュトリガー
    GH->>Repo: バージョン整合性チェック
    
    alt バージョン不整合
        GH->>Repo: 自動修正 (pyproject.toml, __init__.py)
    end
    
    GH->>Repo: Git履歴からCHANGELOG生成
    GH->>Repo: リリースノート生成
    
    alt 変更あり
        GH->>Repo: 自動コミット・プッシュ
    end
    
    Note over GH: タグ作成はスキップ（既存）
    GH->>GH: GitHub Release作成
    GH->>Dev: 🎉 リリース完了通知
```

## 🔧 ジョブ詳細

### 1. version-check ジョブ

**目的**: バージョン情報の抽出と一貫性チェック

**処理内容**:
- トリガー種別の判定（手動 or タグプッシュ）
- バージョン情報の抽出
- プレリリースフラグの判定
- pyproject.tomlと__init__.pyの一貫性チェック

**出力**:
- `version`: 対象バージョン
- `is-prerelease`: プレリリースフラグ

### 2. quality-check ジョブ

**目的**: コード品質とテストの実行

**処理内容**:
- CI/CDワークフロー（ci.yml）の実行
- リンティング、型チェック、テスト実行
- セキュリティスキャン

### 3. prepare-release ジョブ

**目的**: リリース準備と自動補完

**処理内容**:
1. **バージョン整合性チェック・自動修正**
   - pyproject.tomlと__init__.pyの不整合を検出
   - 不整合があれば自動修正
2. **CHANGELOG自動生成・更新**
   - Git履歴からConventional Commitsを解析
   - カテゴリ別に変更内容を分類
   - 既存エントリがあれば日付のみ更新
3. **リリースノート生成**
   - CHANGELOGから該当バージョンを抽出
   - GitHub Release用のマークダウン生成
4. **自動コミット**
   - 変更があれば自動コミット・プッシュ

**出力**:
- `changes-made`: 変更有無フラグ

### 4. create-release ジョブ

**目的**: タグ作成とGitHub Release作成

**処理内容**:
1. **パッケージビルド**
   - Python wheelとtarballの生成
2. **タグ作成（条件付き）**
   - 手動実行時のみタグ作成・プッシュ
   - タグプッシュ時はスキップ
3. **GitHub Release作成**
   - リリースノートを使用
   - アセット添付（dist/, CHANGELOG.md, README.md, LICENSE）

### 5. post-release ジョブ

**目的**: リリース後処理とメトリクス記録

**処理内容**:
- リリースメトリクスの記録
- 成功通知

## 🤖 自動CHANGELOG生成

### Conventional Commits対応

以下のコミット形式を自動認識：

- `feat:` → ✨ 新機能
- `fix:` → 🐛 修正  
- `docs:` → 📝 ドキュメント
- `refactor:` → 🔄 変更
- その他 → 🔧 その他

### 生成例

```markdown
## [1.3.6] - 2025-01-15

### ✨ 新機能
- 完全自動化リリースフロー実装
- Git履歴ベースのCHANGELOG生成

### 🐛 修正
- YAML構文エラー修正
- バージョン整合性チェック改善

### 🔄 変更
- リリースワークフローの最適化
- ドキュメント構造の改善
```

## 🎯 使い分けガイド

### 手動リリース（推奨）

**適用場面**:
- 定期リリース
- 機能リリース
- 緊急修正リリース

**メリット**:
- CI画面で簡単実行
- バージョン指定が明確
- プレリリースフラグ制御可能

### タグプッシュリリース

**適用場面**:
- ローカル開発環境からのリリース
- スクリプト自動化
- 既存ワークフローとの連携

**メリット**:
- コマンドライン完結
- 既存のGitワークフローと統合
- 自動化スクリプトに組み込み可能

## 🔍 トラブルシューティング

### よくある問題

1. **「Run workflow」ボタンが表示されない**
   - YAML構文エラーの可能性
   - mainブランチにプッシュされているか確認

2. **バージョン整合性エラー**
   - 自動修正機能により解決
   - 手動修正が必要な場合はログを確認

3. **CHANGELOG生成が空**
   - Git履歴にConventional Commitsがない
   - フォールバック機能により最小限の内容を生成

4. **タグが重複**
   - 既存タグの確認
   - 手動削除後に再実行

### デバッグ方法

1. **ワークフローログの確認**
   - GitHub Actions画面でログ詳細を確認
   - 各ジョブの実行結果をチェック

2. **ローカルでのテスト**
   ```bash
   # バージョン管理スクリプトのテスト
   uv run python scripts/version-manager.py --check
   uv run python scripts/version-manager.py --update-changelog 1.3.6
   ```

3. **YAML構文チェック**
   ```bash
   # ローカルでYAML構文確認
   uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
   ```

## 📚 関連ドキュメント

- [バージョン管理ガイド](version-management.md)
- [CI/CDパイプライン](ci-cd-pipeline.md)
- [開発者ガイド](../README.md#開発・テスト)
- [品質管理システム](quality-management.md)