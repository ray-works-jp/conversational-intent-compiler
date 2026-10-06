# 要件定義書（最終版）：Conversational Intent Compiler 最新版の Antigravity への引継ぎ

| 項目 | 内容 |
|---|---|
| 版・確認日 | **最終版（v0.6.2 対応）**。2026-10-06 に、0.6.2 の plugin ZIP（下記 SHA-256）を展開し、77 テストの成功と `claude plugin validate .` の合格を確認。GitHub のタグ・Release は 0.6.2 では未作成（確認済み） |
| 対象 | Conversational Intent Compiler（以下「CIC」）プラグイン |
| 引き継ぐ版 | **v0.6.2**（plugin ZIP `conversational-intent-compiler-plugin-0.6.2.zip`。**GitHub 未公開**：タグ・Release なし、作業ツリー未コミット）。公開済みの最新は v0.6.0（タグ = コミット `58fdca3`）。v0.6.0 からの差は、**継続会話モード・UserPromptSubmit ブリッジ・ループ運転の強化（0.6.1）と、task scope 条件の配送修正（0.6.2）**（第3章 FR-18〜FR-20）。 |
| リポジトリ | https://github.com/ray-works-jp/conversational-intent-compiler （Public、MIT） |
| 引継ぎ先 | Antigravity（この文書の受け手） |
| 性格 | 引継ぎ用の文書（公開版）。アカウント固有の識別子と、事故の詳細は省略している |

> **事実の再確認方法**：渡された ZIP の SHA-256 が第2章 2.1 の値と一致するか確認し、展開して `python -m unittest discover -s scripts -p "test_*.py"`（77 件成功を期待）を実行する。GitHub 側は `git ls-remote --tags origin`（`v0.6.2` が**ない**ことを期待。あれば Release の digest と照合）。結果が本書と異なる場合は、**本書ではなく実物を正とし**、差を作成者へ報告すること。

> **この文書の読み方**：事実は「確認済み」「自己報告（未照合）」「未確認」に分けて書いています。「未確認」を「動く」と読み替えないでください。Antigravity は、シェルとファイル操作を使える前提です（作成者は、このホストで実機確認を済ませています）。ただし、受け手の環境が同じとは限らないので、第9章の受入確認を、受け手自身が実行してください。

---

## 1. 目的と範囲

### 1.1 引継ぎの目的
CIC の現行版（v0.6.2）を、仕様・状態・検証結果・未解決事項・運用規則を失わずに Antigravity へ渡し、**変更を加えても、確認済みの性質（原文の保持、権限の分離、検査の決定論性）を壊さずに開発を続けられる**ようにする。

