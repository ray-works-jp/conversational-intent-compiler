# Conversational Intent Compiler — offline contract prototype

この試作は、手書きの intent delta を原文イベント台帳へ適用する **決定論的な基盤の最小実装**です。自然言語理解、意味検証、適応的な routing、Work への毎ターン自動挿入は実装していません。LLM・API・外部操作の呼出しはありません。schema 検証の通過、引用一致、fixture テストの成功は、意味解釈の正しさや原文 baseline に対する改善を証明しません。

## 再現

Python 3.12 以上、標準ライブラリのみを使用します。確認環境は Python 3.12.14、Windows、SQLite。`jsonschema` は環境にありませんでした。追加インストールしていません。

このフォルダーで実行します。

```powershell
python schema_spec.py
python -m unittest -v test_cic
python run_tests.py --output results
python run_replay.py --lengths 10 30 100 --output results
```

この Codex 環境の Python は次のパスです。

```powershell
& 'C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest -v test_cic
& 'C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' run_replay.py --lengths 10 30 100 --output results
```

`results/replay-summary.json` が実測結果です。`hokkaido.events.jsonl` と `hokkaido.turn_ir.json` は必須の旅行例の原文台帳と IR。各長さの events/checkpoints/final_ir も保存します。長さは **人間ターン数**であり、AI・tool・解釈イベント数ではありません。

実行記録: 最終 contract suite は **45 tests / 0 failures / 0 errors**。`results/test-results.json` と `.txt` に実行結果と対象 source hashes を保存しています。

| human turns | events | 期待状態の checks | replay 一致 | 当該 offline harness wall time |
|---:|---:|---:|---|---:|
| 10 | 20 | 36 / 36 | 一致 | 0.939 s |
| 30 | 60 | 116 / 116 | 一致 | 7.438 s |
| 100 | 200 | 396 / 396 | 一致 | 107.099 s |

この wall time は全台帳 integrity 再検査を繰り返す試作の実費用です。モデル遅延ではありません。最後の修正は authority の事前検査・unknown 解決・pending input guard の回帰テストであり、上記 trajectory の delta や投影結果は変更していません。最終 code は更新後の contract suite で検証しました。

## 実装の責務

| ファイル | 内容 |
|---|---|
| `schema_spec.py`、`schemas/` | Event / State / Delta / Turn IR / Artifact の独立 schema と Node / Adoption / Reference / Authority の補助 schema |
| `cic.py` | SQLite append、原文保存、決定論的 schema/evidence/transition 検証、純粋 reducer、CAS commit、branch replay、context packaging、read-only authority preflight |
| `fixtures.py` | 手書き解釈と期待状態。モデルの出力ではない |
| `test_cic.py` | 原文・出自・採用・撤回・scope・権限・競合・復旧・失敗経路の契約テスト |
| `run_tests.py` | テスト結果 JSON / text と対象 source SHA-256 の記録 |
| `run_replay.py` | 10 / 30 / 100 human-turn の fixture replay。A–E モデル比較は未実施 |

## 保存・状態・commit 契約

1. `capture` で raw human event を先に保存する。raw は Unicode の文字列を UTF-8 としてハッシュ化し、改行・結合文字を正規化しない。source span は Python `str` のコードポイント位置、`[start,end)`。未対サロゲートを拒否する。UTF-16 unit、grapheme cluster、UTF-8 byte offset ではない。
2. 原文の捕捉時点で `pending_human` と state version / watermark を更新する。後続の人間入力が一件でも未解釈なら、旧ターンの包装と副作用 preflight を止める。これは安全寄りの簡易 fallback であり、独立作業を細分化して進める機構は未実装。
3. hand-authored delta は捕捉後の `base_state_version` と `base_watermark` を指定する。`commit` が `BEGIN IMMEDIATE` 内で CAS、出典・操作検証、interpretation event の追記、state cache 更新を行う。失敗した commit はすべて rollback し、先に保存した人間原文は残る。
4. 各原文・観測イベントも SQLite transaction 内で projection と一緒に追加する。projection は raw と採用された解釈イベントから再構築できるキャッシュ。意味解釈イベントは raw を置換しない。
5. event ID と request fingerprint が同じ再送は二重適用しない。同一 ID で異なる内容は拒否する。commit も delta ID に基づいて同様に動く。timestamp は記録時刻を新規発行するが、再送の fingerprint は呼出し引数を対象とする。
6. `replay` はイベントを投影するだけで、外部操作を呼ばない。tool status は観測のまま保持する。`rebuild` は replay で cache を再保存するだけ。

