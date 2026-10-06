# 要件定義書（最終版）：Conversational Intent Compiler 最新版の Claude Code への引継ぎ

| 項目 | 内容 |
|---|---|
| 版・確認日 | **最終版**。2026-10-06 に、下記の事実を再確認済み（リポジトリ・タグ・Release・配布物の digest・テスト 30 件） |
| 対象 | Conversational Intent Compiler（以下「CIC」）プラグイン |
| 引き継ぐ版 | **v0.5.2**（タグ `v0.5.2` = コミット `0a828fe`）。`main` は `b57e015` で、v0.5.2 以降の差は README の表の更新のみ（コード・機能の差なし） |
| リポジトリ | https://github.com/ray-works-jp/conversational-intent-compiler （Public、MIT） |
| 引継ぎ先 | Claude Code（この文書の受け手） |
| 性格 | 引継ぎ用の文書（公開版）。アカウント固有の識別子と、事故の詳細は省略している |

> **事実の再確認方法**：リポジトリで `git fetch`、`git rev-parse --short v0.5.2^{commit}`（`0a828fe` を期待）、`gh release view v0.5.2 --repo ray-works-jp/conversational-intent-compiler --json assets`（第2章 2.1 の digest と照合）、`python -m unittest discover -s scripts -p "test_*.py"`（30 件成功を期待）。結果が本書と異なる場合は、**本書ではなく実物を正とし**、差を作成者へ報告すること。

> **この文書の読み方**：事実は「確認済み」「自己報告（未照合）」「未確認」に分けて書いています。「未確認」を「動く」と読み替えないでください。Claude Code は、シェルとファイル操作を使える前提です（作成者は、このホストで実機確認を済ませています）。ただし、受け手の環境が同じとは限らないので、第9章の受入確認を、受け手自身が実行してください。

---

## 1. 目的と範囲

### 1.1 引継ぎの目的
CIC の現行版（v0.5.2）を、仕様・状態・検証結果・未解決事項・運用規則を失わずに Claude Code へ渡し、**変更を加えても、確認済みの性質（原文の保持、権限の分離、検査の決定論性）を壊さずに開発を続けられる**ようにする。

### 1.2 範囲
- **対象（IN）**：CIC プラグイン一式（skill、Python CLI、スキーマ、フック、導入ツール、導入指示書、評価ハーネス、リリース手順）。
- **関連（参考）**：同じ作者の公開リポジトリ `ray-works-jp/relayguard`（別プロジェクト。ライセンス PolyForm Strict 1.0.0＝非商用・再配布不可）、応募用ポートフォリオ。CIC の引継ぎには含めない。
- **対象外（OUT）**：作者の非公開の製品・リポジトリ。ローカルの作業フォルダ。これらの内容は読まない・載せない。

### 1.3 成功条件
1. 受け手が第9章の受入確認を、根拠つきで全て満たす。
2. 受け手が行う変更のあと、第6章の検証（テスト・validate・ハッシュ・個人情報の確認）が通る。
3. 確認していない事項を「確認済み」と報告しない（第5章の区分を守る）。

---

## 2. 現況（事実）

### 2.1 リリース状態
| 項目 | 状態 | 確認方法 |
|---|---|---|
| バージョン | `plugin.json`、`.codex-plugin/plugin.json`、`.claude-plugin/plugin.json` が全て `0.5.2` | 確認済み（テストが一致を検査） |
| GitHub Releases | v0.5.2（Latest）、v0.4.1、v0.4.0、v0.3.1、v0.2.1 | 確認済み |
| タグ | `v0.2.1`、`v0.3.1`、`v0.4.0`、`v0.4.1`、`v0.5.0`（Release なし）、`v0.5.2` | 確認済み。`v0.2.0`、`v0.3.0`、`v0.5.1` は意図して削除済み（欠番） |
| v0.5.2 の配布物 | plugin ZIP：207,127 bytes・73 ファイル・sha256 `786850b56fc385ca02c7b4a05615c28ab6081e99324049a0dd80b118af25cfbe` ／ Antigravity ZIP：53,923 bytes・22 ファイル・sha256 `9008691d4a022a01c33fdd5bf26588d378ba245379ae8d51ad1b7da053b74af2` | 確認済み（GitHub の asset digest と手元の ZIP が一致） |
| テスト | 30 件（`test_cli.py` 17、`test_hook.py` 7、`test_package.py` 6）、全て成功 | 確認済み（2026-10-06 に再実行） |
| 追跡ファイル数 | 73（plugin ZIP の 73 と一致） | 確認済み |