### 1.2 範囲
- **対象（IN）**：CIC プラグイン一式（skill、Python CLI、スキーマ、フック、導入ツール、導入指示書、評価ハーネス、リリース手順、**ループ運転 `cic_loop.py` と、同梱した最初のコンパイラー**）。
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
| バージョン | ZIP 内の `plugin.json`、`.codex-plugin/plugin.json`、`.claude-plugin/plugin.json` が全て `0.6.2`（公開済みの GitHub 最新は `0.6.0`） | 確認済み（テストが一致を検査） |
| GitHub Releases | v0.6.0（Latest）、v0.5.2、v0.4.1、v0.4.0、v0.3.1、v0.2.1 | 確認済み |
| v0.6.2 の公開状態 | タグ `v0.6.2`・Release なし（ローカルと origin のタグ一覧で確認）。作業ツリーに 0.6.1／0.6.2 の変更が未コミットで残る | 確認済み（2026-10-06） |
| タグ | `v0.2.1`、`v0.3.1`、`v0.4.0`、`v0.4.1`、`v0.5.0`（Release なし）、`v0.5.2`、`v0.6.0` | 確認済み。`v0.2.0`、`v0.3.0`、`v0.5.1` は意図して削除済み（欠番） |
| v0.6.0 の配布物（公開済み） | plugin ZIP：295,370 bytes・87 ファイル・sha256 `468750575e1463359a4da4eee0e999c526abb59cc3f51608ffc153f1b8cd44f2` ／ Antigravity ZIP：97,309 bytes・31 ファイル・sha256 `ddd5cee3ce72af3e77365c20e92c5a90d44929ea274a331b9c8296c1cb010af9` | 確認済み（GitHub の asset digest と手元の ZIP が一致）。ループ運転（`cic_loop.py`）と、最初のコンパイラーの同梱 7 ファイルを含む |
| **v0.6.2 の配布物（未公開）** | plugin ZIP：317,913 bytes・91 ファイル（ZIP 直下がプラグインのルート。上位フォルダなし）・sha256 `b59a028c7e09d14a408ca367cc7388da44e480b5126f2faf0883ec7a319dbdca` ／ Antigravity ZIP：**未作成** | 確認済み（ZIP を展開して読了）。継続会話モード（`cic_session.py`、`continuous_turn.py`）を含む |
| テスト | 77 件（`test_cli.py` 17、`test_hook.py` 7、`test_package.py` 6、`test_loop.py` 31、`test_session.py` 16）、全て成功 | 確認済み（2026-10-06、0.6.2 の ZIP を展開して実行。約 58 秒）。v0.6.0 は 45 件 |
| ファイル数 | v0.6.0 の追跡ファイルは 87。v0.6.2 の ZIP は 91（= 87 ＋ 新規 4：`hooks/continuous_turn.py`、`scripts/cic_session.py`、`scripts/test_session.py`、`skills/.../references/continuous-loop.md`） | 確認済み |

### 2.1.1 作成者の環境 の導入状態（参考）
- 作成者の環境 の Antigravity に導入済みの plugin は **0.5.1**（導入指示書の検証で入れたもの。0.6.2 との差は、ループ運転・継続会話モードの追加など）。更新するかは作成者の判断。

### 2.2 ChatGPT 側の登録
- 作成者の ChatGPT アカウントに登録済みの private プラグイン（ID は非公開のため省略）は、GPT セッションの報告では **0.5.1・71 ファイル**（PRIVATE、scope USER）に更新済み。**自己報告で、作成者は未照合**。
- 0.5.1 から 0.6.2 までの差は、フック・文書・**ループ運転・継続会話モード（ローカル実行・信頼済み hook が前提で、ChatGPT 内の Cloud Work では hook が動かない）**。更新は任意。更新する場合は v0.6.2 の plugin ZIP を使い、PRIVATE を維持し、新規作成しない。
- GitHub の v0.5.1 の Release とタグは削除済みで、その ZIP は GitHub から再取得できない。