raw capture 自体も projection と同じ transaction にあるため、capture 中の projector 障害では raw も rollback する。先に入力アダプターの独立した durable inbox へ保存してから投影する構成は未実装。失敗時の再送契約と event ID の再利用が必要。

Ledger UPDATE / DELETE を SQLite trigger で拒否する。raw hash と event hash chain で変更を検出するが、管理者が DB と hash をすべて書き換えた場合の真正性を保証しない。ハッシュは権威や真実性の証明ではない。本試作には retention、暗号化、ユーザー削除、監査署名、アクセス制御、privacy tombstone は実装していない。したがって機密会話の本番保存先としては使わない。設計上は raw を暗号化 blob に分離し、保持期限と削除通知を append して、再構築可能性の欠落を明示する必要がある。

## 出自・採用・指示変更

Node の `origin` と `relation` は、採用によって user に書き換えない。`SELECT` と `CONFIRM` は独立した Adoption を作り、対象 ID、対象 node version、fields、exceptions、任意の artifact version、人間の evidence を保存する。参照は Reference であり、確認・選択・権限を生成しない。

`MODIFY` では元の origin を保存し、変更を根拠へ追加する。user explicit node の変更には trusted user envelope の根拠が必要。引用された命令が user の raw に含まれるだけで、その内容が許可を意味するかは決定論的には判定できない。`trusted_identity` と `principal` は adapter が認証済み transport から設定すべき境界であり、この Python API の boolean を認証機構と見なしてはならない。意味上の採用範囲や許可は候補生成者・意味検証者の責任であり、今回未検証。

| 操作 | 実装範囲 / 拒否条件 |
|---|---|
| ADD | source 付き active v1 node の追加。同 ID は拒否 |
| MODIFY | active node の content / semantics / resolution だけ変更。origin 等は変更禁止 |
| REVOKE / SUSPEND / COMPLETE | lifecycle を変更。依存する active node は保守的に suspended にする |
| REPLACE / SUPERSEDE | 旧 node を superseded として残し、新 node を追加。依存を自動で新版へ付け替えない |
| CONFIRM / SELECT | 人間根拠と対象 version、fields 必須。旧版への採用を新版へ自動拡張しない |
| REFERENCE / RESOLVE | 明示された候補と version を検証。最新候補を機械的に選択しない |
| REOPEN | revoked / suspended / completed / expired を人間根拠で active 化。依存条件の不整合なら拒否 |
| DELEGATE | latitude node の作成。権限を作らない |
| NARROW_SCOPE / EXPAND_SCOPE | finite target-set の包含関係だけ判定。空集合は全対象。時間・task / turn kind の変更は拒否し REPLACE を要求 |
| NO_CHANGE | 意味変更をしないが、人間イベントを記録・解釈済みにする。PASS でも撤回等の delta を処理する |

Node は actor / action / object / goal / deadline / time_range / quantity / sequence の構造化 slots を持つ。business-domain object の詳細は本試作では opaque JSON。数量は value、unit、任意の comparator / epistemic。日時 slot の意味比較は未実装で、scope / authority の有効期間だけ ISO 8601 + timezone を検証する。

依存は node ID 単位で、循環・参照先欠落・inactive 親を持つ active 子を拒否する。変更・撤回時には依存子を suspend し、人間／意味解釈者の明示的な修復を待つ。フィールド単位依存と自動再計算は未実装。

## Authority と実行前境界

Intent operations と authority operations は別配列。GRANT / REVOKE / NARROW / EXPIRE に trusted human source と principal の一致が必要。GRANT は actor、action、target ID / exact version、conditions、期間、scope を保存する。NARROW は条件追加と期限短縮だけを許可し、target/action の変更や権限の拡張は拒否する。

`preflight(..., now=...)` は actor/action/target version、active 権限、scope の targets / task / turn、両方の有効期間、与えられた条件、未解釈の人間入力、行動差を持つ未解決参照、projection integrity を確認する。最新 IR 内の許可を再利用するだけではない。`gate_is_current(gate, now=...)` は state version と watermark の一致に加え、新しい時刻で preflight をやり直す。権限の一部条件や外部情報の真正性は与えられた値以上を証明しない。

本試作は一切の副作用を実行しない。gate が返った直後から外部 API が動くまでの TOCTOU は **未解決**。本番では execution lease / fence、未実行ステップ停止、revoke シグナル、executor の直前再確認が必要。すでに送信・購入・予約されたものは、会話の撤回だけでは取り消せない。tool 完了・実行中・未実行の記録と外部補償手順を別途設計する。

