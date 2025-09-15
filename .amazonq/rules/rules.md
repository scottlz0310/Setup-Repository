# AI開発標準ルール(rules.md)

本ドキュメントは、AI機能を含むソフトウェアの開発・運用における品質、再現性、セキュリティ、持続可能性を高水準で維持するための標準ルールを定義する。全メンバー（人/AI）は本ルールを準拠とする。

適用範囲:
- 本リポジトリ内の全コード、ドキュメント、ワークフロー
- サブプロジェクト/ツールに対しても、特段の合意がない限り本ルールを継承

用語:
- 本書で「AI」とは生成AI/補完AI/自動化エージェントを含む
- 「CI/CD」は GitHub Actions 等の自動パイプラインを指す


## 1. 基本方針

### 1.1 言語・コミュニケーション
- 標準言語は日本語。コードコメント・ドキュメント・PR/Issue も日本語で記述する。
- 英語への自動切替は禁止。ただし対外コミュニケーション（OSS への投稿、外部バグ報告、公開ドキュメント）は英語併記可。
- 可能であれば Issue/PR テンプレートは日英併記を推奨。

### 1.2 品質原則
- 単一責務（Single Responsibility）の徹底。循環依存は原則禁止。
- 公開 API は最小化。内部実装の漏洩を避ける。
- 妥協案の提案や手抜き実装は禁止。エラーは根本解決する。
- 例外設計原則: ドメイン例外を定義し、再試行/中断の基準を明示。ユーザ提示メッセージと開発者向け詳細は分離。

### 1.3 倫理・法令遵守
- PII/機微情報の扱いに注意し、収集・保存・出力は最小化。必要に応じて匿名化・マスキングを強制。
- ライセンス/利用規約の遵守。第三者モデル・データの利用条件を明記。


## 2. リポジトリ構成

### 2.1 ディレクトリ構造（標準例：全行に説明コメント付き）
```
project-root/                         # プロジェクトのルートディレクトリ
├── main.py                           # アプリケーションのエントリポイント
├── test_entry.py                     # テスト実行のエントリポイント（統合/回帰の起点）
├── Makefile                          # ビルド・実行・検査を統一するコマンド群
├── pyproject.toml                    # ツール/ビルド/依存設定の統合ファイル
├── uv.lock                           # 依存関係のロックファイル（再現性担保）
├── .gitignore                        # Git 追跡から除外するパス定義
├── README.md                         # プロジェクト概要・セットアップ・使用方法
├── CHANGELOG.md                      # 変更履歴（Keep a Changelog 準拠）
├── LICENSE                           # ライセンス情報
├── rules_v3.md                       # 本ルールドキュメント
├── src/                              # 実装コード（パッケージ/モジュール群）
├── tests/                            # テストコード（pytest、test_*.py）
├── docs/                             # ドキュメント（設計/仕様/運用）
│   └── adr/                          # Architecture Decision Record（設計判断の記録）
├── config/                           # 環境別設定（例: dev/stg/prod の設定ファイル）
├── schemas/                          # スキーマ定義（JSON Schema 等）
├── playground/                       # 実験/サンプルコード/プロトタイピング
├── scripts/                          # 補助スクリプト（CI 補助/メンテナンス等）
├── tools/                            # 開発用ツール/ラッパー/生成物テンプレート
├── assets/                           # 画像/アイコン/サンプルデータなどの素材
├── output/                           # 実行時/ビルド時の生成物（Git 管理対象外）
├── .cache/                           # キャッシュ格納（Git 管理対象外）
└── .github/                          # GitHub 設定（ワークフロー/テンプレート/所有者）
    ├── workflows/                    # CI/CD ワークフロー定義（GitHub Actions）
    ├── ISSUE_TEMPLATE/               # Issue テンプレート（バグ/機能/質問など）
    ├── PULL_REQUEST_TEMPLATE.md      # PR テンプレート（チェックリスト/説明枠）
    └── CODEOWNERS                    # レビュー/所有範囲の定義（必須レビュア設定）
```

### 2.2 必須ドキュメント（常に最新）
- README.md：概要・セットアップ・使用方法
- CHANGELOG.md：Keep a Changelog 準拠、SemVer に整合
- LICENSE
- rules_v3.md（本書）
- CONTRIBUTING.md：貢献手順、PR チェックリスト
- CODE_OF_CONDUCT.md
- SECURITY.md：脆弱性報告窓口、SLA、公開方針
- SUPPORT.md（任意）：サポート範囲・連絡先
- GOVERNANCE.md（任意）：意思決定・役割
- docs/adr/：設計意思決定の記録