### 2.3 リポジトリ構成（v0.6.0：追跡ファイル 87 ／ v0.6.2 の ZIP：91）
| パス | 役割 |
|---|---|
| `plugin.json` / `.codex-plugin/plugin.json` / `.claude-plugin/plugin.json` | ChatGPT・Codex（Agent Plugins 1.0）／Codex 互換／Claude Code の manifest。`.claude-plugin/marketplace.json` も同居 |
| `skills/conversational-intent-compiler/` | `SKILL.md` と `references/`（`operation-guide.md`、`candidate-format.md`、`handoff.md`、`examples-and-boundaries.md`）。**挙動の仕様の正本**は SKILL.md と operation-guide |
| `scripts/` | `cic.py`（コア）、`cic_cli.py`（CLI）、`schema_spec.py`、`ledger_status.py`、`install_skill.py`、`install_antigravity_hook.py`、テスト 4 本、`cic_loop.py`（ループ運転）、`cli-test-results.json` |
| `schemas/` | 9 スキーマ（event、state、delta、turn_ir、artifact、node、adoption、authority、reference） |
| `hooks/` | `hooks.json`（Claude Code）、`capture_turn.py`、`capture_antigravity.py`、`cic_ledger.py` |
| `hooks.json`（ルート） | Antigravity の plugin 用フック定義（`PreInvocation`、相対コマンド） |
| `docs/install/` | 導入指示書（`GPT-ja.md`、`ANTIGRAVITY-ja.md`）。バージョン・ハッシュを固定しない形 |
| `docs/loop-ja.md` | ループ運転の仕様（使い方・停止・検査項目・限界） |
| `resources/intent-compiler/` | **最初のコンパイラー（Intent Compiler 0.1.0）の無改変コピー 7 ファイル**と `SHA256SUMS.txt`。`cic_loop.py` が、実行仕様 `system-prompt.md` を読む |
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
| ループ運転 | `python scripts/cic_loop.py`（バックエンド：`claude`／`agy`／`cmd:<コマンド>`）。ホストの機能ではなく、ローカルの実行器 | `claude` で実機確認済み（4 回処理・明示停止・台帳に逐語記録）。`agy`・`cmd:` は実モデルで未確認 |

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
- **P8 ループは、明示的な停止だけで終わる**：停止語（`:stop` など）、入力の終わり、Ctrl-C 以外では終わらない。T0・質問・検査の不合格・バックエンドのエラーでも続ける。自然な依頼文（「サーバーを止めて」）は停止にしない。
- **P9 最初のコンパイラーの実行仕様は改変しない**：`resources/intent-compiler/` の 7 ファイルは無改変（ハッシュをテストが検査）。ループは、それをそのまま読んで使う。

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
| FR-16 | **ループ運転** | 人間の雑な入力 → コンパイラ AI（T0／IR／質問 1 つのどれか）→ 機械の検査 → 応答 AI → 次の入力、を**明示的に停止するまで繰り返す**。IR は原文との照合（`q` の逐語一致、`src=u` に `q`、`must` の出自、`assume` の `if_wrong` など）に通ったものだけを応答 AI へ渡し、不合格は 1 回直させ、それでも不合格なら IR を捨てて原文をそのまま渡す。質問は人間へ返す。履歴（0.6.1 以降は既定で全 turn・原文全文。`--history N` で直近 N 回）を両方の AI へ渡す。`--ledger` で人間の入力と AI の応答を台帳へ逐語で記録、`--ab` で IR なしの応答も記録、`--script` でファイルから運転 | `scripts/cic_loop.py`、`docs/loop-ja.md`。`test_loop.py` 31 テスト（モックのバックエンド）と、`claude` による実機確認 |
| FR-17 | 最初のコンパイラーの同梱 | 最初のコンパイラー（Intent Compiler 0.1.0）の 7 ファイルを無改変で同梱し、`SHA256SUMS.txt` で検査する。単独 skill の導入（`install_skill.py`）にも、`cic_loop.py` と合わせて同梱する | `resources/intent-compiler/`、`test_loop.py`、`test_package.py` |
| FR-18 | **継続会話モード（0.6.1）** | 明示起動（`:cic start`／`コンパイラ開始`）した同じ会話・branch で、各 turn に「prepare（原文を先に保存）→ ホストの Compiler／Delta 検査・commit → dispatch（実際に package した Turn IR 全文と hash を応答前に保存）→ 元の依頼への応答 → complete（応答を別出自で保存）」を行い、直接人間入力の停止語まで続ける。start/stop は原文 human event から派生し、再読込・再開・branch 分離・再送の冪等を扱う。complete は、配送内容・raw・state 版・新しい human/stop・同 turn の別応答を検査して拒否する。prepared（表示前の本文）と observed（実際に表示した原文）を区別する。**0.6.2**：task scope の有効条件が dispatch に届かない接続漏れを修正（`task_id` を core.package へ渡し、task scope 条件があるのに `task_id` を省略した配送は拒否） | `scripts/cic_session.py`、`skills/.../references/continuous-loop.md`、`scripts/test_session.py`（16 テスト）。dispatch は処理 lease でも外部操作の許可でもない |
| FR-19 | UserPromptSubmit ブリッジ（0.6.1） | 信頼済みローカルの runtime（Codex／Claude Code）で、開始後の各 turn に固定の処理手順を挿入し、直接人間入力の原文を先に保存する。ユーザー原文を developer 指示へコピーしない。Cloud Work は command hook を実行しないため対象外（skill＋session の継続で、強制介入は保証しない）。インストールだけでは hook を信頼したことにならない | `hooks/continuous_turn.py`、`hooks/hooks.json`（`capture_turn.py` と並置）。実ホストでの hook 実行は未確認 |
| FR-20 | ループ運転の強化（0.6.1） | `cic_loop.py` を、全 turn・原文全文の履歴（既定。`--history N` で直近 N 回）、台帳からの再開、停止入力の保存、入力の終わり＝suspended／Ctrl-C＝interrupted、バックエンドの失敗・引用付き argv への対応へ拡張。`claude` は tool／skill／hook／MCP を制限。`agy`・`cmd:` は tool なしを保証できないため `--allow-agent-tools` の明示が必要。XML ループは意味 Delta を自動確定しない | `scripts/cic_loop.py`、`docs/loop-ja.md`、`scripts/test_loop.py`（31 テスト）。`--ab` は同一履歴からの局所比較で、正式な raw 比較ではない |

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
| NFR-8 | ループ運転は、外部のモデル CLI（`claude`／`agy`／任意のコマンド）を呼ぶ（コア CLI・フック・台帳はモデルを呼ばない）。応答 AI にはツールを与えない（外部操作をしない）。IR（モデルの出力）は、`DOCTYPE`・エンティティ宣言・CDATA・処理命令・2 万文字超を、パースの前に拒否する。0.6.1 以降：`claude` バックエンドは tool／skill／hook／MCP を制限し、`agy`・`cmd:` は tool なしを保証できないため `--allow-agent-tools` の明示が必要 |
| NFR-9 | 継続会話モードは、同梱 Python と永続ファイル（会話専用の SQLite）を必要とする。`cic_session.py` の入出力は新しい UTF-8 JSON。CLI の attestation は認証ではない。hook は信頼済みローカルのみで、Cloud Work は強制介入できない。同じモデルの二重呼出しを防ぐ lease、tool イベントの完全捕捉、無期限・複数端末の保存は未保証 |

