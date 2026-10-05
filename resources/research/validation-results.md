# 検証結果と未実施事項

2026-10-04 JST。これは現行実装の静的監査、offline状態管理試作、評価集計器の検証記録である。**原文直接入力に対する意図精度・最終成功・費用の改善は未測定、優位性は未証明**。自然言語Compiler/Verifier・モデルAPI・Work自動挿入・外部副作用は接続していない。

## 実行環境と判定範囲

Windows / Python 3.12.14 / SQLite / Python標準ライブラリ。実在runtimeは `C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`。追加ライブラリはインストールしていない。現行Intent Compiler 0.2.0は読み取りだけを行った。

| 検証 | 実行結果 | 示すこと | 示さないこと |
|---|---|---|---|
| 現行validatorの境界probe | 18件すべて期待した受理/拒否と一致、exit 0。独立再実行でも一致 | 実物XML lintの受理境界 | 意味正確性18/18、現行modelの成績 |
| 最終prototype contract suite | 45 tests、failure/error/skip 0、exit 0。実装担当1.904秒、独立レビュー1.586秒、root確認2.228秒 | 保存・型・根拠照合・状態遷移・権限事前検査のfixture契約 | 自然言語解釈の正しさ、将来の違反確率0 |
| schema export一致 | Event/State/Delta/Turn IR/Artifactと補助4種、9ファイルのruntime定義一致 | 配布schemaと実行定義の一致 | 完全Draft 2020-12適合、semantic correctness |
| 北海道fixture | AI予算のassistant origin維持、未確認維持、予約不許可、replay一致 | 与えた手作成Deltaの適用 | モデルが「2番で」を正しく読めること |
| 10/30/100 human-turn replay | 下表の期待状態チェック全件通過、Stateとreplay一致 | 既知解釈を与えた台帳からの再構築 | 長期対話の自然言語Compiler性能 |
| 最終codeによる保存済みtrajectory再確認 | 3台帳のreplay hashが保存済み値と一致。全checkpoint=true。4 source hashes一致 | 最後の修正後も保存済み結果が再構築できること | 元runと同じ処理時間を再測定したこと |
| 評価harness selfcheck | 合成22件通過、exit 0。root独立実行も通過 | 分子/分母、N/A、会話cluster bootstrap、宣言一致、応答追従方策 | A–Eを実modelで比較したこと、実際の情報公平性 |
| 評価scorer CLI | 合成20観測rowを読み取り、集計出力、exit 0 | manifest/observations入出力が動くこと | 合成counterを実測成功率として使えること |
| ローカルApp Server schema取得 | CLI 0.155.1、experimental schema 437宣言、exit 0 | protocol宣言の実物が取得可能 | Work/desktopの全turn capture・hook運用 |

元記録は `audit/probe-results.json`、`prototype/results/test-results.json` と `.txt`、`prototype/results/replay-summary.json`、`evaluation/selfcheck-results.json`。独立レビューの対象・修正・残存制限は `prototype-review.md`。root独立確認の記録は `verification-summary.json`。

## Fixture replayの実測

Deltaと期待状態は手作成。長さは人間ターン数である。AI/tool/解釈event数と区別する。会話は単一fixture familyの拡張であり、24familyの自然言語benchmarkを実行したものではない。

| Human turns | Ledger events | 期待状態チェック | Replay | 元offline harness wall time |
|---:|---:|---:|---|---:|
| 10 | 20 | 36 / 36 | 一致 | 0.939秒 |
| 30 | 60 | 116 / 116 | 一致 | 7.438秒 |
| 100 | 200 | 396 / 396 | 一致 | 107.099秒 |

この時間はappendごとに全台帳integrityとreplayを再検査する簡易実装の処理時間であり、model/APIの遅延ではない。100ターンでは実装上の非効率が大きい。snapshot、増分検査、監査時の完全replayへ分ける改善を今後測定する。最後のauthority・pending-input・unknown・reference修正はtrajectoryのDelta/投影を変更しておらず、最終codeで保存台帳のreplay一致を別途確認した。元runのwall timeはそのまま履歴値として保持する。

`declared_context_event_coverage=1.0`はfixtureが宣言したrequired source集合に対する取得率であり、意味上必要な条件をすべて抽出できた証明ではない。

## 発見して修正した境界

独立レビューでは、assistant根拠でuser explicit nodeを修正する経路、古いgateの時刻再検査不足、内外scopeの早い期限の見落とし、未解釈の撤回後に旧packetを使う経路、authority target scopeの無視、解決済みunknownのopen残留、同ID/version参照候補の型曖昧、resource自身の期限境界を確認した。修正と回帰テストを追加した。これは設計だけで実装の正しさが保証されない具体例でもある。

現行lintでは実在する引用に反する否定反転、資料内命令のuser制約化、存在しない一般infer根拠ID、推測を含むunknown等が受理された。これらは決定論的validatorの範囲外を可視化した観測であり、現在のホストmodelが実際にその誤IRを生成する頻度は測定していない。

## 設計と試作の差

- 原文captureと投影は試作では同一SQLite transaction。capture中のprojector障害ではrawもrollbackする。独立durable inbox・host再送adapterは未実装。
- 保存対象は受け取ったUnicode文字列。元byte/BOM、PDF原本と抽出representation、座標map、extractor versionは未実装。
- schema validatorはREADMEに列挙した限定vocabularyだけを扱う。未対応keywordは拒否。汎用Draft 2020-12 validatorでの独立metaschema検査は `not_run`。
- 依存は保守的なnode単位suspension。typed AND/OR支持、field依存、自動再計算は設計段階。
- artifact manifestsの旧版は保持する。古いnode revisionを後から採用/参照するsnapshot resolverと実hostのseen-version captureは未実装。
- authority preflightはread-only検査。認証backend、artifact/event直接許可、dispatch lease/fencing、実行中の撤回・取消・外部補償は未実装。gate後からdispatchまでのraceは未解決。
- `trusted_identity`は認証済みadapter入力の想定であり、Python引数のbooleanが認証を提供するわけではない。引用一致も、その文が実行許可を意味することを証明しない。
- schema migration、解釈版切替、privacy/retention/deletion、暗号化、production ACLは未実装。
- selectorはcaller指定と小さい保守的closure。意味検索・必要集合の独立推定・adaptive routingは未実装。

## 未実施の比較実験と再実行

A–Eの実model比較、natural-language Delta精度、semantic verifier、10/30/100-turn closed-loop、blind human adjudication、確認負荷、token/API金額/p50/p95、Work実環境の自動介入、実tool撤回raceを実施していない。model呼出し・外部操作は0件。付属synthetic counterを実績へ転記しない。

再実行コマンドは納品 `README.md` と各下位READMEにまとめた。新しい出力pathを使い、現行pluginの原本を編集しない。モデル比較へ進むには `benchmark-protocol.md` に沿って実model adapter・人間gold・sandbox executorを接続し、情報アクセス・context/総予算・model設定を固定する。評価用の閾値・試行数は事前登録案であり、ユーザー承認済み予算や実測改善ではない。

キャッシュ障害ではledgerを変更せずreplay/rebuildする。重要な原文欠落やhash不一致なら欠落/破損を表示し、依存する権限を使わない。未知schema/compiler版は拒否する。replayで外部toolを再実行しない。
