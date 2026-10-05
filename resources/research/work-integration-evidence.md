# Work / Codex 接続の確認記録

確認日: 2026-10-04 JST。これは接続の設計調査であり、常時hookの導入・有効化・実行試験は行っていない。

## 確認方法と判定

「確認済み」は文書上の仕様か実際の観測かを併記する。「要確認」は製品全体に存在しないという意味ではない。「利用不可」は対象のsurfaceと接続方式を限定する。ローカル実行のWorkとクラウドでオーケストレーションするWorkを同一視しない。

| 必要機能 | ローカルCodex / local-only Work | cloud-orchestrated Work + 通常Plugin | 今回の環境での実動作 |
|---|---|---|---|
| 毎ターンの人間入力 | 公式確認済み: UserPromptSubmit | Plugin prompt hookは利用不可 | 現在の入力は取得済み。自動全ターンは未試験 |
| 過去原文・AI応答 | 要確認: transcriptは安定APIではない。App Serverによる自前capture候補 | 要確認: 完全原文exportの保証なし | read_threadは要約・切詰め付き。lossless取得の証拠にならない |
| tool / artifactイベント | 公式確認済み: hookの一部tool、App Server item通知。全artifact対応は要確認 | 通常Pluginによる全体tapは要確認 | ツールの結果とファイルは今回観測。全体stream未試験 |
| 安定conversation / turn ID | 公式確認済み: session_id / turn_id、App Server thread / turn / item | Pluginへ毎回渡されるIDは要確認 | hostのchat管理toolsあり。完全なbranch lineage未試験 |
| 永続State | 自前storeは可能。今回SQLite試作で検査 | 自前MCP store候補。ユーザー・tenant認証と分岐キーが必要 | ワークスペースへの書込みを確認。MCP永続store未接続 |
| 下流入力へのIR挿入 | 公式確認済み: additionalContext / 自前App Server client。ただし役割の問題あり | 通常Pluginから任意の全ターン前処理を強制できる証拠なし | 全ターン挿入未試験 |
| 副作用直前gate | 公式確認済み: 一部PreToolUse。全tool強制境界ではない | 通常Plugin hooks利用不可。enterprise managed MCP hooksは条件付き | 最新Stateの関数gateをoffline試験。外部実行未接続 |
| 分岐・再生成・中断・再開 | App Server候補。adapterのlineage / attempt mappingは要確認 | 要確認 | 試作branch隔離とreplay。製品とのID対応未試験 |

ローカルCLIは実コマンドで `codex-cli 0.155.1` を観測した。ただしdesktop appの実行engine版と同じとは断定しない。現在のplugin 0.2.0はSkillと文書処理scriptを持つ。hookや常時ledger実装の実物はない。CLIが存在することも、自動挿入成功の証明ではない。

## 公式根拠と重要な制限

[Plugins](https://learn.chatgpt.com/docs/plugins) はSkill、MCP、hookを別要素として説明する。[Build skills](https://developers.openai.com/plugins/build/skills) の役割は再利用可能な手順であり、全入力の横取りを保証する契約ではない。

[Hooks](https://learn.chatgpt.com/docs/hooks) は入力時context追加、一部toolの前後通知を規定する。追加contextはdeveloper roleへ入るため、原文やAI提案をそのまま高権威の命令として挿入してはいけない。生データを別の低権威入力に保持できるadapterを優先する。hook利用案は固定policyと型付き索引だけに限定し、それでもrole昇格リスクを試験する。hookには対象外の経路があり、エラー時にtoolが継続する場合がある。したがって確実な拒否は自前executor側で行う。

[Work Cloud local access](https://learn.chatgpt.com/docs/enterprise/cloud-local-access) は、クラウド側で動くWorkでは通常Plugin/ローカルprompt hooksが非対応であると説明する。enterprise管理のremote MCP hooksは対象イベント・設定・accountが限定される。個人環境で利用できるとはしない。

[Codex App Server](https://learn.chatgpt.com/docs/app-server) はthread / turn / item、入力の開始・steer・streamingを扱う。これは自前clientを設計する候補であり、現在開いている既存Work chatの全ターンへ自動介入できたという実績ではない。

[MCP Events](https://developers.openai.com/plugins/build/mcp-events) はサーバーが提供するイベントへの購読を説明する。外部システムのイベント購読から、ホスト会話の全入力・全応答を得られると推論しない。

## 代替構成と受入試験

1. **明示起動Plugin / 手動引継ぎ**: 人間が原文履歴を渡し、検証済みpacketを同じchatか下流へ明示的に渡す。ledgerへのwriteはwriteとして宣言する。履歴不足はknown omissionsへ記録する。
2. **ローカルhook補助**: captureと索引通知を補助に使う。製品のtool bypass、失敗継続、contextの切詰めを検出する。完全なauthority enforcementとは呼ばない。
3. **自前orchestrator**: ユーザー入力、model入力、tool実行経路を所有する。全副作用をexecutor gate経由に限定し、branch/attempt/cancellationを自前で保持する。API / App Server adapterは実装・認証・モデル利用条件を別途確認する。

接続受入試験は同一sessionの2入力をcapture→完全一致、AI応答のcommentary/final別capture、tool call/result対応、artifact observed_version、fork/retry/interrupt/resume、中断中の撤回、store停止時のwrite拒否、gate timeout時の副作用拒否を行う。現在はこの製品接続試験を未実施。内部記録権限と送信・購入・公開権限は別管理とする。

## MCP tool契約案

| tool | write性 | 主な契約 |
|---|---|---|
| validate_packet / validate_delta | read-only | 永続状態変更なし。ログ永続化する版は別write tool |
| retrieve_evidence / read_state | read-only | tenantとbranch ACL、欠落・版・鮮度を返す |
| capture_event / commit_interpretation | write | idempotency、CAS、監査、session認証 |
| rebuild_projection | write | cache更新のみ。外部tool再実行禁止 |
| preflight | read-only判定版 | 現在条件の照合。lease取得版はwrite |
| execute_authorized | external write | current grant、対象版、exact arguments、execution ID |

[MCP tools仕様](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) と [公式annotations解説](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/) を確認。annotationsはhintであり、認証・実行権限の証明ではない。台帳追記toolをreadOnlyと表示しない。
