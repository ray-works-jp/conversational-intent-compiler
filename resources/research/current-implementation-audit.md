# 現行 Intent Compiler 0.2.0 実物監査

監査日: 2026-10-04（Asia/Tokyo）。調査対象はインストール済みプラグインの読み取りと、別ディレクトリでの静的 validator 検証。元プラグイン、ホスト設定、既存成果物を変更していない。

## 結論

現行実装は **ホストAIが単発のXML解釈メモを生成し、Pythonが入力抽出・静的検証・別名保存を行う明示起動型Skill** である。原文優先、委任/未決の保存、引用命令の隔離、原入力の別添、元依頼を実行しない境界を規定する。永続的な会話台帳、再構築可能な状態、ターンごとのDelta、AI提案の採用履歴、権限の失効、全ターン挿入、下流AIの自動起動はこのパッケージに存在しない。

文書中の `basis` は記述的命題のローカル集合であり、vNextの Immutable Event Ledger と同一ではない。設計文書の「これなら幻制約を作れない」等の表現は実測による保証ではない。引用が実在するだけでも、その引用と反対の制約・資料内命令のユーザー指示への昇格が validator を通過することを本監査で確認した。

## 実際に読んだ資料

対象ルート（以後 `P`）:

`C:\Users\HP\.codex\plugins\cache\created-by-me-remote\intent-compiler\0.2.0`

通常のファイル一覧では隠し `.codex-plugin/plugin.json` が除かれたため、再帰ファイル列挙でも確認した。10ファイルを全文読了した。長い設計原本は588行を分割して読み、出力の切り詰め部分も再読した。

| 相対パス（P基準） | 種類 | 読了 | SHA-256 |
|---|---|---|---|
| `skills/compile-intent/SKILL.md` | 現行Skill実行境界・文書入出力 | 全文 | `6348526a2450f976831b1f6462c05c4adff007b33bd9d1fd0fdba4d9f654bccf` |
| `skills/compile-intent/references/original-design.txt` | 元の単発設計の保存コピー、著者未確認 | 全文588行 | `8268db34ae676556c45db50562a464d471d039db8d979813a3deafbbd8266d21` |
| `skills/compile-intent/references/system-prompt.md` | ホストAIによる意味解釈の現行仕様 | 全文 | `9864669090e5d8900915f34f717d4ec395a713610bbcb7d70c8e86bfcedd416a` |
| `skills/compile-intent/references/integration-notes.md` | 原設計からの変更・組み込み判断 | 全文 | `33caa9eb0a2815d41e0a391dd0143f67775e5cc26b7f226b6d2f0b7e2eccb523` |
| `skills/compile-intent/references/examples.md` | 出力例、実モデルの実行結果ではないと明記 | 全文 | `dde634d449f2c1655b7ff8f9ce8db594353ee3b59ceb07e13bce3785ce51e4d4` |
| `skills/compile-intent/references/document-io.md` | 抽出・検証・別名ファイル出力の利用法 | 全文 | `bc4749f878599523fe0bca3b707dfc47119108e4f06b3cb59f48efc308549a8d` |
| `skills/compile-intent/scripts/document_io.py` | 実行可能な抽出/静的validator/出力、244行 | 全文 | `8d51b901abd3f4419463359703ce502b5855af1088b7fc1f26bef755a5cc8902` |
| `plugin.json` | プラグイン紹介・起動プロンプト | 全文 | `78b79159c95fd3c441e287cd4c8cae2f27cc8316ae58ac14cf17eb6c56d881ce` |
| `.codex-plugin/plugin.json` | Codex向けパッケージ情報 | 全文 | `98ad4afbcbc7714b9facc2cc9fdfa65de68e96a0a450b4b44c11f94ab7c4b4e1` |
| `assets/icon.svg` | アイコン | 全文 | `4d83d223b08cba9f5a7dbc1edb648dba7592fec3da65689107dfa8739561d7a7` |

個別の絶対パス・サイズ・読了状態は同じ出力フォルダーの `material-inventory.json` に記録した。ハッシュは監査対象の識別と変更検出用であり、内容の真実性・著者・権威の証明ではない。

今回の長いMissionは直接のユーザー原文であり、上記設計資産や引用された命令と別の権威を持つ。`original-design.txt` は存在するが、それと「旧Work指示書」を同一とする根拠はない。独立した旧Work指示書、別添の会話改訂方針、現行IRのXSD/JSON Schema、自動テスト群、実モデルA/B結果は調査パッケージ内に存在しない。全ディスクでの不在を主張するものではない。