### 4.2 不変の制約（壊してはならないもの）
1. **ハッシュ照合**：`resources/upstream-files.json` の 33 ファイルの SHA-256 と実ファイルが一致する（テストが検査）。該当ファイルの改行・内容を変えない。`.gitattributes` を外さない。
2. **バージョンの一致**：3 つの manifest、README 冒頭の `version X`、`release-verification.json` の `release`、CHANGELOG の見出しを、リリースごとに同時に更新する（テストが検査）。
3. **コアの不変性**：`cic.py`・`schema_spec.py` は、このリポジトリの初回コミット（`7853ebd`）以降、変更されていない（`cli-test-results.json` に、0.1.0 の試作と同一であるという記録もある）。変更する場合は意図を明記し、記録を更新する。
4. **個人情報の非掲載**：公開物にメールアドレス、API キー、トークン、ローカルの個人パスを入れない。コミットの作者は GitHub の noreply アドレス（`250263009+ray-works-jp@users.noreply.github.com`）、名前は `ray-works-jp`。
5. **主張の上限**：「コンパイルしたほうが、そのまま渡すより良い」（未測定）、「全ターン自動追跡」「意味精度の保証」「原文直接入力より優れる」「第三者による品質保証」とは書かない。
6. **最初のコンパイラーの 7 ファイル**（`resources/intent-compiler/`）は無改変。変更する場合は、新しい版として別に置き、`SHA256SUMS.txt` とテストを更新する。
7. **ループの停止の意味**：停止語（`STOP_WORDS`）以外の入力を停止にしない。T0・質問・検査の不合格・エラーで止めない（`test_loop.py` が検査）。

