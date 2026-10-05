# Mission対応表

「設計済み」は効果を検証済みという意味ではない。「試作」は接続していない部分を含めて実製品と区別する。

| 必須成果物 | 納品先 | 確認状態 |
|---|---|---|
| 1 Executive Summary / 現行再評価 | 主レポート§1–2、current-implementation-audit.md | 実物監査＋設計 |
| 2 一次資料・限界 | research-evidence.md、research-systems-evidence.md、references.json | 読取範囲を明示 |
| 3 アーキテクチャ比較 | 主レポート§4 | 4案、期待見積り |
| 4 会話/tool dataflow | 主レポート§5、prompt-contracts.md | 図＋タイミング契約 |
| 5 Ledger/State/Delta/IR schemas | prototype/schemas、主レポート§6 | 9schema実ファイル、subset検査 |
| 6 Provenance/adoption/authority | 主レポート§7、prototype | 軸分離設計＋限定実装 |
| 7 参照/撤回/失効/依存 | 主レポート§8、prototype/tests | 基本契約実行、typed多支持は未実装 |
| 8 Router/selector/validator | 主レポート§9、prompt-contracts.md、prototype | deterministic実行、NL/意味routing未接続 |
| 9 Work接続/代替 | work-integration-evidence.md、主レポート§11 | 文書/宣言確認、運用未試験 |
| 10 複数turn原文/state/IR | 主レポート§12、prototype/results | 概念例＋手作成Deltaの実replay |
| 11 Replay/loop/metrics | benchmark-protocol.md、evaluation | 計画＋記録集計器、実loop未実施 |
| 12 実験/未実施と手順 | validation-results.md、各README | offlineのみ実測、A–E未実施 |
| 13 試作/test/recovery | prototype、audit、evaluation | 再実行可能script |
| 14 費用/遅延/観測/版 | 主レポート§13/16、benchmark-protocol.md | offline時間、model費用未測定 |
| 15 MVP→v1→v2 | 主レポート§17 | 評価で進めるgate案 |
| 16 非採用機能/残存risk | 主レポート§17、prototype-review.md | 制限・失敗境界明記 |
| 17 TOP10改善 | 主レポート§18 | 指定8列、効果は期待 |
| 18 参考文献 | references.json、研究/接続記録 | 実URL、read scope |

| Mission章 | 主な対応 |
|---|---|
| 0–2 目的/資料/絶対原則 | 主レポート§1–3、監査・在庫 |
| 3 一次調査 | 研究2ファイルとcatalog |
| 4–5 四表現/更新順 | 主レポート§5–6、schemas |
| 6–7 出自/採用 | 主レポート§7/12、北海道fixture |
| 8–9 lifecycle/参照版 | 主レポート§8/12、contract tests |
| 10 raw/context | 主レポート§6/9、欠落試験 |
| 11 Router/PASS | 主レポート§9、PASS撤回test、benchmark metric定義 |
| 12 schemas | 主レポート§6、prototype/schema_spec.py + exports |
| 13 Validator | 主レポート§9、prompt-contracts、静的反例 |
| 14 Authority | 主レポート§7/5/13、preflight tests、executor未実装契約 |
| 15 Work接続 | 確認表・local schema監査 |
| 16 整合性/復旧 | 主レポート§13、CAS/idempotency/replay tests |
| 17–18 benchmark/metrics | benchmark-protocol.md、recorded scorer、policy |
| 19 modules/prototype | 主レポート§10/15、prototype |
| 20 最終成果/roadmap | 本対応表、主レポート§16–18 |
| 21 改善判断 | 主レポート§14、優位性未証明、事前判断条件 |

維持原則は原文保管、source優先、推論型、未決保持、最小overlay、PASSでもcapture、authorityをcontentから生成しない、validationと意味を分ける、eventへ逆引き、未実測値を実測と呼ばないことで対応する。原文を保存すること・取得すること・下流へ届けること・正しく解釈することを、各々の検査と指標へ分けた。
