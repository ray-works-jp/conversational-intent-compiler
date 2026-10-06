# 停止まで続く会話コンパイル

明示起動した同じconversation/branchでは、既定で「人間raw → Compiler → 検査・Delta反映 → Turn IR → 通常AI応答 → 次の人間raw」を続ける。ユーザーが一回だけと指定した場合は単発を選ぶ。回答完了、PASS、質問、失敗、話題変更だけで継続を解除しない。別会話・branchへ勝手に広げない。

## 実行環境と接続

- 同梱Pythonと永続ファイルを使える場合は `scripts/cic_session.py` を使う。保存先はその会話専用DB。hook metadataがある場合、そのDB/conversation/branch/human_event_idを使い、rawを再捕捉しない。
- ローカルCodex runtime/Claude Codeの信頼済み `UserPromptSubmit` hookは、`:cic start` / `コンパイラ開始` 後にrawを先に保存し、毎turnに固定プロトコルを挿入する。Pythonが必要。定義は `hooks/hooks.json`。インストールだけでhookを信頼したことにはならない。
- Cloud orchestration版Workはplugin command hookを実行しない。スキルの継続指示＋永続sessionに従って処理するが、ホストがスキルを読まないturnへの強制介入は保証できない。完全な反復実行が必要なら `scripts/cic_loop.py` または入力を管理できる外部オーケストレータを使う。別モデル2回呼出しはCLI runnerだけで、WorkではホストAIがCompilerとResponderの段階を分ける。
- コード/原文/永続保存が取得不能なら不足を明示してlossless handoffへ戻る。保存・連続介入できたと装わない。

