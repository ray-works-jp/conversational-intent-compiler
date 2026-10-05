# Release notes

## 0.2.0 — 2026-10-05

- Claude Code用 `.claude-plugin/plugin.json` を追加（validate合格、skill認識を確認）。
- Antigravity用に、skill単独の自己完結フォルダを作る `scripts/install_skill.py` を追加。
- operation-guideのPLUGIN_ROOT解決を、単独skill配置にも対応させた。
- CLI・schema・skill本文は0.1.0から変更なし。17契約テスト合格。Antigravity上での実動作は未検証。

## 0.1.0 — 2026-10-05

- 新しい独立プラグインとして、会話意図の明示起動workflowを追加。
- 原文優先、origin/adoption分離、Delta、未決/latitude、権限境界、PASS時の記録をskillへ実装。
- offline基盤を同一bytesのまま再利用し、Python CLI adapterを追加。
- 9schema、一次研究・現行監査・評価計画、合成評価harnessを同梱。
- portable/compatibility manifests、標準アイコン、3 starter promptsを追加。
- 全turn hooks、MCP server、認証、外部操作、優位性の実測は今回のreleaseへ含めない。