---

## 5. 検証状況の台帳（確認の区分）

### 5.1 確認済み
- 77 テスト（構造契約、フック、パッケージ、バージョン一致、ハッシュ、導入ツール、ループ運転、**継続会話モード**）の成功。0.6.2 の ZIP を展開して実行（2026-10-06）。`claude plugin validate .` の合格（0.6.2 の展開物）。`agy plugin validate .` はエラー表示なし（hooks 1 件処理）。
- `claude plugin validate` の合格（0.6.2 を含む）。`agy plugin validate` は 0.6.2 でエラー表示なし。
- Claude Code・Antigravity CLI での実機動作（上記 2.3.1）。
- 小規模パイロット：Claude Code 実機（`claude-sonnet-5-5`、skill の手順どおり）で、日本語 5 シナリオ・18 発話を処理し、18/18 が `apply`、自動のキーワード検査 19/20（不一致 1 件は採点器の偽陽性と判断）。`resources/evaluation/pilot/RESULTS.md`。
- **ループ運転の実機確認**：`cic_loop.py --script`（入力 5 行＋`:stop`＋停止後の 1 行）を、コンパイラ・応答の両方に `claude -p` を使って実行。4 回処理（IR、T0、**履歴を使った訂正**、不可逆の依頼で gate）し、明示停止で終了。停止後の行はログにも台帳にも入っていない。台帳には人間の入力 4 件が逐語で入った。検査の不合格 0 件。

### 5.2 自己報告（未照合）
- ChatGPT の登録版が 0.5.1（71 ファイル、PRIVATE）であること。
- Antigravity のエージェントが導入指示書どおりに導入・`init` に成功したこと。
- GPT 側での ZIP 検証（ハッシュ・manifest・30 テスト）、および **Codex 環境での** Python による台帳の初期化と読み取り（ChatGPT 上ではない）。

### 5.3 未確認（「動く」と言わない）
- ChatGPT 内でのスキル起動、Python 実行、永続ファイルによる台帳の保存。
- Antigravity IDE / 2.0 での plugin フックの実行。
- 意味精度の一般性：パイロットは**評価者が実行側と同一**、各 1 回、比較対象（原文直接入力）なし。長い会話、曖昧な参照、複数候補の選択、他モデル・他ホストは未測定。
- 全ターンの自動介入（フックは人間入力の記録のみで、AI 応答・tool 結果・Delta は記録しない。`/clear` 後の別 session、複数端末は対象外）。
- **コンパイルの価値**：「コンパイルしたほうが、そのまま渡すより良い」ことは未測定（`--ab` のログで盲検比較が必要）。
- ループの `agy` と `cmd:` のバックエンドを、実モデルで動かした結果。利用者のグローバルなフックを隔離した場合のコンパイラの挙動。
- **継続会話モードの実ホスト確認**：`continuous_turn.py` の hook 実行（Claude Code・Codex）、Cloud Work での 2 turn 目以降の継続、Antigravity 上の動作。`:cic start` → 複数 turn → `:stop` の実機記録がない。
- **0.6.2 の GitHub 公開**（タグ・Release・Antigravity 用 ZIP）と、ChatGPT・Antigravity への 0.6.x の導入。

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
- **2026-10-06：最初のコンパイラーに戻り、「人間の雑な入力 → コンパイラ AI → AI の応答 → … → 明示的に停止」のループを最新版へ追加する**と決定（台帳を使うパイプライン案 `cic_pipeline.py` は保留）。
- 導入と検証の許可確認は迂回しない（`--dangerously-skip-permissions` を原則使わない。使った場合はユーザーの許可と範囲を記録）。

---

## 7. 既知の制限・未解決事項（優先度順）