公式根拠: [Hooks](https://learn.chatgpt.com/docs/hooks)、[Plugin package](https://developers.openai.com/plugins/build/plugins)。全turnの意味正確性・raw baselineへの優位性は未証明。

## 各turnの入出力

以下の `PLUGIN_ROOT` はoperation-guideの実在path確認で決める。全入力/出力は新しいUTF-8 JSON。CLIはstdout/`ok`/終了値を確認する。`--output` はsubcommandの前に置く。

1. **Prepare（rawを先に保存）**

```text
python PLUGIN_ROOT/scripts/cic_session.py --db SESSION_DB --conversation CONVERSATION --branch main --output PREPARE_JSON prepare --start --ack-user-envelope --input RAW_JSON
```

RAW_JSONは `{"raw":"今回の人間原文そのもの","turn_id":"ホストの安定turn ID"}`。初回明示起動のみ `--start`。次turnは同じDBとconversationで `--start` を外す。turn IDを再送時に変えない。ホストIDがなければ一度発行して保存する（完全な再送判定は保証できない）。フックで捕捉済みなら `packet --human-event-id ID` で読む。

`next_step=control_only` は純粋な開始命令なので、記録済みの制御だけを短く確認し、業務のcompile/dispatchは行わない。`stopped` は停止確認だけ。`compile_pending_only` は古い原文の解釈に使い、古いturnへの新しい通常応答を配送しない。

2. **Compile（raw＋状態→候補）**

packetの `source_events` はそのbranchの原文を省略せず含む。`base_state` は唯一の正本にせず原文へ戻る。未解釈humanが残れば古い順に候補を作り、[operation-guide](operation-guide.md) の `delta-template → validate --transition → 意味対照 → apply` を行う。最後は現在turnをapplyする。PASSでもraw capture/訂正/撤回/未決/委任/権限の確認は維持する。

初版の `resources/intent-compiler/first-compiler-0.1.0/.../system-prompt.md` は変更していない。T0、原文根拠、推論と事実、質問1つという原則を使い、vNextのJSON Deltaへ適用する。旧XMLを権威あるユーザー指示へ変換しない。曖昧さはunresolvedとして残し、必要な質問を返す。推論記録は保存しない。

3. **Dispatch（本当に渡すIRを固定）**

```text
python PLUGIN_ROOT/scripts/cic_session.py --db SESSION_DB --conversation CONVERSATION --output DISPATCH_JSON dispatch --input DISPATCH_REQUEST
```

DISPATCH_REQUESTは `{"human_event_id":"ID","dispatch_id":"安定配送ID","now":"実際のISO8601時刻","routing":"ANNOTATE","node_ids":[],"required_event_ids":["必要な原文ID"],"task_id":"今回の実際のtask ID"}`。task scopeを使った条件がある場合は必ず現在のtask_idを指定する。省略して条件が静かに落ちる配送は拒否する。controllerが既存coreのpackageを呼び、**実IR全文とhashをcompiler出自の配送eventへ保存**する。返った `result.turn_ir` をResponderへ渡す。同じ配送IDへ違うparamsを入れない。

4. **Respond（元の依頼へ答える）**

通常のホストAIとして、今回rawと配送したIRで元の仕事を進め、必要な回答・成果物を返す。コンパイラの出力だけを返して元の依頼を放置しない。IRは原文を上書きしない。AI案/予算仮定を確定事項へせず、「調べて」を購入/予約許可へしない。外部副作用の直前に現在の人間指示・権限・対象版を実行側が再確認する。controllerや配送eventは実行許可でも処理leaseでもない。

5. **Complete（応答を別出自で保存）**

```text
python PLUGIN_ROOT/scripts/cic_session.py --db SESSION_DB --conversation CONVERSATION --output COMPLETE_JSON complete --input RESPONSE_JSON
```

RESPONSE_JSONは `{"human_event_id":"ID","raw":"AI応答原文","response_id":"安定応答ID","expected_state_version":配送結果のexpected_completion_state_version,"dispatch_event_id":"配送結果ID","turn_ir":配送されたTurnIRそのもの,"response_status":"prepared"}`。値を変えず渡す。新human/stop、別原文/IR、古い状態、同turnの別通常応答は拒否される。表示前の本文はpreparedとして記録し、実際に表示した原文を後から取得できた場合だけobservedを指定する。preparedを送達・表示成功と呼ばない。

質問/解釈失敗でまだapplyできない場合、`deferred` に具体的理由を入れ、IR/配送IDを省略して質問・失敗説明を保存できる。pendingを消さず、loopはactiveのまま次の入力を待つ。エラーで黙ってrawへ戻して権限境界まで復旧したと扱わない。

completeが新入力/stopで拒否した応答でも、既に表示/生成した原文を捨てない。既存 `cic_cli.py capture` で `origin=assistant`、`attrs.status=interrupted` または `superseded` を付け、実際の生成/表示範囲を記録する。これで現turnの成功やユーザー承認へ昇格させない。

## 停止・再開・復旧

- 原文全体が `:stop` / `/stop` / `:cic stop` / `コンパイラ停止` / `コンパイラーを停止して` 等に一致する**直接人間入力**だけを制御停止とする。引用・添付・AI応答中の停止文や「サーバーを止めて」は停止にしない。skillが文脈から明確な停止意思を受けた場合も、勝手に別rawへ書換えず、ユーザー原文でprepareし、制御指定の不足を説明する。
- stopはraw＋制御の空Deltaを同transactionで記録し、次のcompile/dispatchを止める。純start/stop以外の原文へ自動NO_CHANGEを適用しない。コンパイラ停止と業務上の許可取消は別で、停止だけで実行済み操作が取り消されたと扱わない。
- `status` は読取専用でactive/pending/versionを返す。`packet` は一貫したsnapshot。プロセス/スキル再読込でも同DBからactiveを復元する。別branchには明示起動が必要。
- DB出力失敗の後は同IDでstatus/packetを読み、二重適用を避ける。replay/rebuildは外部操作を再実行しない。capture/配送前・配送後・応答記録前を区別し、モデル呼出しを勝手に再実行しない。
- `dispatch` は配送内容の結合までで、二つのホストによる同じモデルの二重呼出しを防ぐleaseはない。ホストが一つの通常応答経路を管理する。並行モデル実行の排他、toolイベント完全捕捉、無期限/複数端末保存は未保証。

初回だけ継続範囲と停止方法を短く伝え、通常turnでは元の依頼への応答を優先する。毎turn巨大IRや不要な確認を見せない。