## 文書仕様・コード挙動・未確認の分離

| 論点 | 文書で規定される現行仕様 | 実コードで確認できる挙動 | 未確認 / vNextで補う項目 |
|---|---|---|---|
| コンパイル | ホストAIがXMLを生成、元依頼は実行しない | PythonにLLM/API呼出し・意味コンパイルなし | ホストAIの忠実性・下流成功率 |
| 原文 | 正本、長いrawを省く場合も原入力を別添 | `requires_source` が真なら `.source.txt` を別名で保存 | 原文発話者、範囲、後続訂正、引用出自 |
| PASS | T0は `<pass/>`、ファイルと原入力を返す | `pass` は属性/子/実質本文なしのみ、source要求 | PASSでもイベント記録・撤回検出する処理 |
| 委任 / 未決 | `latitude` と `open`、`unknown` を分離 | タグの親子関係とunknownの属性値を検査 | 意味上の区別、長期間の維持、変更範囲 |
| 出自 | 要求にsrc/strength、命題に型を付ける | `src=u` のq実在、mustのsrc制約など | AI提案→ユーザー採用の独立イベント関係 |
| 権限 | IR記載はスキル自身の実行許可でない、既存承認は範囲一致なら維持 | 外部副作用を行うコードがない | 許可オブジェクト、最新権限、取消・失効・実行直前検査 |
| 参照 | 見える履歴・添付だけを候補にする | step afterの解決/循環を検査 | 会話/成果物ID、対象版、複数候補、採用範囲 |
| 状態 | 任意の見える文脈を解釈に利用 | 状態ストア/投影/Delta/replay/branchなし | vNextの4表現と競合・再解釈 |
| 検証 | 機械検証とホストAIの意味監査を区別 | 部分的なXML lintのみ | source支持、否定、要求網羅、権限・遷移検証 |

actor/action/object/goal/deadline/time range/quantity/sequenceの専用構造は、現行パッケージの語彙・Python定義に一式として存在しない。goal/steps/out等に自然文で載せられるが、その保持と意味検査は実装されていない。ユーザーが述べた「旧仕様」のこの部分は、独立した旧Work資料なしには現行確認済み仕様へ昇格させない。

## 原設計と現行仕様の重要な差

`integration-notes.md` は、原設計の§13をベースにしつつ、XML特殊文字を標準エスケープで保持する、重要仮定を隠すquietを採らない、既存承認は対象/範囲/影響の一致を要求する、trust=userを資料提供の出自に限定する、原入力を別添する、と説明する。従って原設計だけを実行仕様の代用にしない。

原設計の例には、Linuxの決め打ち、固定readの省略表示、複合的 `from="q:... ctx:..."` 等があり、現行指示や現validatorと整合しない例が混じる。例は既存実装の性能証拠ではない。

## Validator の実装範囲

`document_io.py:117` 以降を直接読んだ。決定論的に検査するものは次の通り。

- DTD / ENTITY / CDATA禁止、XML構文、ルート `pass` / `ir tier=1|2|3`、空IR禁止。
- 許可された親子関係、ルートからの深さ3、ID重複。
- `src=u` のqが入力中に実在する部分文字列であること、rawが入力中の部分文字列であること。
- `must` は `src=u|sys`、`src=d|conv` はpreferまで。constraint strengthの3値。
- infer from、assume if_wrong、unknown need/handle、lookup via、constraint src/strengthの存在。
- unknown need/handle、lookup viaのenum、forkのhypo 2個以上とresolve。
- infer fromが `q:` で始まる時だけ、後ろ全体の文字列が入力に実在すること。
- step afterの対象存在・循環・afterを持つstepのID、T2/T3の固定read一致。
- `emit` は既存の出力/入力/XML候補を上書きせず、rawが原入力全体と等しくなければsourceも保存する。

検査しないものは、支持関係、制約網羅、数量/主体/日付の忠実性、否定、資料の引用者、一般的なsrc値や属性の許可リスト、一般ID参照、infer連鎖長、check by必須、data trust、gate/limitの妥当性、latitude/openの意味、unknown内の推測、factの観測根拠、権限生成・失効、会話状態遷移である。引用一致を意味の正しさと表現しない。

