# テストリファクタリング計画書

## 概要

現在のテストスイートには大量の「環境偽装モック」が使用されており、プロジェクトルールに違反している。
本計画書では、ルールに準拠した実環境重視のテストへの段階的移行を定義する。

## ルール違反の現状

### 違反内容
- プラットフォーム検出のモック使用
- 環境変数の偽装（`@patch.dict(os.environ)`）
- システム情報の偽装（`@patch("platform.system")`）
- プラットフォーム固有モジュールの可用性偽装

### 該当ファイル
1. `tests/unit/test_platform_detector_comprehensive.py` - 重度違反（大量のモック）
2. `tests/unit/test_platform_detector_edge_cases.py` - 重度違反（環境偽装）
3. `tests/unit/test_platform_integration.py` - 軽度違反（一部モック）
4. `tests/multiplatform/test_platform_detection.py` - 軽度違反（一部モック）
5. `tests/conftest.py` - `mock_platform_detector`フィクスチャ（削除済み）

## 依存関係分析

### テスト間依存関係
1. **フィクスチャ依存**:
   - `mock_platform_detector` → 統合テスト、単体テスト（削除済み）
   - `mock_github_api` → セットアップテスト（外部依存、維持）
   - `temp_dir` → ファイルシステムテスト（実環境、維持）

2. **モジュール間依存**:
   - `platform_detector` → `setup`, `interactive_setup`, `vscode_setup`
   - `config` → `setup`, `sync`
   - `utils` → 全モジュール

3. **CI/CD依存**:
   - プラットフォーム検出テスト → マトリクステスト
   - 統合テスト → プラットフォーム固有テスト
   - カバレッジ計算 → 全テストファイル

### 影響範囲マップ
```
mock_platform_detector 削除
├── test_setup_integration.py ✅ 修正済み
├── test_platform_integration.py ⚠️ 要修正
├── test_interactive_setup.py ⚠️ 要確認
└── test_vscode_setup.py ⚠️ 要確認

platform.system() モック削除
├── test_platform_detector_*.py ⚠️ 要修正
├── test_cross_platform.py ⚠️ 要確認
└── CI マトリクステスト ⚠️ 要調整
```

## 修正方針

### 基本原則
1. **実環境優先**: プラットフォーム依存のテストは実環境で実行
2. **適切なスキップ**: 実環境に合わないテストは`pytest.skip`で除外
3. **外部依存のみモック**: GitHub API、ネットワーク等の外部サービスのみモック使用
4. **破壊的変更の回避**: エッジケース再現が必要な場合のみ限定的モック使用
5. **依存関係保持**: テスト間の必要な依存関係は維持

### 段階的修正計画

## Phase 1: 重度違反ファイルの修正

### 1.1 test_platform_detector_comprehensive.py
**現状**: 50+ `@patch`デコレータで環境を偽装
**修正内容**:
- 環境偽装モックをすべて削除
- プラットフォーム固有テストを実環境でのみ実行
- `@pytest.mark.skipif`でプラットフォーム別スキップ実装

**修正例**:
```python
# 修正前（ルール違反）
@patch("platform.system")
def test_detect_platform_windows(self, mock_system):
    mock_system.return_value = "Windows"
    # テスト実装

# 修正後（ルール準拠）
@pytest.mark.skipif(platform.system() != "Windows", reason="Windows環境でのみ実行")
def test_detect_platform_windows(self):
    # 実環境でのテスト実装
```

### 1.2 test_platform_detector_edge_cases.py
**現状**: 環境変数とシステム情報を大量に偽装
**修正内容**:
- 環境変数偽装を削除
- エッジケースは実環境で再現可能なもののみテスト
- 再現不可能なケースは削除またはスキップ

## Phase 2: 軽度違反ファイルの修正

### 2.1 test_platform_integration.py
**現状**: 一部で環境偽装を使用
**修正内容**:
- 環境偽装モックを削除
- 外部依存（subprocess等）のみモック使用
- プラットフォーム検出は実環境で実行

### 2.2 test_platform_detection.py
**現状**: CI環境での一部モック使用
**修正内容**:
- CI環境変数の偽装を削除
- 実際のCI環境でのみテスト実行

## Phase 3: テスト構造の最適化

