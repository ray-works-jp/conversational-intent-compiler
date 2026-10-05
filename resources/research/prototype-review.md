# Prototype と主報告の独立レビュー

2026-10-04 JST。対象は `prototype/cic.py`、`schema_spec.py`、9個の出力schema、tests、fixture/replay、README、および主報告・benchmark protocol・Work接続表・systems evidence。レビュー担当は実装を変更せず、問題を実装担当へ連絡し、修正後を再確認した。本書だけを作成した。

**結論:** 現在のoffline試作について、宣言された決定論的契約のテストは通過した。自然言語の忠実性、意味上の許可、原文baselineに対する改善、Workへの自動挿入、実行中の外部操作停止は未検証または未実装である。実サービスのexecutorへそのまま接続できるという判断はしていない。

## 実行・成果物照合

Python 3.12.14 / Windows / SQLite、標準ライブラリの環境で、最終版に対して独立に `-B -m unittest -v test_cic` を実行した。

| 確認 | 結果 | 意味する範囲 |
|---|---|---|
| 最終contract suite | **45 tests、0 failures、0 errors、exit 0**。独立再実行のunittest経過時間1.586秒 | 手書きDeltaの決定論的適用・拒否・復旧契約 |
| 記録済みtest manifest | `test-results.json` の `cic.py` / `schema_spec.py` / `fixtures.py` / `test_cic.py` SHA-256が現ファイルと全件一致 | テスト記録と最終コードの同一性 |
| 9出力schemaとruntime定義 | 同一性テスト通過。レビューでもschema識別用metadataを除いた同一性を確認 | ローカルvalidatorが使用するschemaとの整合性 |
| Draft 2020-12の独立実装による検証 | **not_run**。`jsonschema` は利用不可、追加インストールなし | 完全なDraft 2020-12実装との互換性は未確認 |
| 10 / 30 / 100 human-turn保存済みJSONL | 別のin-memory台帳へ取り込み、最終コードのreplay hashが記録済みstate hashと全3件一致。exit 0 | 保存された台帳を現在の同じprojector版で再構築できる |
| 保存済みcheckpoints | 36 / 116 / 396 checksが全てtrue | fixtureで与えた解釈の期待状態。自然言語精度とは別 |

replay再確認では元JSONL・checkpoint・IRを更新していない。`replay-summary.json` の0.939 / 7.438 / 107.099秒は元のoffline harness実行記録であり、本レビューで全trajectoryを再生成して測り直した値ではない。LLM呼出しは0回。記録済みharness遅延をモデル/API遅延へ転用しない。

## レビューで発見し修正された項目

以下は修正前に再現した問題、または対象型を明示できないsubsetへの改善である。最終版では該当回帰テストと全suiteが通過している。

| ID | 修正前の問題 / 改善 | 修正後の契約 | 回帰test ID |
|---|---|---|---|
| RV01 | assistant根拠だけでuser explicit nodeをMODIFYし、user explicitの出自を保持したまま内容を変えられた | user explicitの変更とunknown RESOLVEにはtrusted user根拠を要求 | `test_assistant_cannot_rewrite_user_explicit_node` |
| RV02 | gateのstate version/watermarkが同じなら、時刻だけ進んで失効してもcurrentと判定した | `gate_is_current(..., now=...)` が新時刻でpreflightを再実行 | `test_gate_rechecks_clock_expiry_without_tick` |
| RV03 | Authorityの外側期限とscope期限の一方を採り、早い期限を無視した | tickは両期限の最小を採る。preflightも両方を確認 | `test_authority_scope_targets_and_earliest_expiry` |
| RV04 | 新たな未解釈の訂正入力があっても、旧human turnをpackageできた | pending humanが一件でもある場合、包装を止める | `test_stale_turn_packaging_blocks_on_new_pending_human` |
| RV05 | grantのscope.targetsに対象がなくても、明示target ID/versionの一致だけで許可した | scope.targetsと実対象の一致も必要 | `test_authority_scope_targets_and_earliest_expiry` |
| RV06 | 成功したunknown RESOLVE後も、role=unknownという理由で未決一覧に残った | resolution=resolvedはopen一覧から除外。resolvedをverifiedへ昇格させない | `test_resolved_unknown_leaves_open_set_without_becoming_verified` |
| RV07 | Referenceのresolved typeがないため、同ID/versionでtypeの違う候補を区別できない | このsubsetでは同ID/versionの複数候補を拒否し、型軸の限界をREADMEへ明示 | `test_reference_duplicate_id_version_is_rejected` |
| RV08 | 権限が有効でも、対象node自身の期限・task/turn scopeを別途評価する必要があった | preflightがresource自身のeffective期間・scopeも確認 | `test_resource_expiry_blocks_authority_before_tick` |

RV07の最終テストは重複node候補の拒否を検証している。node/artifact同ID/versionの衝突は同じ決定論的重複検査で拒否する実装を読んだ。artifactとnodeを自動で同一対象と解釈する機能はない。

## 重要契約の確認