### 2.3 Git 除外規則（抜粋）
- 上記以外にも、プロジェクトやスクリプトが自動生成するファイル/ディレクトリはすべて除外対象とする（生成物の誤コミット防止）。
必ず除外:
- __pycache__/, .venv/, output/, .cache/, .pytest_cache/, .ruff_cache/, .mypy_cache/
- *.log, *.tmp, *.bak, .coverage, coverage.xml, htmlcov/
- dist/, build/, pip-wheel-metadata, .tox/
- .DS_Store, .idea/, .vscode/, .python-version
- .env, .env.*（秘密情報はコミット禁止）
- 除外漏れは CI で検出・警告する。


## 3. 開発環境

### 3.1 仮想環境・依存管理（uv 必須）
基本方針: uv を標準ツールとする。ロックファイル（uv.lock）は必ずコミット。

推奨セットアップ:
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
# 代替（CI等）
pip install uv
```

基本ワークフロー:
```bash
uv venv --python 3.13        # .venv に作成
uv lock                      # ロック生成
uv sync                      # 環境同期
uv add requests              # 依存追加
uv run python -m pytest      # 仮想環境で実行
```

制約:
- --system は開発環境で禁止（CI/コンテナのみ許可）
- CI では uv sync による再現性検証必須

### 3.2 Python バージョンポリシー
- サポート: 直近 LTS と最新安定版（例: 3.11/3.12/3.13）を CI マトリクスで検証。
- EOL 到来前にマイグレーション計画を作成。
- pyproject.toml の requires-python を最新方針に整合。

### 3.3 設定管理
- 全ツール設定は pyproject.toml に統合（ruff, mypy, pytest, coverage 等）。
- requirements.txt は互換性維持のため自動同期生成可。setup.py 等の旧式構成は禁止。

### 3.4 Makefile と DX（開発者体験）
標準ターゲット例:
- bootstrap, lint, format, typecheck, test, cov, security, build, release, clean
- ローカル最小ループ: make lint && make typecheck && make test

### 3.5 OS 差異・ローカル設定
- 改行コード/パス/ロケール差異に配慮。テキストは LF 統一。
- ファイル監視/通知機構の差異に注意（特に Windows）。


## 4. コード品質

### 4.1 リンター・フォーマッター・型
標準ツール:
- ruff（lint/format）, mypy（型）, pytest（テスト）

基本コマンド:
```bash
ruff check .
ruff format .
mypy .
pytest -q
```

補足:
- ruff を一次フォーマッタとし、black は必要時のみ。二重整形の衝突は回避。
- import 順序は ruff の import-order ルールに準拠。
- pyupgrade/UP 系、B, C90x, I, T20x（print 検出）を適用推奨。

### 4.2 スタイルガイド
- PEP 8 準拠。行長: コード 88 文字、コメント/Docstring 72 文字。
- PEP 257（Docstring）、NumPy もしくは Google スタイルをプロジェクトで統一。
- 公開関数/クラス/モジュールには Docstring を必須。

### 4.3 型ヒント
- PEP 484 準拠。Any 使用時は PR で理由を明記。
- 段階的厳格化: prototype では緩和、staging で強化、production で mypy strict 相当へ。
  - 推奨フラグ例: disallow-any-generics, no-implicit-optional, warn-redundant-casts 等。

### 4.4 セキュリティ静的解析
- 開発中スキャン: Amazon Q Developer セキュリティースキャン 等
- 補助: bandit 等のセキュリティ linter を導入可。

### 4.5 デバッグ・ログ
- print 使用は禁止。logging を使用。ruff T20x で検出。
- 構造化ログ（JSON）を標準とする。lazy logging を徹底。
- ログレベルの運用: DEBUG/INFO/WARNING/ERROR を適切に使用。


## 5. テスト戦略

### 5.1 構成
- フレームワーク: pytest
- 配置: tests/ ディレクトリ配下、ファイル名は test_*.py
- pytest-cov によるカバレッジ測定を CI ゲート化（行/分岐）

### 5.2 カバレッジ目標
- 最終目標: 80%以上（production）
- CI で閾値を設定し、未達はブロック

### 5.3 段階別方針
```
prototype:
  - 単体テスト中心、mypy 緩和、カバレッジ目標なし
staging:
  - 統合テスト追加、mypy 厳格化、カバレッジ60%
production:
  - E2E/パフォーマンス、mypy strict、カバレッジ80%以上必須
