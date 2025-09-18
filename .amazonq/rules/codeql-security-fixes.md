# CodeQL セキュリティ修正計画

## 概要
CodeQLスキャンで検出されたセキュリティ問題の修正計画（.venv除外）

## 修正対象問題

### 1. High Priority（高優先度）

#### 1.1 OSコマンドインジェクション（CWE-77,78,88）
**対象ファイル:**
- `src/setup_repo/platform_detector.py:209-210`
- `src/setup_repo/ci_environment.py:133-134`
- `src/setup_repo/safety_check.py:16-22`

**問題:** subprocess呼び出しで部分パス使用
**修正方針:** 絶対パスまたはshutil.which()使用

#### 1.2 不適切な認証チェック
**対象ファイル:** `src/setup_repo/quality_collectors.py:432-464`
**問題:** クライアント制御入力による認証
**修正方針:** サーバーサイド認証に変更

#### 1.3 パストラバーサル（CWE-22）
**対象ファイル:** `src/setup_repo/utils.py:238-239`
**問題:** 未検証ユーザー入力でパス構築
**修正方針:** pathlib.Path.resolve()とstartswith()チェック

#### 1.4 XSS脆弱性（CWE-20,79,80）
**対象ファイル:** `src/setup_repo/quality_errors.py:191-192`
**問題:** 未サニタイズ出力
**修正方針:** html.escape()使用

#### 1.5 汎用例外処理問題（CWE-396,397）
**対象ファイル:**
- `tests/unit/test_utils.py:172-173`
- `tests/unit/test_platform_detector_real.py:237-238`
- `tests/unit/test_utils_coverage.py:138-139`

**問題:** 汎用Exception処理
**修正方針:** 具体的例外型とlogging.exception()使用

#### 1.6 GitHub Actionsスクリプトインジェクション
**対象ファイル:** `.github/workflows/release.yml:63-94`
**問題:** 未検証入力使用
**修正方針:** 環境変数経由での値渡し

### 2. Medium Priority（中優先度）

#### 2.1 循環複雑度
**対象ファイル:** `src/setup_repo/logging_config.py:204-205`
**問題:** 複雑度24
**修正方針:** 関数分割

### 3. Low Priority（低優先度）

#### 3.1 PEP8違反
**対象ファイル:** 複数のテストファイル
**問題:** `len(val) == 0` 使用
**修正方針:** `if not val` に変更

## 修正順序

### Phase 1: セキュリティ修正（即座）
1. OSコマンドインジェクション修正
2. 認証チェック修正
3. パストラバーサル修正
4. XSS脆弱性修正
5. GitHub Actions修正

### Phase 2: 例外処理改善
1. 汎用例外処理を具体的例外に変更
2. ログ出力追加

### Phase 3: コード品質改善
1. 循環複雑度削減
2. PEP8違反修正

## 修正実装方針

### セキュリティ修正
- 入力検証強化
- 安全なAPI使用
- ログ出力でのセキュリティ情報マスキング

### テスト修正
- 実環境重視のテスト維持
- 適切な例外処理
- ログ出力による問題追跡

### CI/CD修正
- セキュアな変数渡し
- 権限最小化
- 入力検証

## 完了基準
- CodeQLスキャン: プロジェクト固有の脆弱性0件
- セキュリティレビュー完了
- テスト全通過
- CI/CD正常動作