| # | 内容 | 影響 | 備考 |
|---|---|---|---|
| 1 | **コンパイルの価値が未測定**（IR 付きと、そのまま渡した場合の比較がない） | 作る価値の根拠がなく、モデル呼び出しは 2〜3 倍になる | `cic_loop.py --ab` のログを使った盲検比較（雑な入力 10〜20 件）。評価の基準は作成者が決める |
| 2 | ループの実モデル確認が `claude` のみ（`agy`・`cmd:` は未実行）。グローバルなフックの隔離が未確認 | コンパイラの出力が環境に影響される恐れ | 隔離した環境のコマンドを `--compiler cmd:` で指定して確認する |
| 3 | ChatGPT 内での動作が未確認 | 主要ホストの 1 つで保証がない | `docs/install/GPT-ja.md` の手順で、受け手が確認・報告する |
| 4 | 意味精度が未評価（パイロットのみ） | 「正しい Delta を作れるか」の根拠が弱い | 独立した評価者による gold、シナリオ増、反復、原文直接入力との対照（`resources/evaluation/` の事前登録の A–E 比較）が次の候補 |
| 5 | Antigravity の IDE / 2.0 が未確認 | plugin フックが動くか不明（フォーラムに同様の質問あり） | 実機がないと確認できない |
| 6 | フックが `python` コマンドを前提とする | `python3` のみの macOS・Linux でフックがエラーになる | 修正案の `||` による切替は、Windows のシェル不明で未採用 |
| 7 | Antigravity の transcript の形式が公式 docs にない | `agy` の更新で記録が取り込めなくなる可能性 | 観察に基づく実装（`USER_INPUT` / `USER_EXPLICIT` / `<USER_REQUEST>`） |
| 8 | 保存する原文が平文。暗号化・保持期間・削除・ACL・durable inbox・dispatch lease・実行中取消は未実装 | 機密を扱う運用には不向き | README に明記済み |
| 9 | AI 応答・tool 結果は自動では台帳に入らない | 全体の追跡は不完全 | 仕様。skill の手順でホスト AI が捕捉する |
| 10 | **0.6.2 が未公開**：GitHub にタグ・Release がなく、作業ツリーは未コミット。Antigravity 用 ZIP も未作成。ZIP に埋め込まれた `docs/handoff/` は、0.6.0 時点の注記つきの版 | 配布物を GitHub から取得できない。ChatGPT・Antigravity の更新ができない | 作成者の依頼があったときだけ、コミット・push・タグ・Release・Antigravity ZIP を作る（6.2）。その際、埋め込みの引継ぎ文書を最新へ差し替えるなら 0.6.3 として出し直す |
| 11 | **継続会話モードの実ホスト確認が薄い**：hook（`continuous_turn.py`）の実機実行、Cloud Work の 2 turn 目以降の継続、Antigravity 上の動作は未確認。release-verification には、Cloud Work で 0.6.1 の初回 turn を観察して 0.6.2 の修正につながったとの記録がある（自己報告・未照合）。意味精度・raw 直接入力との比較は未測定 | 「継続する」が実機で保証されていない | 実機で、`:cic start` → 2〜3 turn → `:stop` を観察し、記録を貼る |

---

## 8. 事故・注意（再発防止）
- **環境変数の露出**：調査用のコマンドが、フックのプロセスの環境変数を出力してしまう事故があった（一時ファイルは削除済み）。以後、環境変数の一覧を出力・保存しない。CIC のフックが読む環境変数は `CIC_CAPTURE` と `CIC_LEDGER_DIR` の 2 つだけで、その他は読まず、記録しない。
- Windows の注意：標準入出力が cp932 になるため、日本語の入出力は UTF-8 を明示する（`sys.stdout.reconfigure(encoding="utf-8")`、`stdin.buffer` を decode）。作業ツリーの改行が CRLF の環境がある。`git archive` で配布物を作る。
- Antigravity の headless 実行はコマンドが自動拒否される（許可ルールまたは対話が必要）。許可ルールの一時追加は、実行後に必ず元へ戻す。
- **ループ運転の注意**：応答 AI のツールは、`claude` では制限し、`agy`・`cmd:` では明示許可が必要で、IR の `gate` は文章上の指示で、コードによる強制ではない。IR はモデルの出力なので、検査（`q` の逐語一致など）が必須。バックエンドの `claude -p` は、利用者の環境のフック・設定を読み込む場合があり、コンパイラの出力に影響しうる。ループは、モデルへ入力を送るため、個人情報を含む入力は利用先の方針を確認する。

