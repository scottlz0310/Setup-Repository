# AI開発標準ルール（要約版）

目的
- AIを含む開発の品質・再現性・セキュリティ・運用性を高水準で維持するための実務指針（毎回のコンテキスト読込向け要約）詳細はプロジェクトルートの[rules.md](./rules.md)rules.mdを参照

適用範囲
- 本リポジトリの全コード/ドキュメント/CI、サブプロジェクトも特段の合意がなければ継承

1. 基本方針（抜粋）
- 言語: 原則日本語。外部公開/OSSは英語併記可（自動切替は禁止）
- 品質: 単一責務・循環依存禁止・公開API最小化・妥協実装禁止・例外設計の明確化
- 倫理/法令: PII最小化とマスキング、ライセンス/利用規約順守

2. リポジトリ構成（標準例：全行コメント付き）
```
project-root/                         # プロジェクトのルート
├── main.py                           # アプリのエントリポイント
├── test_entry.py                     # テスト実行のエントリポイント
├── Makefile                          # ビルド/検査/実行コマンド集
├── pyproject.toml                    # ツール/ビルド/依存の統合設定
├── uv.lock                           # 依存関係ロック（再現性担保）
├── .gitignore                        # Git除外設定
├── README.md                         # 概要/セットアップ/使用方法
├── CHANGELOG.md                      # 変更履歴（Keep a Changelog）
├── LICENSE                           # ライセンス
├── rules_v3.md                       # 詳細ルール（本編）
├── src/                              # 実装コード
├── tests/                            # テストコード（pytest）
├── docs/                             # ドキュメント全般
│   └── adr/                          # 設計判断の記録（ADR）
├── config/                           # 環境別設定（dev/stg/prod）
├── schemas/                          # スキーマ定義（JSON Schema等）
├── playground/                       # 実験/試行コード
├── scripts/                          # 補助スクリプト（CI/運用）
├── tools/                            # 開発ツール/ラッパー
├── assets/                           # 画像/素材/サンプル
├── output/                           # 生成物（Git管理外想定）
├── .cache/                           # キャッシュ（Git管理外想定）
└── .github/                          # GitHub設定一式
    ├── workflows/                    # CI/CDワークフロー
    ├── ISSUE_TEMPLATE/               # Issueテンプレート
    ├── PULL_REQUEST_TEMPLATE.md      # PRテンプレート
    └── CODEOWNERS                    # 所有/必須レビュア設定
```

2.2 必須ドキュメント
- README, CHANGELOG(SemVer整合), LICENSE, rules_v3, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, docs/adr（任意: SUPPORT, GOVERNANCE）

2.3 Git除外規則（重要点）
- プロジェクト/スクリプトが自動生成するファイル・ディレクトリは原則すべて除外する（生成物の誤コミット防止）
- 例: __pycache__/, .venv/, output/, .cache/, .pytest_cache/, .ruff_cache/, .mypy_cache/, *.log, *.tmp, *.bak, .coverage, coverage.xml, htmlcov/, dist/, build/, pip-wheel-metadata, .tox/, .DS_Store, .idea/, .vscode/, .python-version, .env, .env.*

3. 開発環境（uv標準）
- uv.lockは必ずコミット、--systemは開発で禁止（CI/コンテナのみ）
- CIはuv syncで再現性検証必須
- Pythonサポートは最新安定＋直近LTS（例: 3.11/3.12/3.13）をCIマトリクスで検証
- 全ツール設定はpyproject.tomlに統合、Makefileに標準ターゲット（lint/type/test等）

4. コード品質
- ツール: ruff(lint/format)/mypy(pytypes)/pytest(tests)
- ルール: PEP8, Docstring規約, import順序, pyupgrade等
- 型: Any使用は理由明記、段階的にmypy strictへ
- デバッグ: print禁止、構造化JSONログ、lazy logging、レベル適切運用

5. テスト戦略
- pytest/pytest-cov採用、CIでカバレッジ閾値ゲート
- 目標: productionで>=80%
- 段階: prototype(緩和)→staging(強化,60%)→production(strict,80%+)
- 絶対NG: 条件緩和スキップ、ダミー、assert無し
- 再現性: seed固定、時刻はUTC注入、I/O安定化、スナップショットは差分レビュー

6. セキュリティ/品質保証
- GH Advanced Security（CodeQL/Secret scan/Dependabot）、SCAをCIに組込
- SBOM（CycloneDX）とライセンス監査、秘密管理（.envはコミット禁止、CIはOIDC+シークレット）
- Actions permissions最小化、トークン最小権限/短命化、例外は期限/再評価日/承認者を文書化

7. CI/CD
- マトリクス: OS×Python、キャッシュキーにpyproject.toml/uv.lock
- 必須チェック: uv sync再現性、lint、type、test+cov、セキュリティ（CodeQL/SCA/Secret/SBOM）
- デプロイ: 環境保護と承認ゲート、Branch Protection（必須レビュー/force-push禁止/linear history）
- 失敗時通知: Slack/Teams/GitHubで即時通知

8. 開発フロー
- フェーズ: 計画/設計→基盤→統合/検証→品質保証→デプロイ準備→リリース/運用（各Exit Criteriaを明文化）
- ブランチ: trunk-basedまたは簡易Git Flow（feature/fix/chore/release）、ドラフトPR活用、セルフマージ禁止、PRは小さく
- レビュー: CODEOWNERSで責任範囲、設計/実装/品質/セキュリティのレビュー実施

9. コミット/リリース
- Pre-commit: 自動修正は--amend --no-edit、メッセージ固定
- Conventional Commits＋SemVer、重大変更はPR/CHANGELOGで明示
- 署名コミット or DCO推奨、リリースはタグ/Releaseノート自動化、バージョン整合をCI検証

10. ログ/観測性
- 構造化JSONログ、必須フィールド（UTC timestamp/trace_id等）、PIIはマスク
- トレーシング/メトリクス（OpenTelemetry可）
- 日付/時刻ルール（改定済）
  - 原則: ドキュメント上の日時はCI/ビルドで自動埋め込み（UTC/ISO 8601）
  - 手入力が必要な場合: dateコマンド等で現在時刻を確認してから記載すること（UTC/形式統一）
    - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"` / 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`

11. AI特有の規約
- プロンプト設計: テンプレ化、入力検証、秘密持込禁止、インジェクション対策
- 評価/回帰: 正確性/安全性/バイアス/コスト/レイテンシの自動評価と回帰監視
- 実験管理: seed固定、データ/モデル/プロンプトの版管理、モデルカード/リスク評価
- ガードレール: 出力フィルタ、PII検出/マスク、失敗時フォールバック、レート制御
- コスト: トークン/推論コストの可視化と上限・アラート

12. データガバナンス
- 機微度分類（Public/Internal/Confidential/Restricted）と取扱い
- ライセンス/第三者データの条件記録、保持/削除ポリシー（GDPR等考慮）、復旧計画/監査ログ

最小チェックリスト（毎回のPR前に確認）
- uv.lockコミット済 / uv sync再現性OK / CI全緑（lint/type/test+cov/セキュリティ）
- 自動生成物は.gitignoreで除外 / 構造化ログ/UTC/PIIマスクの遵守
- ADR/README/CHANGELOG更新 / Conventional Commits / Branch Protection通過
- AI変更は評価/ガードレール/コスト影響を記録