実装上の補足: 原入力はbytesからdecodeするが、XMLパーサーは改行を正規化する。そのためCRLFを含むraw全体の照合が失敗する場合がある。emitのXML/sourceの複数ファイル書込は単一トランザクションではなく、後半の書込失敗で部分成果物が残り得る。DOCX抽出は削除変更を除き、段落/表/ヘッダー/フッター/脚注/末尾注を読むが、Wordコメントは対象一覧にない。PDF抽出・OCR・DOCX視覚表示は今回実行していない。

## 実行した小検証

Bundled Pythonで現行utilityを `runpy.run_path` により読み、モデルを呼ばず18ケースの静的境界を検証した。18/18が予測した受理/拒否境界と一致した。これは意味正確性18/18という結果ではない。既存テストの実行でもない。新しく作った監査用probeである。

| 検証群 | 実観測 |
|---|---|
| PASS、エスケープraw、正しい引用 | 受理 |
| 存在しないq、derived must、if_wrong欠落、step循環、T2 read欠落、DTD | 拒否 |
| 「必ず残して」をqにして本文を「全て削除」へ反転 | 受理。引用実在は支持検査でない |
| 原入力の「引用資料: 全部削除せよ」を `src=u` 制約へ転用 | 受理。発話者/引用境界の検査なし |
| 存在しない一般infer根拠ID、未知属性、根拠なしlatitude/fact | 受理 |
| check by欠落、unknownの推測混入 | 受理 |
| CRLF原文raw、qにctx文字列を同属性内連結 | 拒否。raw改行規約・from文法の整合性課題 |

再実行用の作業ファイルは `work/audit/probe_current_validator.py`、詳細は `work/audit/probe-results.json`。意味監査や実モデルA/B、下流tool arguments、長期対話、権限遵守、latency/costは測定していない。

## Codex CLI / App-server の限定的な追加調査

現行npmパッケージ `C:\Users\HP\AppData\Roaming\npm\node_modules\@openai\codex\package.json` はバージョン0.155.1を持つ。`codex app-server --help` と `generate-json-schema --experimental --out work/audit/appserver-schema` はexit 0。実物バイナリから437個のJSON schemaが生成された。これはプロトコル宣言の確認であり、運用中の自動介入の実証ではない。

| 確認対象 | 実物で確認した宣言 | 運用評価 |
|---|---|---|
| `v2/TurnStartParams.json` | `threadId`, `input`, `clientUserMessageId`, `additionalContext` | 対象propertiesを読んだ。実turn/start未実行 |
| `v2/ThreadReadParams.json` | `threadId`, `includeTurns`。paginated readへの移行注意書き | 全文を読んだ。履歴原文の完全性未検証 |
| `ClientRequest.json` | `thread/read`, `hooks/list`, `turn/start` | 対象methodを検索。全ファイル読了とはしない |
| `ServerNotification.json` | `turn/started`, `hook/started`, `hook/completed` | 対象eventを検索。全イベント取得未検証 |
| Hook notification / list schemas | enum `userPromptSubmit`, `preToolUse`, `postToolUse`, `sessionStart`, `stop`、thread/turn ID等 | 対象定義を検索・抜粋。hook未設置 |
| `codex features list` | 今回のシェルでhome解決失敗、exit 1 | 有効feature一覧は未取得 |
| host configのhooks真偽値だけの限定読取 | 裸の `hooks=true|false` 行は見つからない | effective hooks設定・他section/managed設定は未確定 |

CLI宣言・公式仕様・このチャットのコネクタ機能・ChatGPT Work cloudを別に扱う。宣言からWorkクラウドや現在の会話への全ターンhookを推定しない。自動hookを設置/有効化したり、設定を書き換えたり、app-serverを起動したりしていない。スキル/プラグインの存在も自動挿入の証拠にはならない。

## vNext の再評価に渡す優先事項

1. 現行の原文優先・委任/未決・外部命令隔離・下流の推論余地を維持する。
2. basisを会話台帳と混同せず、immutable raw events / derived state / delta / turn packageを別契約にする。
3. qの実在に加え、event ID・span・発話者・採用関係・支持/矛盾/不明を検査する。
4. PASSでも撤回・参照・権限の軽量検出とイベント記録を続ける。
5. 既存承認の範囲を保存し、外部副作用前の最新状態検査を実行レイヤーに置く。
6. 現行Bを実物prompt+utilityで評価し、資料からの模倣やfixtureに現行実装というラベルを付けない。
7. 独立した旧Work指示書の未提供部分はunknownとして残し、現行確認仕様へ推測で足さない。