Authority の target は本試作では **現在の node revision**だけに限定する。artifact / event を直接許可対象にする型は未実装。対象 node 自体の期間・task / turn scope も preflight で評価し、有効期間外を拒否する。許可が構造的に適合しても、raw 本文がその操作を意味的に許可していることは今回検証していない。

## Branch、時刻、成果物

Fork は親 branch の watermark と state hash を固定して記録し、その後は子 branch の追記へ隔離する。親の未来イベントや sibling branch は参照できない。fork 時点に未解釈の人間入力がある場合は、本試作では拒否する。branch merge は未実装。

clock を暗黙に読みながら projection しない。期限の lifecycle 反映には明示 `tick` イベントを保存し、同じ ledger と projector version から同じ状態を replay する。preflight / packaging は明示 now を用いて tick 前でも期限を評価する。古い時刻の tick と timezone 無しを拒否する。

Artifact は安定 ID + version + source event + 絶対 path + bytes hash を記録する。旧版を採用しても新版へ置換しない。包装時は path の欠落と hash 変化を known omissions に出す。本試作の path は immutable blob store ではなく、外部変更による内容消失があり得る。

node の変更履歴は解釈イベントと replay prefix に残るが、API は current revision の node を返す。古い node revision を後から SELECT / CONFIRM / REFERENCE する snapshot resolver は未実装で拒否する。過去に記録された Adoption の旧 target_version は保持する。artifact manifests は複数 version を保持する。Reference の候補で同じ ID / version が複数 type に重なる場合は、resolved type の型を持たない subset として拒否する。

## Context と未決事項

Turn IR は今回 raw + delta + 選択 node + 現在有効な constraint / prohibition / latitude / unknown + 依存閉包 + 採用関係 + 参照 + 権限境界 + artifact manifests + 原文抜粋 + coverage / omissions を含む。過去 IR の要約を次の唯一の入力にしない。

selector は小規模な保守的閉包で、embedding retrieval や意味検索を実装していない。preference / goal は caller が node IDs を指定する必要がある場合がある。authority と reference は全件を渡すため長期会話で肥大化し得る。原文がない場合 `missing_event_ids` と `missing_sources` の `retrieval_status=unavailable` を返す。deleted と not_provided の status は schema の余地として存在するが、削除記録がない限り deleted と推測しない。未解決意味は references / unknown の別軸で保持する。

coverage は **宣言された required-event 集合**の取得率であり、必要な全意味条件を取り出せたことの証明ではない。raw の複製だけで overlay の忠実性を判定していない。本試作の semantic field は常に not_run / unverified。

## Schema validator の範囲

出力 JSON Schema は Draft 2020-12 の core で表せる構造です。同梱 validator は次の vocabulary だけを実装します。完全な Draft 2020-12 validator ではありません。

`$schema`, `$id`, `type`, `properties`, `required`, `additionalProperties`, `items`, `enum`, `const`, `minimum`, `maximum`, `minLength`, `pattern`

未対応 keyword は、未使用の property 下にあっても拒否します。外部 schema の `$ref`、format、conditional、unevaluated、anyOf 等は未対応。生成 schema と runtime 定義の同一性をテストしています。Op value / patch は JSON で受け、opcode-specific runtime checks が厳密な対象 node / adoption / reference / authority schema へ検証します。単なる Delta schema 通過では、適用可能性を保証しません。

原 byte stream / BOM、PDF 原本と抽出表現の stable representation ID / extractor version は未実装。raw は入力された Unicode 文字列を保存する subset。完全な原ファイル保存契約とは区別する。

## 未実装と評価の限界

自然言語 Compiler / reference resolver / semantic verifier / adaptive router / multi-hypothesis policy / human clarification / Work hooks / private storage / schema migration / execution lease は interface 契約・研究設計の段階です。未対応 schema/compiler version は migration せず拒否します。再解釈版の並列保存・選択切替も今後の実装です。

各 append で台帳全体の integrity と replay を再検査する簡易実装なので、production 性能・大量会話・1000+ turns の基準には使えません。A–E の同一下流モデル比較、closed-loop、モデル自然言語 accuracy、token / API cost、確認負荷、human adjudication、raw baseline に対する優位性は未測定です。単一シードの fixture 結果へ統計的改善率を付けません。

fixture 契約テストとモデル評価を区別し、モデル候補は別の評価 harness で記録・採点してください。本番移行前に、少なくとも「引用一致だが意味が誤った候補」「user raw 内の引用された許可命令」「文脈欠落」「依存の部分更新」「実行直前の撤回」を意味検証・実環境で追加評価する必要があります。