### 2.1.1 作成者の環境 の導入状態（参考）
- 作成者の環境 の Antigravity に導入済みの plugin は **0.5.1**（導入指示書の検証で入れたもの。0.5.2 との差は文書のみで、機能は同一）。更新するかは作成者の判断。

### 2.2 ChatGPT 側の登録
- 作成者の ChatGPT アカウントに登録済みの private プラグイン（ID は非公開のため省略）は、GPT セッションの報告では **0.5.1・71 ファイル**（PRIVATE、scope USER）に更新済み。**自己報告で、作成者は未照合**。
- 0.5.1 と 0.5.2 の差は文書のみ（機能は同一）。更新は任意。更新する場合は v0.5.2 の plugin ZIP を使い、PRIVATE を維持し、新規作成しない。
- GitHub の v0.5.1 の Release とタグは削除済みで、その ZIP は GitHub から再取得できない。

### 2.3 リポジトリ構成（追跡ファイル 73）
| パス | 役割 |
|---|---|
| `plugin.json` / `.codex-plugin/plugin.json` / `.claude-plugin/plugin.json` | ChatGPT・Codex（Agent Plugins 1.0）／Codex 互換／Claude Code の manifest。`.claude-plugin/marketplace.json` も同居 |
| `skills/conversational-intent-compiler/` | `SKILL.md` と `references/`（`operation-guide.md`、`candidate-format.md`、`handoff.md`、`examples-and-boundaries.md`）。**挙動の仕様の正本**は SKILL.md と operation-guide |
| `scripts/` | `cic.py`（コア）、`cic_cli.py`（CLI）、`schema_spec.py`、`ledger_status.py`、`install_skill.py`、`install_antigravity_hook.py`、テスト 3 本、`cli-test-results.json` |
| `schemas/` | 9 スキーマ（event、state、delta、turn_ir、artifact、node、adoption、authority、reference） |
| `hooks/` | `hooks.json`（Claude Code）、`capture_turn.py`、`capture_antigravity.py`、`cic_ledger.py` |
| `hooks.json`（ルート） | Antigravity の plugin 用フック定義（`PreInvocation`、相対コマンド） |
| `docs/install/` | 導入指示書（`GPT-ja.md`、`ANTIGRAVITY-ja.md`）。バージョン・ハッシュを固定しない形 |
| `resources/research/` | 研究・設計の記録（参考資料。実装一覧ではない） |
| `resources/evaluation/` | 合成の自己検査、採点器、`pilot/`（小規模評価） |
| `resources/upstream-files.json` | 研究資料のパス・サイズ・SHA-256 の対応表（テストが検証） |
| `release-verification.json` | 版ごとの検証記録（実機確認と未確認を区別して記録） |
| `README.md` / `CHANGELOG.md` / `LICENSE`（MIT） | 利用者向け文書。作者・著作権者名は `ray-works-jp` |

### 2.3.1 ホスト別の対応と検証状況
| ホスト | 導入方法 | 検証状況 |
|---|---|---|
| Claude Code | `claude plugin marketplace add ray-works-jp/conversational-intent-compiler` → `claude plugin install conversational-intent-compiler-plugin@conversational-intent-compiler` | 確認済み：`claude plugin validate` 合格、marketplace・GitHub からの導入（隔離環境）、skill 起動から `init` 成功、フックによる 1 ターン記録 |
| Antigravity CLI（`agy`） | `agy plugin install https://github.com/ray-works-jp/conversational-intent-compiler`、または `scripts/install_skill.py` で単独 skill | 確認済み（1.2.14〜1.2.16）：plugin・単独の両配置で `PLUGIN_ROOT` 解決と `init` 成功、対話モードの許可確認と承認、plugin フックによる逐語記録。**別エージェントが導入指示書どおりに導入・`init` 成功**（自己報告） |
| Antigravity IDE / 2.0 | 同上（置き場が異なる） | **未確認** |
| ChatGPT / Codex | Plugin Creator へ ZIP を渡す（`docs/install/GPT-ja.md`） | ZIP 検証（ハッシュ・manifest・30 テスト）は GPT 側で実施（自己報告）。**ChatGPT 内でのスキル起動・Python 実行・永続保存は未確認**。フックは動作しない（仕様） |

