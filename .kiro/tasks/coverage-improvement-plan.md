# テストカバレッジ向上計画

## 📊 現状分析

### 現在のカバレッジ状況
- **総合カバレッジ**: 66.18%
- **目標カバレッジ**: 80%
- **改善必要**: +13.82%

### モジュール別カバレッジ分析
```
高カバレッジ (80%+): 10個
├── logging_config.py: 100.0%
├── config.py: 97.8%
├── project_detector.py: 95.6%
├── quality_trends.py: 95.5%
├── utils.py: 95.4%
├── quality_logger.py: 90.7%
├── sync.py: 89.1%
├── platform_detector.py: 81.8%
├── gitignore_manager.py: 81.2%
└── quality_metrics.py: 81.0%

中カバレッジ (50-79%): 3個
├── ci_error_handler.py: 78.4%
├── github_api.py: 76.0%
└── setup.py: 76.0%

低カバレッジ (<50%): 7個
├── vscode_setup.py: 42.9%
├── safety_check.py: 27.9%
├── python_env.py: 24.0%
├── uv_installer.py: 24.0%
├── git_operations.py: 22.4%
├── interactive_setup.py: 16.4%
└── cli.py: 13.7%
```

## 🎯 カバレッジ向上戦略

### Phase 4: テストカバレッジ向上（新規追加）

#### Task 4.1: 低カバレッジモジュールの優先改善
**優先度**: 最高
**工数**: 3日
**目標カバレッジ**: 60%以上

**対象モジュール** (現在<50%):
- `cli.py` - 13.7% → 70%
- `interactive_setup.py` - 16.4% → 60%
- `git_operations.py` - 22.4% → 70%
- `python_env.py` - 24.0% → 60%
- `uv_installer.py` - 24.0% → 70%

**テストファイル**:
```
tests/unit/
├── test_cli.py (新規)
├── test_interactive_setup.py (新規)
├── test_git_operations.py (新規)
├── test_python_env.py (新規)
└── test_uv_installer.py (新規)
```

#### Task 4.2: 中カバレッジモジュールの完成
**優先度**: 高
**工数**: 2日
**目標カバレッジ**: 85%以上

**対象モジュール** (現在50-79%):
- `ci_error_handler.py` - 78.4% → 85%
- `github_api.py` - 76.0% → 85%
- `setup.py` - 76.0% → 85%

**テストファイル**:
```
tests/unit/
├── test_ci_error_handler.py (拡張)
├── test_github_api.py (拡張)
└── test_setup.py (拡張)
```

#### Task 4.3: 残り低カバレッジモジュールの改善
**優先度**: 中
**工数**: 2日
**目標カバレッジ**: 60%以上

**対象モジュール**:
- `safety_check.py` - 27.9% → 70%
- `vscode_setup.py` - 42.9% → 70%

**テストファイル**:
```
tests/unit/
├── test_safety_check.py (新規)
└── test_vscode_setup.py (新規)

tests/integration/
└── test_safety_integration.py (新規)
```

#### Task 4.4: 高カバレッジモジュールの最適化
**優先度**: 低
**工数**: 1日
**目標カバレッジ**: 95%以上

**対象モジュール** (80%以上を95%以上に):
- `quality_metrics.py` - 81.0% → 95%
- `gitignore_manager.py` - 81.2% → 95%
- `platform_detector.py` - 81.8% → 95%

**テストファイル**:
```
tests/unit/
├── test_quality_metrics.py (拡張)
├── test_gitignore_manager.py (拡張)
└── test_platform_detector.py (拡張)
```

#### Task 4.5: 統合テストの強化
**優先度**: 中
**工数**: 1.5日
**目標**: エンドツーエンドカバレッジ向上

**対象領域**:
- 完全な同期ワークフロー
- セットアップフロー
- エラーハンドリングフロー

**テストファイル**:
```
tests/integration/
├── test_full_workflow.py (新規)
├── test_error_scenarios.py (新規)
└── test_cross_platform.py (新規)
```

#### Task 4.6: パフォーマンス・エッジケーステスト
**優先度**: 低
**工数**: 1.5日
**目標**: 品質向上とエッジケースカバー

