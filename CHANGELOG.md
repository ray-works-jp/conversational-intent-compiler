# Release notes

## 0.4.1 — 2026-10-05

- ホストAIの意味解釈の小規模パイロットを追加（`resources/evaluation/pilot/`: 5シナリオ・18発話、実行器と採点器、結果）。Claude Code実機で18/18がapply、自動チェック19/20（不一致1件は採点器の偽陽性と判断）。実行側が正解設計と判断を兼ねる・各1回・ベースライン比較なし、のため精度の一般化は不可。CLI・フックの変更なし。

## 0.4.0 — 2026-10-05

- フックで捕捉した台帳の引き継ぎ: `scripts/ledger_status.py`（未解釈の人間入力を読み取り専用で一覧）と、operation-guideの該当節を追加。applyで`pending`から外れることをテスト化。
- 台帳の既定の保存先を`~/.cic/ledgers`に固定（`CLAUDE_PLUGIN_DATA`はskillのBashから見えず、hookとskillで場所がずれるため）。
- 単独skillの配置に`ledger_status.py`を同梱。テストは29件。Claude Code実機でフック→skill→pending報告まで確認。意味解釈の精度とAntigravity上の同flowは未確認。

## 0.3.1 — 2026-10-05

- 作者名・著作権者名をGitHubアカウント名`ray-works-jp`へ統一（LICENSE、3つのmanifest、marketplace、README）。コードの変更なし。

## 0.3.0 — 2026-10-05

- 任意(`CIC_CAPTURE=1`)の自動捕捉フックを追加。Claude Code: `UserPromptSubmit`→`hooks/capture_turn.py`。Antigravity: `PreInvocation`→`hooks/capture_antigravity.py`（transcriptから人間入力を読む）と`scripts/install_antigravity_hook.py`。人間入力の原文を会話別の台帳へ逐語記録する。共通処理は`hooks/cic_ledger.py`。単体テスト7件、実機でClaude Code1ターン・Antigravity2ターンを確認。AI応答・Delta・ChatGPT/Codexは対象外。

## 0.2.1 — 2026-10-05

- 公開リポジトリで、ハッシュ記録のある17ファイルがLFに正規化されており`resources/upstream-files.json`のSHA-256と一致しなかった不具合を修正（元のバイト列のまま保存）。再発防止に`test_upstream_hashes_match_files`を追加。

## 0.2.0 — 2026-10-05

- Claude Code用 `.claude-plugin/plugin.json` を追加（validate合格、skill認識を確認）。
- Antigravity用に、skill単独の自己完結フォルダを作る `scripts/install_skill.py` を追加。
- operation-guideのPLUGIN_ROOT解決を、単独skill配置にも対応させた。
- 全manifestとREADMEを0.2.0へ統一。README（同梱ファイル表・ホスト別配布）と`release-verification.json`（0.1.0記録を`baseline_0_1_0`へ移し、0.2.0の結果と未検証項目を追加）を更新。
- `scripts/test_package.py`を追加（バージョン一致、SKILL.md frontmatter、install_skill.pyの配置・CLI実行・上書き拒否）。この過程で、Windowsで読取専用属性のあるフォルダがあると`install_skill.py --force`が権限エラーになる不具合を見つけて修正。
- LICENSE（MIT）を追加し、作者名を`t93094195-jpn`へ設定。単独skill配置にもLICENSEを同梱。
- Antigravity単独skill配置(plugin無し)でも、更新後の手順書どおりSKILL_ROOT直下の存在確認からinit成功を確認。
- Antigravity(plugin配置)でも、更新後の手順書どおりに直接のTest-Pathで解決しinit成功を確認。
- Claude Code用`.claude-plugin/marketplace.json`を追加（validate合格、隔離環境でadd/install確認）。
- operation-guideに、`cic_cli.py`の存在確認は直接指定のls/Test-Path/Readで行い、Glob0件や広域検索の結果で判断しない旨を追記。再実行でSKILL_ROOT→Test-Path→2階層上→Test-Pathの手順どおりに解決しinit成功。
- Claude Code対話セッションでskill起動からinit成功(ok:true)まで確認（許可確認の有無は未判定）。
- Antigravity対話モードで許可確認が出て、承認後にok:trueになること、承認が保存されないことをログで確認（先の「プロンプトなし」の記録は誤りで訂正）。
- Antigravity内でのcic_cli.py init実行(ok:true)を確認。
- `agy plugin install`での導入と、plugin配置からのskill認識を確認。
- Antigravity CLI(agy 1.2.14)でskill認識とroot解決、Claude Codeでroot解決とinit成功を実機確認。skills置き場を公式docsに合わせ`.agents/skills`へ訂正。PythonコマンドとHeadless権限の注意をREADMEとoperation-guideへ追記。
- CLI・schema・skill本文は0.1.0から変更なし。21テスト（既存17+新規4）合格。Claude Code上のskill root解決とAntigravity上での実動作は未検証。

## 0.1.0 — 2026-10-05

- 新しい独立プラグインとして、会話意図の明示起動workflowを追加。
- 原文優先、origin/adoption分離、Delta、未決/latitude、権限境界、PASS時の記録をskillへ実装。
- offline基盤を同一bytesのまま再利用し、Python CLI adapterを追加。
- 9schema、一次研究・現行監査・評価計画、合成評価harnessを同梱。
- portable/compatibility manifests、標準アイコン、3 starter promptsを追加。
- 全turn hooks、MCP server、認証、外部操作、優位性の実測は今回のreleaseへ含めない。