```

### 5.4 絶対ルール
禁止:
- 条件緩和/簡素化/回避目的のスキップ
- カバレッジ稼ぎのダミーテスト
- assert 不在/常 True
- 無意味な __str__/__repr__ 呼び出し
必須:
- 実際のバグ検出能力のあるテスト
- エラーは根本解決まで継続
- 有意な検証を含むこと

### 5.5 テストデータと再現性
- 疑似乱数の seed 固定。時刻依存は固定注入（UTC）。
- タイムゾーンは常に UTC。I/O は安定化（並び順・ロケール固定）。
- スナップショット/ゴールデンファイルは差分レビュープロセスを定義。

### 5.6 契約/統合/E2E/パフォーマンス
- 外部 API は契約テストまたは信頼できるスタブで検証。
- DB/メッセージブローカーは実体/軽量代替で統合テスト。
- ベンチマークの基準値を設定し、回帰を検出。自動リトライは原則禁止。

### 5.7 Moc戦略
- 各プラットフォーム(Winodws,Linux,macOS)依存のテストは実環境を優先して、Mocによる代替は行わない。
- 実環境に合わないテストはSKIP処理を用いて適切に除外する。
- Mocの使用は最小限とするが、以下のケースでは適切にMocを使用する。
 - 外部依存に関係する部分
 - 破壊的変更が起こるケース
 - 非決定的挙動を含む処理
 - エッジケースの再現が必要な場合

## 6. セキュリティ・品質保証

### 6.1 継続的セキュリティチェック
- GitHub Advanced Security（CodeQL, Secret scanning, Dependabot）を有効化。
- SCA（Software Composition Analysis）を CI に組込。

### 6.2 依存監査・SBOM・ライセンス
- SBOM 生成（CycloneDX 等）を定期的に実施。
- ライセンス監査: 許容/禁止ライセンス一覧を維持。例：GPLv3 の扱いは事前合意必須。

### 6.3 秘密情報管理
- ローカル: .env（コミット禁止）。CI: OIDC＋リポジトリ/環境シークレット。
- ログ/CI 出力のシークレットマスキングを強制。

### 6.4 権限最小化
- GitHub Actions の permissions を最小化（read 標準、必要時 write を限定）。
- トークン権限の最小化・短命化。

### 6.5 コンテナセキュリティ（該当時）
- ベースイメージの定期更新。Trivy 等でスキャン。
- ルートレス/最小権限実行、不要パッケージ削減。

### 6.6 セキュリティ例外の承認
- 例外は期限・迂回策・再評価日を文書化し、承認者を明記。


## 7. CI/CD 要件

### 7.1 マトリクス・キャッシュ
- OS × Python バージョンのマトリクス（Windows/Linux/macOS × 3.11/3.12/3.13 目安）
- キャッシュキーは pyproject.toml と uv.lock を含める。

### 7.2 必須チェック
- 依存再現性（uv sync）
- lint（ruff）、type（mypy）、test+cov>=閾値
- セキュリティスキャン（CodeQL/SCA/Secret scan/SBOM）
- 秘密情報検出

### 7.3 デプロイ・環境保護
- 環境別に承認ゲートを設定（stg→prod）。
- Branch Protection: 必須チェック、force-push 禁止、linear history、必須レビュー人数を設定。

### 7.4 失敗時通知
- Slack/Teams/GitHub 通知を自動化。MTTA/MTTR の短縮を図る。


## 8. 開発フロー

### 8.1 段階的実装フェーズと Exit Criteria
- Phase 1: 計画/設計（要件、アーキテクチャ、DB/API、実装計画を .amazonq/rules/ または .kiro/steering/ に配置）
  - 完了条件: 設計レビュー承認、ADR 更新
- Phase 2: 基盤実装（計画に基づく実装、単体テスト、継続セキュリティ、README 整備）
  - 完了条件: 基本機能動作、実装レビュー、CI 全緑
- Phase 3: 統合/検証（全機能確認、UX 改善、責務分離リファクタ）
  - 完了条件: 全機能確認、品質レビュー、ドキュメント更新完了
- Phase 4: 品質保証（包括的セキュリティ、テストスイート、CI/CD 構築、cov>=80%）
  - 完了条件: セキュリティレビュー完了、未解決脆弱性 0
- Phase 5: デプロイ準備（pre-commit、環境構築、設定管理、マイグレーション計画）
  - 完了条件: デプロイ承認、環境保護設定完了
- Phase 6: リリース/運用（Actions 最終検証、段階デプロイ、監視/メトリクス、インシデント対応）
  - 完了条件: 安定運用開始、Runbook 整備

### 8.2 ブランチ戦略
- trunk-based もしくは簡易 Git Flow。命名: feature/, fix/, chore/, release/
- ドラフト PR を活用。セルフマージ禁止。PR は ~300 行目安で小さく保つ。

### 8.3 レビュー体制/CODEOWNERS
- CODEOWNERS で責任範囲を明確化。必須レビュア数を設定。
- 設計/実装/品質/セキュリティレビューを各フェーズ終盤に実施。

### 8.4 エラーハンドリング原則
- 問題発生時は前段階へ戻って根本原因を解決。重大設計変更は Phase 1 から再開。
- 変更は全てドキュメントへ反映し、承認を得る。


## 9. コミット・リリース管理

### 9.1 Pre-commit 規約
- 自動修正時は git commit --amend --no-edit を使用し、元メッセージは変更しない。
- 自動修正のみ: "fix: pre-commit による自動修正"

### 9.2 コミット規約・バージョニング
- Conventional Commits（feat, fix, docs, refactor, test, chore, perf, build, ci）
- SemVer 準拠。重大変更は PR/CHANGELOG で明示。

### 9.3 署名・DCO
- 署名コミット（GPG/SSH）または DCO の採用を推奨。プロジェクトで統一。

### 9.4 リリース
- タグ付与・GitHub Release の自動ノート生成。pre-release の扱いを定義。
- バージョン整合（pyproject.toml / CHANGELOG / タグ）を CI で検証。


## 10. ログ・観測性

### 10.1 構造化ログ
- JSON を標準。必須フィールド: timestamp（UTC, ISO8601）, level, event, message, logger, module, trace_id, span_id, user_id（あれば）、request_id
- PII はマスキング/匿名化。Plain な PII 出力は禁止。

### 10.2 トレーシング/メトリクス
- OpenTelemetry を採用可。相関 ID（trace_id/request_id）を各層で伝搬。

### 10.3 時刻・日付記録規則
- 全ログは timezone-aware UTC を使用する。
- ドキュメント上の日時は原則 CI/ビルド時に自動埋め込みする。
- やむを得ず手入力で日時を記載する場合は、date コマンド等で実際の現在時刻を確認してから記載すること（UTC/ISO 8601 など形式を統一）。
  - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"`
  - 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`


## 11. AI 特有の規約

### 11.1 プロンプト設計
- テンプレート化と入力検証。秘密情報の持込み禁止。プロンプトインジェクション対策を実施。
- 依存データ（コンテキスト/ナレッジ）は出所と版を明記。

### 11.2 評価・回帰
- 自動評価フレーム（正確性/安全性/バイアス/コスト/レイテンシ）を整備。回帰テストを導入。

### 11.3 実験管理・バージョニング
- seed 固定、データセットバージョニング（DVC/MLflow/W&B 等）。モデルカード/リスク評価を作成。

### 11.4 ガードレール
- 出力フィルタ、コンテンツポリシー、PII 検出/マスク、失敗時フォールバック、レート制御を設ける。

### 11.5 コスト管理
- トークン/推論コストのメトリクス化、上限設定、閾値超過のアラート。


## 12. データガバナンス

### 12.1 データ分類
- 機微度分類（Public/Internal/Confidential/Restricted）と取り扱いルールを定義。

### 12.2 ライセンス/第三者データ
- 許容/禁止ライセンス一覧を維持。第三者データ/モデルの利用条件を記録。

### 12.3 保持・削除
- 保持期間・削除ポリシー（GDPR/国内法等を考慮）。復旧計画と監査ログを保持。


---
付録 A. 推奨 .gitignore 追記
```
__pycache__/
.venv/
output/
.cache/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.log
*.tmp
*.bak
.coverage
coverage.xml
htmlcov/
dist/
build/
pip-wheel-metadata/
.tox/
.DS_Store
.idea/
.vscode/
.env
.env.*
.python-version
```

付録 B. 推奨 Makefile ターゲット例
```Makefile
.PHONY: bootstrap lint format typecheck test cov security build release clean
bootstrap:
	uv venv --python 3.13
	uv sync
	pre-commit install

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