**対象領域**:
- 大量リポジトリ処理
- ネットワークエラー処理
- ファイルシステムエラー

**テストファイル**:
```
tests/performance/
├── test_large_repos.py (新規)
└── test_error_recovery.py (新規)

tests/unit/
└── test_edge_cases.py (新規)
```

## 📅 拡張スケジュール

### Week 4: 低カバレッジ優先改善
- Day 1-3: Task 4.1 (低カバレッジモジュール)
- Day 4-5: Task 4.2 (中カバレッジ完成)

### Week 5: 残りモジュール・最適化
- Day 1-2: Task 4.3 (残り低カバレッジ)
- Day 3: Task 4.4 (高カバレッジ最適化)
- Day 4-5: Task 4.5 (統合テスト強化)

### Week 6: 品質向上・最終調整
- Day 1-2: Task 4.6 (パフォーマンス・エッジケース)
- Day 3-4: カバレッジ最適化
- Day 5: 最終検証

**追加工数**: 11日
**総工数**: 23日 (4週間 → 6週間)

## 🧪 テスト実装戦略

### モックとフィクスチャ戦略
```python
# conftest.py 拡張
@pytest.fixture
def mock_github_api():
    """GitHub API モック"""
    with patch('setup_repo.github_api.GitHubAPI') as mock:
        yield mock

@pytest.fixture  
def mock_git_operations():
    """Git操作モック"""
    with patch('setup_repo.git_operations.GitOperations') as mock:
        yield mock

@pytest.fixture
def temp_repo_structure(temp_dir):
    """テスト用リポジトリ構造"""
    repo_dir = temp_dir / "test-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "README.md").write_text("# Test")
    return repo_dir
```

### パラメータ化テスト活用
```python
@pytest.mark.parametrize("platform,expected", [
    ("windows", "windows"),
    ("linux", "linux"), 
    ("darwin", "macos"),
])
def test_platform_detection(platform, expected):
    """プラットフォーム検出のパラメータ化テスト"""
    pass
```

### 統合テスト強化
```python
@pytest.mark.integration
def test_full_sync_workflow(temp_dir, mock_github_api):
    """完全な同期ワークフローテスト"""
    # エンドツーエンドのテスト
    pass
```

## 📊 カバレッジ目標とマイルストーン

### マイルストーン設定
```
現在: 66.18%
Week 4 終了: 75% (低・中カバレッジ改善完了)
Week 5 終了: 80% (統合テスト・最適化完了)  
Week 6 終了: 85% (品質向上・最終調整完了)
```

### 品質ゲート更新
```toml
# pyproject.toml 更新
[tool.coverage.report]
fail_under = 80  # 25 → 80 に段階的更新

[tool.pytest.ini_options]
addopts = [
    "--cov-fail-under=80",  # 最終目標
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=json:coverage.json",
]
```

## 🔍 継続的カバレッジ監視

### 自動化スクリプト
```bash
# scripts/coverage-monitor.py
def monitor_coverage():
    """カバレッジ監視とアラート"""
    current = get_current_coverage()
    target = get_target_coverage()
    
    if current < target:
        send_alert(f"カバレッジ低下: {current}% < {target}%")
```

### CI/CD統合
```yaml
# .github/workflows/coverage.yml
- name: Coverage Report
  run: |
    uv run pytest --cov=src/setup_repo --cov-report=json
    uv run python scripts/coverage-check.py --min-coverage 80
    
- name: Coverage Badge Update
  run: |
    COVERAGE=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])")
    echo "COVERAGE=$COVERAGE" >> $GITHUB_ENV
```

## ✅ 成功指標

### 定量的指標
- [ ] 総合カバレッジ 80%以上
- [ ] 全モジュール 60%以上
- [ ] 重要モジュール 80%以上
- [ ] テスト実行時間 5分以内

### 定性的指標  
- [ ] テストの保守性向上
- [ ] バグ検出率向上
- [ ] リファクタリング安全性向上
- [ ] 新機能開発速度向上

## 🎯 最終目標

**7週間後の達成状態**:
- ✅ 責任分離の完全実装
- ✅ テストカバレッジ80%達成
- ✅ 品質ゲート強化
- ✅ 継続的品質監視体制確立