### 3.1 プラットフォーム別テスト分離
```
tests/
├── unit/
│   ├── test_platform_detector_real.py      # 実環境のみ
│   └── test_platform_detector_external.py  # 外部依存モック
├── multiplatform/
│   ├── test_windows_only.py               # Windows専用
│   ├── test_linux_only.py                 # Linux専用
│   └── test_macos_only.py                 # macOS専用
```

### 3.2 スキップ条件の統一
```python
# 共通スキップ条件
skip_on_windows = pytest.mark.skipif(platform.system() == "Windows", reason="Windows環境では実行しない")
skip_on_unix = pytest.mark.skipif(platform.system() != "Windows", reason="Unix系環境では実行しない")
skip_on_macos = pytest.mark.skipif(platform.system() == "Darwin", reason="macOS環境では実行しない")
```

## Phase 4: CI/CD最適化

### 4.1 マトリクステスト強化
- Windows/Linux/macOS × Python 3.11/3.12/3.13
- プラットフォーム固有テストの並列実行
- 実環境テスト結果の統合

### 4.2 テストカバレッジ調整
- 環境偽装モック削除によるカバレッジ低下への対応
- 実環境テストでの実質的カバレッジ向上
- プラットフォーム別カバレッジレポート

## 実装スケジュール

### Phase 0: 依存関係分析（1-2日）
- [ ] 全テストファイルの依存関係マッピング
- [ ] フィクスチャ使用状況の調査
- [ ] CI/CDへの影響評価
- [ ] 修正優先順位の決定

### Week 1: Phase 1 - 重度違反修正
- [ ] 依存関係分析結果の確認
- [ ] test_platform_detector_comprehensive.py 完全リファクタリング
- [ ] test_platform_detector_edge_cases.py 大幅簡素化
- [ ] 依存テストの整合性確認
- [ ] CI/CDでの動作確認

### Week 2: Phase 2 - 軽度違反修正
- [ ] test_platform_integration.py 修正
- [ ] test_platform_detection.py 修正
- [ ] 統合テスト実行確認

### Week 3: Phase 3 - 構造最適化
- [ ] プラットフォーム別テスト分離
- [ ] スキップ条件統一
- [ ] テストスイート再編成

### Week 4: Phase 4 - CI/CD最適化
- [ ] マトリクステスト強化
- [ ] カバレッジ調整
- [ ] 最終動作確認

## 品質保証

### 修正前後の検証項目
1. **機能性**: 実環境でのプラットフォーム検出が正常動作
2. **カバレッジ**: 実質的なテストカバレッジの維持
3. **CI/CD**: 全プラットフォームでのテスト成功
4. **保守性**: テストコードの可読性・保守性向上
5. **依存関係整合性**: テスト間依存の破綻がないこと
6. **フィクスチャ一貫性**: 必要なフィクスチャが正常動作すること

### 依存関係検証チェックリスト
- [ ] `mock_github_api`フィクスチャ使用テストの動作確認
- [ ] `temp_dir`フィクスチャ使用テストの動作確認
- [ ] 統合テストと単体テストの連携確認
- [ ] CI/CDマトリクステストの整合性確認
- [ ] カバレッジレポートの統合性確認

### リスク管理
- **カバレッジ低下**: 実環境テストでの補完
- **テスト実行時間増加**: 並列実行とスキップ最適化
- **プラットフォーム依存バグ**: 実環境テストでの早期発見
- **依存関係破綻**: 段階的修正と各ステップでの検証
- **フィクスチャ不整合**: 事前分析と段階的移行
- **CI/CDパイプライン停止**: バックアップブランチでの並行作業

### 緊急時対応計画
1. **ロールバック戦略**: 各Phaseでのコミットポイント保存
2. **部分的復旧**: 特定ファイルのみ元に戻す手順
3. **代替テスト**: 一時的なスキップでCI/CD維持

## 完了基準

1. ✅ 環境偽装モックの完全削除
2. ✅ 全プラットフォームでのCI/CD成功
3. ✅ テストカバレッジ75%以上維持
4. ✅ ルール準拠の確認
5. ✅ ドキュメント更新完了

## 参考資料

- [プロジェクトルール](../rules_v3.md#57-mock戦略)
- [テスト戦略](../rules_v3.md#5-テスト戦略)
- [CI/CD要件](../rules_v3.md#7-cicd-要件)
