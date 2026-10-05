# Release notes

## 0.2.0 — 2026-10-05

- Claude Code用 `.claude-plugin/plugin.json` を追加（validate合格、skill認識を確認）。
- Antigravity用に、skill単独の自己完結フォルダを作る `scripts/install_skill.py` を追加。
- operation-guideのPLUGIN_ROOT解決を、単独skill配置にも対応させた。
- 全manifestとREADMEを0.2.0へ統一。README（同梱ファイル表・ホスト別配布）と`release-verification.json`（0.1.0記録を`baseline_0_1_0`へ移し、0.2.0の結果と未検証項目を追加）を更新。
- `scripts/test_package.py`を追加（バージョン一致、SKILL.md frontmatter、install_skill.pyの配置・CLI実行・上書き拒否）。この過程で、Windowsで読取専用属性のあるフォルダがあると`install_skill.py --force`が権限エラーになる不具合を見つけて修正。
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
