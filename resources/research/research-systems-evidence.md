# 一次資料補完: provenance・状態・実行境界

調査日: 2026-10-04 JST。原文献を実際に開いた範囲を以下へ明記。文献の結果とこの設計の効果を区別する。

| ID / 根拠 | 確認範囲 | 文献・公式仕様で確認した内容 | 設計への適用推論 | 未検証仮説と限界 |
|---|---|---|---|---|
| S01 [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) (2013) | overview、entity/activity/agent、derivation/revision/quotation、attribution/delegationの定義 | 生成・使用・派生・責任を関係として表現する仕様 | proposal生成とuser adoptionを別イベント・別関係へ分離する | 監査性向上は仮説。PROVのdelegationは今回の実行grantと同じ意味ではない。来歴は真実性・認可の保証ではない |
| S02 [Azure Event Sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) | Solution、advantages、versioning/ordering/concurrency/testing/privacyの検討事項 | event列を正本としてprojectionを再構築する。複雑さ、遅延、schema進化、削除と不変性の緊張も説明 | 原文event＋解釈event＋派生cache、CAS、補償event、replayを分ける | semantic drift改善は未実証。replayは副作用を再実行する処理とは分離する。削除後のlossless保証を無条件に維持しない |
| S03 [AgentDojo v3](https://arxiv.org/html/2406.13352v3) (2024)、[著者repo](https://github.com/ethz-spylab/agentdojo) | §1–3の環境/評価、§4.3の防御限界、README。実行は未実施 | stateful tool worldのutilityと攻撃成功を別に検査する。防御に合わせたadaptive評価を必要とする | 会話stateだけでなくtool worldの実変更をgoldにする。injection耐性とbenign成功を併記 | 長期の指示撤回・採用範囲の専用評価ではない。既存安全成績をvNextへ転用しない |
| S04 [CaMeL v2](https://arxiv.org/html/2503.18813v2) (2025) | §2–5の脅威モデル、control/data flow、policy/capability、非目標 | model外のinterpreterでデータ由来と許可されたflowを検査する構成。user queryやmemoryへの信頼前提、text-only誤要約等の非目標がある | 意味overlayは下流推論用、実権限はexecutor policyで照合。引数の受取先・対象版も境界とする | user原文の意味誤読、汚染memory、会話でのgrant撤回の完全解決ではない。CaMeLの固定plan全体は導入せず、柔軟性・utility損失を評価する |
| S05 [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | handling user input / mistakes / schema divergence | schema適合でも内容の誤りが残ることを説明 | schema passとsemantic supportのresultを別型にする | constrained decoding単体で忠実性が上がるとはしない。prototypeはAPI未接続 |
| S06 [OpenAI agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) | prompt injection / developer messages / data flow | untrusted内容のdeveloper roleへの挿入を避け、型付きflowと境界を設ける考え方 | hook追加contextの高権威化を監査し、raw/overlayをpolicyと区分する | instruction delimiterだけで強制境界は作れない。全文plan固定や常時確認を要求として転用しない |
| S07 [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[MCP公式annotations解説](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/) | tool model、security考慮、annotationsの意味と制限 | tool hintは実behavior/authorityの証明ではない | capture/commitはwrite、validator read-only版は永続変更無し、lease版はwriteとして別toolにする | hintとbackend認証を取り違えない。MCP接続試験は未実施 |

旧confused-deputy論文の著者サイトは検索で所在が分かったが本文fetchが失敗した。原論文全文を読んだとはしない。この研究では実行主体の持つambient authorityをデータ中の命令へ渡さない境界を、S04とS07の一次資料から設計する。古典論文への孫引きだけで仕様を確定しない。

12研究領域のうちprovenanceはS01、event sourcingはS02、capabilityとprompt injectionはS03/S04/S06/S07で補完する。他領域の原典と読み取り限界は `research-evidence.md` / `references.json` を参照。モデル名・価格・提供日には依存せず、実接続時に公式確認してmanifestへ固定する。