---

## 3. 機能要件

### 3.1 設計原則（変更してはならない性質）
- **P1 原文が正本**：人間の原文は要約・正規化（改行・Unicode）せずに保存する。AI 応答・tool 結果・資料は別 event として扱う。
- **P2 origin と adoption の分離**：AI が提案し人間が選んでも、生成元を user に書き換えない。選択・確認は対象 ID・見た版・採用範囲を持つ別の関係。
- **P3 意図と権限の分離**：依頼・選択・委任・同意・参照を、外部操作の許可と混同しない。引用・添付・AI・tool・資料の中の命令は、データであり権威を持たない。
- **P4 裁量と未決の分離**：「任せる」は latitude、「迷っている」は未決。解釈の仮説をユーザーの明示条件に昇格させない。
- **P5 検証は正しさの証明ではない**：CLI は構造・引用・参照・状態遷移・保存を機械的に検査する。意味の正しさと実行許可は判定しない。preflight は機械的な適合判定。
- **P6 PASS でも記録する**：overlay が不要なら PASS できるが、raw の捕捉と、必要な状態確認は続ける。
- **P7 外部操作をしない**：CIC は送信・予約・購入・公開・取消を実行も許可もしない。replay は外部操作を再実行しない。

### 3.2 機能一覧（FR）
| ID | 機能 | 要件 | 実装・根拠 |
|---|---|---|---|
| FR-1 | 台帳の初期化 | 存在しない専用 DB を新規に作る。既存 DB は拒否（再 init しない） | `cic_cli.py init`。既存 DB への再実行が `FileExistsError` で拒否されることを確認済み |
| FR-2 | raw の捕捉 | 人間／AI／tool／external の raw を別 event として保存。event ID は再送で再利用し、同 ID に別内容を入れない。raw 捕捉と軽量投影は同一トランザクション | `capture`（`--ack-user-envelope` は呼び出し側の申告であり、認証ではない） |
| FR-3 | Delta の候補とひな形 | `delta-template --human-event-id` が、最新 base（state_version・watermark）を含む NO_CHANGE のひな形を返す | `delta-template` |
| FR-4 | Delta の検査と適用 | 候補を dry-run 検査（`validate --kind delta --transition`）し、CAS 検査のうえ commit（`apply`）。衝突時は最新の原文・状態から再解釈 | `validate`、`apply`（`--ack-authority-review` も申告であり許可ではない） |
| FR-5 | 意図操作（16 種） | `ADD`、`MODIFY`、`REVOKE`、`REPLACE`、`SUPERSEDE`、`CONFIRM`、`SELECT`、`REFERENCE`、`RESOLVE`、`REOPEN`、`DELEGATE`、`NARROW_SCOPE`、`EXPAND_SCOPE`、`NO_CHANGE`、`COMPLETE`、`SUSPEND` | `schemas/delta.schema.json` |
| FR-6 | 権限操作（4 種） | `GRANT`、`REVOKE`、`NARROW`、`EXPIRE`。意図操作と別の配列（`authority_operations`）。人間原文の支持と独立した意味監査が必要 | 同上 |
| FR-7 | 状態モデル | node の role は `goal`／`constraint`／`preference`／`prohibition`／`proposal`／`latitude`／`unknown`、lifecycle は `active`／`revoked`／`superseded`／`suspended`／`completed`／`expired`、origin は `user`／`assistant`／`tool`／`external`／`compiler` | `schemas/node.schema.json` |
| FR-8 | 状態の読取と再構築 | `state`（最新状態）、`replay`（台帳から再構築して比較）、`rebuild`（replay から cache を再保存） | CLI |
| FR-9 | 引継ぎ IR | `package` が、現 turn の raw・状態・根拠・coverage・known omissions を包む。routing は `PASS`／`ANNOTATE`／`CONTRACT`／`VERIFY` | `schemas/turn_ir.schema.json` |
| FR-10 | 権限の機械照合 | `preflight` が最新の権限と操作対象を機械的に照合する。実行・許可の発行はしない | CLI |
| FR-11 | 成果物・時刻・分岐 | `artifact`（ID・版・path・bytes hash）、`tick`（明示時刻による失効投影）、`fork`（親 watermark を固定した branch 作成） | CLI |
| FR-12 | 実行環境がない場合 | Python 実行と永続ファイルが使えない環境は、`references/handoff.md` の手動引継ぎ（原文・根拠・変更・有効条件・未決・権限境界）。永続台帳を更新したと言わない | skill |
| FR-13 | 人間入力の自動記録（任意） | `CIC_CAPTURE=1` のときだけ、人間入力の原文を `~/.cic/ledgers/<会話ID>.db`（`CIC_LEDGER_DIR` で変更可）へ逐語で追記。Claude Code は `UserPromptSubmit`、Antigravity は `PreInvocation`（`transcriptPath` の `USER_EXPLICIT` の `USER_INPUT` を読む）。stdout を汚さず、失敗しても常に正常終了 | `hooks/`。実機で確認済み |
| FR-14 | 未解釈入力の引継ぎ | `scripts/ledger_status.py` が、`pending_human` を読み取り専用で一覧（event ID・原文）。skill は古い順に `delta-template` → 解釈 → `validate` → `apply` で処理し、捕捉済み raw を再 capture しない | 確認済み（テスト・Claude Code 実機） |
| FR-15 | 導入ツール | `install_skill.py`（単独 skill の自己完結フォルダ。LICENSE・hooks・`ledger_status.py` 同梱）、`install_antigravity_hook.py`（`hooks.json` を書く。パスに空白があると拒否） | 確認済み |