---

### 8.1 Antigravity 固有の注意
- **導入の形**：`agy plugin install <GitHub の URL またはローカルのパス>`。plugin は `~/.gemini/config/plugins/<名前>/` へコピーされ、`dist/` などの未追跡の生成物もコピーされる。単独 skill は `.agents/skills/`（既定）、グローバルは版により `~/.gemini/antigravity-cli/skills`（CLI）または `~/.gemini/config/skills`（2.0・IDE）。plugin と単独 skill を同時に有効にしない。
- **フック**：plugin ルートの `hooks.json`（形式：`{"<名前>": {"enabled": true, "PreInvocation": [{"command": "python hooks/capture_antigravity.py"}]}}`）。**フックの cwd は plugin ディレクトリ**で、`command` は shell を介さずに実行される。**引用符を入れると壊れる**。フックの入力に発話本文はなく、`transcriptPath` の `transcript_full.jsonl` から読む（形式は公式 docs になく観察による）。
- **許可**：headless（`-p`）では、許可ルールのないコマンドは自動拒否される。単純な前置一致ルール（`command(python)` など）は通らず、**パスを含む正規表現ルール**が必要だった。ユーザーの設定に `ask: unsandboxed(*)` など、許可より優先される規則がある場合、ルールを足しても通らない。**ユーザーのグローバル設定（`settings.json`、`config.json`）は、許可なく変更しない**。一時変更をした場合は、必ず元へ戻す。
- **対話モードの許可ダイアログ**：「今回のみ」「この会話中は許可」「許可して設定へ保存」「キャンセル」の選択肢が出る。保存を伴う選択は、ユーザーの指示がある場合に限る。
- **環境変数の露出に注意**：フックのプロセスの環境変数には、利用者の認証情報の変数が含まれうる。調査でも、環境変数の一覧を出力・保存しない。
- **この環境の版**：作成時の確認は `agy` 1.2.14〜1.2.16（CLI）。IDE 版と 2.0 版は未確認。
- **ループ運転の `agy` バックエンド**：`agy -p=<プロンプト>`（引数渡し）。プロンプトが長い場合、コマンドライン長の制限に当たる可能性がある（未確認）。ヘッドレスではコマンド実行の許可が必要になる場合があるが、ループの応答 AI はツールを使わない前提。

---

## 9. 引継ぎの受入確認（受け手が行う）

以下を、**根拠（実行したコマンドと結果）つき**で報告する。できないものは「できない」と報告する。