| 項目 | 確認された挙動 | 証拠test / 残る限界 |
|---|---|---|
| AI提案の出自・選択・確認 | SELECTが全面CONFIRMへ変わらず、採用は別relation。AI仮定予算をuser explicitへ書換えない | `test_hokkaido_selection_does_not_confirm_budget_or_authorize_booking`、`test_explicit_confirmation_keeps_origin_and_target_fields`、`test_user_referenced_is_not_confirmed` |
| 権限根拠 | AI/tool/externalとuntrusted user envelopeからGRANTを拒否。intent opとauthority opは別 | `test_ai_tool_external_sources_cannot_grant_authority`、`test_untrusted_user_envelope_cannot_grant`、`test_authority_is_separate_from_intent` |
| 原文・source span | Unicodeコードポイント、CRLF、結合文字を正規化せず保持。引用・hash不一致と空根拠を拒否 | `test_raw_unicode_crlf_and_spans_are_exact`、`test_quote_mismatch_rejected_atomic_and_raw_remains`、`test_empty_evidence_rejected`。原ファイルbyte/BOM/PDF表現IDは未実装 |
| CAS・二重適用 | state versionとwatermarkの双方を確認。古い並行Deltaを拒否。同ID同内容は二重適用しない | `test_cas_version_and_watermark`、`test_parallel_connection_stale_delta_rejected`、`test_commit_retry_is_idempotent_after_other_events` |
| 撤回・依存・PASS | 撤回を記録し依存をsuspendedへ。PASSでもDelta処理。未解釈入力が既存gateを止める | `test_revocation_suspends_dependencies_and_cannot_silently_reactivate`、`test_pass_captures_and_applies_revocation`、`test_pending_revocation_blocks_gate_before_compile` |
| 分岐隔離 | fork時点の親watermarkを固定、親未来eventや別branchを根拠へ使わない | `test_branch_isolation_and_replay`。branch mergeは未実装 |
| replay / recovery | cache欠落・改変を検出しrebuild。観測tool結果を再実行しない | `test_cache_missing_detected_recovery_does_not_reexecute_tools`、`test_cache_corruption_detected_and_rebuilt`、`test_partial_tool_failure_is_observation_without_authority_or_reexecution` |
| 台帳の変更検出 | SQLite UPDATE/DELETE禁止、raw/hash chain検査 | `test_sqlite_ledger_update_delete_prohibited`、`test_tamper_detected_even_when_sqlite_trigger_bypassed`。管理者が全hashを書換えた場合の真正性保証はない |
| source / artifact欠落 | 欠落・hash変化をpacketで明示し、存在しない原文を補完しない | `test_missing_source_explicit_not_imputed`、`test_artifact_old_version_preserved_and_changed_content_detected`。独立blob保管と削除policyは未実装 |
| schema境界 | 未対応keywordを黙認せず拒否。boolをintegerとして受理しない。exportとruntimeを照合 | `test_schema_unsupported_keyword_extra_property_boolean_integer_rejected`、`test_exported_schemas_match_runtime_definitions`。opcode-specific domain検査はschema検査とは別 |

## 実行境界に関する未解決事項

1. **認証済み発話者は外部の前提。** `trusted_identity` とprincipalはPython APIの呼出し側が指定する。許可根拠のquoteがuser原文に一致することは、その文が実際に許可を意味することの証明ではない。原文内の引用命令、無関係なuser発話にGRANTを結び付けた候補、採用範囲の誤読を判定する意味検証は未実装。決定論的preflightのallowedを実サービスの意味上の許可として使用しない。
2. **raw captureの独立耐久保存は未実装。** captureと軽量projectionが同一SQLite transactionにあるため、capture中のprojector障害ではrawもrollbackする。成功したcapture後のinterpretation commit失敗ではrawが残る。この二つを区別する。adapterのdurable inboxと再送契約が必要。
3. **TOCTOUと実行中撤回は未解決。** gate取得後から外部操作開始までの競合、execution lease/fence、途中操作の停止、外部補償はない。tool statusは観測記録であり、実際の送信・予約を取り消す機能ではない。
4. **旧node revisionの再採用は未対応。** 過去Adoptionは対象versionを保持するが、後から旧node revisionをSELECT/CONFIRM/REFERENCEするresolverはなく拒否する。Artifact manifestsの旧version保存とは別。
5. **文脈取得の意味網羅性は未検証。** callerが選ぶgoal/preference、有限閉包、全件のreferences/authoritiesという実装。coverage=1.0は宣言されたrequired-event集合の取得率であり、原文から必要な全制約を見付けた割合ではない。
6. **性能・保存・migrationは試作範囲。** 全台帳再検査により100-turn fixtureは約107秒を要した。暗号化、retention、削除、再解釈版の選択、schema migrationはない。production容量や機密会話を受け入れる基準ではない。

READMEはこれらを明示している。自然言語Compiler、semantic verifier、adaptive routing、human clarification、host接続は設計契約の段階であり、未実装を最終テスト成功へ含めていない。

## 主報告・評価設計との整合

主報告は原文baselineに対する優位性を未証明と述べ、研究結果・設計推論・offline実装を分離している。完全設計のdurable captureとprototypeの同一transaction実装の差も追記された。Workの毎ターン自動介入、モデル比較、closed-loop、実executor cancellationを実現済みとは報告していない。架空の自然言語精度・改善率・API費用は見当たらなかった。

benchmark protocolでは、固定履歴ReplayとClosed-loopを分け、A–Eへ同じ原文・成果物・toolアクセスを与える。応答に応じた番号・参照を生成するuser policy、曖昧さに対する許容解釈集合、会話単位のbootstrap、blind評価とhuman裁定、総予算と下流予算の二つの比較を設計している。216 trajectories / arm、閾値、試行数は事前登録**案**であり、実測データではない。重要な改善指標だけでなく、明確依頼の非劣性、確認負荷、費用・遅延も含む。

今回の検証は、基盤実装の具体的な欠陥を修正し、再現できる契約を増やしたという範囲で報告できる。Conversational Intent Compiler全体が原文直接入力より良いという判定には、別途、自然言語Delta生成・文脈取得・意味検証・下流行動を含むA–E比較が必要である。