### 3.3 CLI の入出力契約
- 全コマンドは `{ok, command, result, limitations, external_execution_authorized: false}` の形で返す。入力は UTF-8 JSON ファイル、出力は**新規ファイル**（既存の出力ファイルは上書きしない）。
- DB 本体・sidecar・入力・プラグインのソースと同じ path へ出力しない。
- コマンド：`init`、`capture`、`delta-template`、`apply`、`validate`、`package`、`state`、`replay`、`rebuild`、`preflight`、`artifact`、`tick`、`fork`。

---

## 4. 非機能要件・制約

### 4.1 非機能要件（NFR）
| ID | 要件 |
|---|---|
| NFR-1 | Python 3.12 以上、標準ライブラリのみ。外部通信なし、モデル呼び出しなし（CLI は意味を判定しない）。ローカル SQLite |
| NFR-2 | 決定論：同じ入力から同じ状態（replay で再構築した結果が保存状態と一致） |
| NFR-3 | 原文のバイト保存。UTF-8、`.gitattributes` の `* -text` により改行を変換しない |
| NFR-4 | 冪等：同一 event ID・同一内容の再送は重複 commit にならない。CAS（base_state_version・base_watermark）で競合を検出する |
| NFR-5 | フックは既定で無効。stdout に何も出さず（Antigravity は `{}`）、**読む環境変数は `CIC_CAPTURE` と `CIC_LEDGER_DIR` の 2 つだけ**で、環境変数の一覧を読まず・記録せず、常に終了コード 0 |
| NFR-6 | フックの command は `python` をPATHから呼ぶ（`python3` のみの環境では動かない。README に前提として明記済み）。Antigravity の plugin フックは相対コマンドで、**引用符を入れると壊れる**（cwd が plugin dir） |
| NFR-7 | 保存した原文は平文。暗号化・保持期間・削除・ACL は未実装（利用環境の方針に従う） |

### 4.2 不変の制約（壊してはならないもの）
1. **ハッシュ照合**：`resources/upstream-files.json` の 33 ファイルの SHA-256 と実ファイルが一致する（テストが検査）。該当ファイルの改行・内容を変えない。`.gitattributes` を外さない。
2. **バージョンの一致**：3 つの manifest、README 冒頭の `version X`、`release-verification.json` の `release`、CHANGELOG の見出しを、リリースごとに同時に更新する（テストが検査）。
3. **コアの不変性**：`cic.py`・`schema_spec.py` は、このリポジトリの初回コミット（`7853ebd`）以降、変更されていない（`cli-test-results.json` に、0.1.0 の試作と同一であるという記録もある）。変更する場合は意図を明記し、記録を更新する。
4. **個人情報の非掲載**：公開物にメールアドレス、API キー、トークン、ローカルの個人パスを入れない。コミットの作者は GitHub の noreply アドレス（`250263009+ray-works-jp@users.noreply.github.com`）、名前は `ray-works-jp`。
5. **主張の上限**：「全ターン自動追跡」「意味精度の保証」「原文直接入力より優れる」「第三者による品質保証」とは書かない。