| # | 確認 | 期待 |
|---|---|---|
| A1 | `git ls-remote --tags origin` と、渡された ZIP の有無を確認 | `v0.6.0` が `58fdca3`。**`v0.6.2` はない**（あれば Release の digest と ZIP を照合）。ない場合は「未公開」と報告し、ZIP で検収する |
| A2 | 渡された 0.6.2 の plugin ZIP の SHA-256 を、第2章 2.1 の値と照合 | 一致（違えば中止して報告） |
| A3 | Python 3.12 以上を確認し、77 テストを実行（`python -m unittest discover -s scripts -p "test_*.py"`） | 全成功（このホストは Python を実行できる前提のため**必須**） |
| S1 | **継続会話モード**：`references/continuous-loop.md` と `scripts/test_session.py` を読み、使い捨ての DB で `cic_session.py` の prepare → dispatch → complete を 1 巡し、`:stop` 後の prepare が停止扱いになること、新入力のあとの古い応答の complete が拒否されることを確認 | 期待どおり。hook の実機動作・Cloud Work の継続は**未確認**と報告し、動くと言わない |
| B1 | `skills/.../SKILL.md` と `references/operation-guide.md` を読み、第3章 3.1 の P1〜P7 を自分の言葉で要約 | 原文正本・origin と adoption の分離・意図と権限の分離・検証は正しさの証明ではない、を含む |
| B2 | 第7章の未解決事項を、自分の優先度と理由つきで並べ替えて提案 | 作成者の判断を要するものを区別している |
| B3 | 第4章 4.2 の不変の制約を、守れないケースの例とともに説明 | 4.2 の 1（ハッシュ）と 2（バージョン一致）を含む |
| D1 | `agy plugin validate .` | `skills` と `hooks` が processed |
| D2 | `agy plugin install https://github.com/ray-works-jp/conversational-intent-compiler`（またはローカルのクローン）→ `agy plugin list`、導入先の `plugin.json` の version | version 0.6.2（GitHub 未公開のため、marketplace 経由の導入はできない。その旨を報告し、展開した ZIP のディレクトリで代替できる範囲を示す）。`hooks : 1 processed` |
| D3 | skill が認識されることを確認し、`PLUGIN_ROOT` を直接のパス確認で解決して、一時 DB に `init` を 1 回 | `"ok": true`。許可確認は迂回せず（`--dangerously-skip-permissions` を使わず、「今回のみ」を選ぶ） |
| D4 | `CIC_CAPTURE=1` と `CIC_LEDGER_DIR`（使い捨て）で、`agy -p` を 2 回（`--continue` を使う）実行し、`ledger_status.py` で確認 | 2 ターンが逐語・順序どおり・重複なしで `pending` に入る |
| L1 | ループ運転（未確認事項の解消）：`python scripts/cic_loop.py --script <入力ファイル> --log <ログ> --compiler agy --responder agy`（入力は 3〜4 行＋`:stop`＋停止後の 1 行） | 入力の行数だけ処理され、`explicit_stop` で終わり、停止後の行はログに入らない。**`agy` のバックエンドは実モデルで未確認**なので、動いた／動かなかった（エラーの原文）を報告 |
| D5 | **IDE 版または 2.0 版が使える場合**、plugin フックが実行されるかを同じ手順で確認（未確認事項の解消） | 動いた／動かなかったを、根拠つきで報告。使えない場合は「未確認」のまま |
| C2 | 変更を提案する場合、影響範囲（テスト・manifest・README・hashed ファイル）と検証手順を先に示す | 第6章に従う |

**受入の合否**：A1〜A3、B1〜B3、D1〜D4 が根拠つき（L1 は未確認事項の解消のため、結果を報告）で満たされれば、引継ぎ完了とする。D5 は、環境が無い・許可が得られない場合は、理由を記録して未解決事項へ加える。

---

## 付録 A. コマンド早見
```text
python scripts/cic_cli.py --help
python scripts/cic_cli.py --db <DB> init --conversation <ID> --branch main
python scripts/cic_cli.py --db <DB> state --conversation <ID> --branch main
python scripts/ledger_status.py [--dir DIR] [--conversation ID]
python scripts/cic_loop.py --script <入力ファイル> --log <ログ> [--ledger <DB>] [--ab]   # ループ運転（明示停止: :stop）
python -m unittest discover -s scripts -p "test_*.py"
claude plugin validate .
agy plugin validate .
gh release view v0.6.0 --repo ray-works-jp/conversational-intent-compiler --json assets
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
- ループ運転：`docs/loop-ja.md`、`scripts/cic_loop.py`、`scripts/test_loop.py`、最初のコンパイラー `resources/intent-compiler/`