test:
	uv run pytest -q

cov:
	uv run pytest --cov=src --cov-report=term-missing

security:
	# 例: bandit -r src || true
	echo "Run security scans in CI"

build:
	uv build

release:
	# タグ生成やリリースノート自動化をフック
	echo "Release pipeline"

clean:
	rm -rf .venv .cache .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage
```

付録 C. CI ワークフロー項目（参考）
- トリガ: PR, push（main）, schedule
- ジョブ: setup-uv → uv sync → lint → type → test+cov → security（CodeQL/SCA/Secret）→ sbom
- マトリクス: os=[ubuntu-latest, windows-latest, macos-latest], python=[3.11, 3.12, 3.13]
- permissions: contents: read, pull-requests: write（必要時のみ）等
- キャッシュキー: hashFiles('pyproject.toml', 'uv.lock')

付録 D. ruff 推奨ルール（例）
- E/F/W（pycodestyle/pyflakes）, I（import order）, UP（pyupgrade）, B（bugbear）, C90x, T20x（print 禁止）

付録 E. mypy 推奨 strict 設定（例）
```
warn_unused_ignores = True
warn_redundant_casts = True
no_implicit_optional = True
disallow_any_generics = True
warn_return_any = True
strict_equality = True
```

---
遵守事項:
- 本ルールはプロジェクトの品質基盤であり、逸脱はレビュー承認が必要である。
- 追加機能実装時は Phase 1 からの完全サイクルを繰り返すこと。