---

## 5. 検証状況の台帳（確認の区分）

### 5.1 確認済み
- 30 テスト（構造契約、フック、パッケージ、バージョン一致、ハッシュ、導入ツール）の成功。展開した ZIP でも成功。
- `claude plugin validate`、`agy plugin validate` の合格。
- Claude Code・Antigravity CLI での実機動作（上記 2.3.1）。
- 小規模パイロット：Claude Code 実機（`claude-sonnet-5-5`、skill の手順どおり）で、日本語 5 シナリオ・18 発話を処理し、18/18 が `apply`、自動のキーワード検査 19/20（不一致 1 件は採点器の偽陽性と判断）。`resources/evaluation/pilot/RESULTS.md`。

### 5.2 自己報告（未照合）
- ChatGPT の登録版が 0.5.1（71 ファイル、PRIVATE）であること。
- Antigravity のエージェントが導入指示書どおりに導入・`init` に成功したこと。
- GPT 側での ZIP 検証（ハッシュ・manifest・30 テスト）、および **Codex 環境での** Python による台帳の初期化と読み取り（ChatGPT 上ではない）。

### 5.3 未確認（「動く」と言わない）
- ChatGPT 内でのスキル起動、Python 実行、永続ファイルによる台帳の保存。
- Antigravity IDE / 2.0 での plugin フックの実行。
- 意味精度の一般性：パイロットは**評価者が実行側と同一**、各 1 回、比較対象（原文直接入力）なし。長い会話、曖昧な参照、複数候補の選択、他モデル・他ホストは未測定。
- 全ターンの自動介入（フックは人間入力の記録のみで、AI 応答・tool 結果・Delta は記録しない。`/clear` 後の別 session、複数端末は対象外）。

---

## 6. 運用規則（引継ぎ後も守る手順）

### 6.1 変更の標準手順
1. 変更し、`python -m unittest discover -s scripts -p "test_*.py"` を実行（全成功）。`claude plugin validate .`、`agy plugin validate .` も実行。
2. バージョンを上げる場合は 4.2 の 2 を満たす（CHANGELOG と `release-verification.json` も更新）。
3. コミットは `ray-works-jp` の noreply 作者で行う。コミットメッセージの末尾に、使用した AI の共作者表記を付ける運用だった（環境の指示に従う）。
4. 公開前に、追跡ファイルに個人情報・秘密情報が無いことを検索で確認する。

### 6.2 リリース手順（実績）
1. タグを付けて `main` とタグを push。
2. **タグの内容から** ZIP を作る（`git archive <tag>` を展開 → plugin ZIP は `conversational-intent-compiler-plugin/` を接頭辞に、Antigravity ZIP は展開物で `scripts/install_skill.py` を実行した結果）。作業ツリーの CRLF を拾わないこと。
3. 展開した ZIP で、テスト・validate・`init` を確認。
4. `gh release create` で Release を作り、asset の digest と手元の SHA-256 の一致を確認。
5. 導入指示書は ZIP 自身のハッシュを書けないので、固定のハッシュを書かず、Release の digest と照合させる。

### 6.2.1 実行ごとのユーザー承認が必要な操作
作成者（ユーザー）は、次の外向きの操作を、**その都度明示した指示のあったときだけ**許可してきた。許可なく行わない：GitHub への push・Release 作成・タグ削除、ChatGPT のプラグイン登録・更新、設定ファイルの変更、プラグインの導入・削除。

### 6.3 確定済みの決定（ユーザー）
- CIC のライセンスは MIT。作者・著作権者名は GitHub アカウント名 `ray-works-jp`（以前は `t93094195-jpn` で、統一済み）。
- 公開リポジトリは Public。メールアドレスは公開しない。
- 非公開の製品・リポジトリは、公開物に載せない。
- `v0.2.0`、`v0.3.0`、`v0.5.1` のタグ、`v0.5.0`・`v0.5.1` の Release は削除する方針（実施済み）。
- 導入と検証の許可確認は迂回しない（`--dangerously-skip-permissions` を原則使わない。使った場合はユーザーの許可と範囲を記録）。

---

## 7. 既知の制限・未解決事項（優先度順）

| # | 内容 | 影響 | 備考 |
|---|---|---|---|
| 1 | ChatGPT 内での動作が未確認 | 主要ホストの 1 つで保証がない | `docs/install/GPT-ja.md` の手順で、受け手が確認・報告する |
| 2 | 意味精度が未評価（パイロットのみ） | 「正しい Delta を作れるか」の根拠が弱い | 独立した評価者による gold、シナリオ増、反復、原文直接入力との対照（`resources/evaluation/` の事前登録の A–E 比較）が次の候補 |
| 3 | Antigravity の IDE / 2.0 が未確認 | plugin フックが動くか不明（フォーラムに同様の質問あり） | 実機がないと確認できない |
| 4 | フックが `python` コマンドを前提とする | `python3` のみの macOS・Linux でフックがエラーになる | 修正案の `||` による切替は、Windows のシェル不明で未採用 |
| 5 | Antigravity の transcript の形式が公式 docs にない | `agy` の更新で記録が取り込めなくなる可能性 | 観察に基づく実装（`USER_INPUT` / `USER_EXPLICIT` / `<USER_REQUEST>`） |
| 6 | 保存する原文が平文。暗号化・保持期間・削除・ACL・durable inbox・dispatch lease・実行中取消は未実装 | 機密を扱う運用には不向き | README に明記済み |
| 7 | AI 応答・tool 結果は自動では台帳に入らない | 全体の追跡は不完全 | 仕様。skill の手順でホスト AI が捕捉する |
| 8 | v0.5.2 の ZIP の中の README が、表の更新前の版 | 軽微 | 機能の差なし。必要なら v0.5.3 |

---

## 8. 事故・注意（再発防止）
- **環境変数の露出**：調査用のコマンドが、フックのプロセスの環境変数を出力してしまう事故があった（一時ファイルは削除済み）。以後、環境変数の一覧を出力・保存しない。CIC のフックが読む環境変数は `CIC_CAPTURE` と `CIC_LEDGER_DIR` の 2 つだけで、その他は読まず、記録しない。
- Windows の注意：標準入出力が cp932 になるため、日本語の入出力は UTF-8 を明示する（`sys.stdout.reconfigure(encoding="utf-8")`、`stdin.buffer` を decode）。作業ツリーの改行が CRLF の環境がある。`git archive` で配布物を作る。
- Antigravity の headless 実行はコマンドが自動拒否される（許可ルールまたは対話が必要）。許可ルールの一時追加は、実行後に必ず元へ戻す。

---

### 8.1 Claude Code 固有の注意
- **plugin の構造**：manifest は `.claude-plugin/plugin.json`、skill は `skills/`、フックは `hooks/hooks.json`（`${CLAUDE_PLUGIN_ROOT}` で参照）。plugin 名は `claude-` などで始められない（予約名の検査があり、`conversational-intent-compiler-plugin` は合格）。ルートの `hooks.json` は Antigravity 用で、Claude Code は読まない。
- **skill の場所**：skill の読み込み時に base directory が提示される。`PLUGIN_ROOT` は、`SKILL_ROOT/scripts/cic_cli.py` が存在すれば `SKILL_ROOT`、なければ 2 階層上。**存在確認は、Glob などの検索ではなく、パスを直接指定した確認（`ls`・`Test-Path`・Read）で行う**（Glob が 0 件を返して誤判断した実績がある）。
- **許可**：非対話実行（`-p`）では、許可のないコマンドは `This command requires approval` で拒否され、作業ディレクトリ外の Read も拒否される（`--add-dir` が必要）。必要最小限の `--allowedTools` を使う。実環境の設定を変えずに試すには、`CLAUDE_CONFIG_DIR` に使い捨てのフォルダを指定する。
- **フック**：`UserPromptSubmit` の stdout はモデルの文脈へ入るため、何も出力しない。`python` コマンドが PATH に必要。
- **この環境の版**：作成時の確認は Claude Code 2.1.280 で行った。

---

## 9. 引継ぎの受入確認（受け手が行う）

以下を、**根拠（実行したコマンドと結果）つき**で報告する。できないものは「できない」と報告する。

| # | 確認 | 期待 |
|---|---|---|
| A1 | リポジトリを取得し、`git describe` / タグ一覧を確認 | `v0.5.2` が `0a828fe`、`main` が `b57e015` 以降 |
| A2 | Release の ZIP 2 つの SHA-256 を、第2章 2.1 の値と照合 | 一致 |
| A3 | Python 3.12 以上を確認し、30 テストを実行（`python -m unittest discover -s scripts -p "test_*.py"`） | 全成功（このホストは Python を実行できる前提のため**必須**） |
| B1 | `skills/.../SKILL.md` と `references/operation-guide.md` を読み、第3章 3.1 の P1〜P7 を自分の言葉で要約 | 原文正本・origin と adoption の分離・意図と権限の分離・検証は正しさの証明ではない、を含む |
| B2 | 第7章の未解決事項を、自分の優先度と理由つきで並べ替えて提案 | 作成者の判断を要するものを区別している |
| B3 | 第4章 4.2 の不変の制約を、守れないケースの例とともに説明 | 4.2 の 1（ハッシュ）と 2（バージョン一致）を含む |
| D1 | `claude plugin validate .` | `Validation passed` |
| D2 | **使い捨ての `CLAUDE_CONFIG_DIR`** で `claude plugin marketplace add ray-works-jp/conversational-intent-compiler` → `claude plugin install conversational-intent-compiler-plugin@conversational-intent-compiler` | version 0.5.2・enabled。実環境の設定は変更しない |
| D3 | skill を起動し、`PLUGIN_ROOT` を直接のパス確認で解決して、一時 DB に `init` を 1 回 | `"ok": true`。検索ツールを使っていない。使った許可（`--allowedTools` など）を報告 |
| D4 | `CIC_CAPTURE=1` と `CIC_LEDGER_DIR`（使い捨て）で 1 ターンを実行し、`ledger_status.py` で `pending` を確認（Delta は適用しない） | 発話が逐語で `pending` に入る |
| D5 | 許可ルールなしの**対話**で、コマンド実行前に許可確認が出るかを観察（未判定事項の解消） | 出た／出なかったを、画面と記録の両方で根拠つきで報告 |
| C2 | 変更を提案する場合、影響範囲（テスト・manifest・README・hashed ファイル）と検証手順を先に示す | 第6章に従う |

**受入の合否**：A1〜A3、B1〜B3、D1〜D4 が根拠つきで満たされれば、引継ぎ完了とする。D5 は、環境が無い・許可が得られない場合は、理由を記録して未解決事項へ加える。

---

## 付録 A. コマンド早見
```text
python scripts/cic_cli.py --help
python scripts/cic_cli.py --db <DB> init --conversation <ID> --branch main
python scripts/cic_cli.py --db <DB> state --conversation <ID> --branch main
python scripts/ledger_status.py [--dir DIR] [--conversation ID]
python -m unittest discover -s scripts -p "test_*.py"
claude plugin validate .
agy plugin validate .
gh release view v0.5.2 --repo ray-works-jp/conversational-intent-compiler --json assets
```

## 付録 B. 用語
- **Delta**：今回の人間入力が、意図の状態をどう変えるかの候補（operations と authority_operations）。
- **Turn IR**：現 turn の raw・有効条件・未決・権限・根拠・coverage を小さくまとめた引継ぎデータ。
- **pending_human**：捕捉済みだが、どの Delta も適用されていない人間 event。
- **CAS**：Delta の base_state_version・base_watermark が最新と一致する場合だけ commit する検査。
- **PASS**：重い意味 overlay を省ける turn。raw の捕捉は省かない。

## 付録 C. 参照
- 利用者向け：README.md、CHANGELOG.md、`release-verification.json`
- 挙動の仕様：`skills/conversational-intent-compiler/SKILL.md`、`references/operation-guide.md`、`references/candidate-format.md`、`references/handoff.md`、`references/examples-and-boundaries.md`
- 研究・設計の記録：`resources/research/`（参考。実装済み機能の一覧ではない）
- 評価：`resources/evaluation/pilot/RESULTS.md`
