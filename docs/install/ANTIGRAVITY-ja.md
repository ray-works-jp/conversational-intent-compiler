# 導入指示書：Antigravity 用（Conversational Intent Compiler v0.5.1）

この文書は、**AntigravityのAIエージェントへそのまま渡して、導入と検証を依頼するための指示書**です。人間が読む場合は、末尾の「コマンドだけ見たい場合」を参照してください。確認できている環境は Antigravity CLI（`agy` 1.2.14〜1.2.16）です。IDE版・2.0版は未検証です。

## 依頼（AIへ）

次のプラグインを導入し、動作を検証して報告してください。**権限確認を迂回しない**（`--dangerously-skip-permissions` を使わない、設定ファイルへ常時許可を保存しない）こと。コマンド実行の許可確認が出たら、**「今回のみ許可」**を選ぶよう私に求めてください。

### 導入（方法A：プラグイン。おすすめ）
1. 次を実行する：
   `agy plugin install https://github.com/ray-works-jp/conversational-intent-compiler`
   （更新も同じコマンドです。出力に `skills : 1 processed`、`hooks : 1 processed` が出ること）
2. `agy plugin list` に `conversational-intent-compiler-plugin` があること、導入先（`~/.gemini/config/plugins/conversational-intent-compiler-plugin/`）の `plugin.json` の `version` が `0.5.1` であることを確認する。

### 導入（方法B：単独skill。pluginを使わない場合）
1. `https://github.com/ray-works-jp/conversational-intent-compiler/releases/tag/v0.5.1` から `conversational-intent-compiler-antigravity-0.5.1.zip` を取得する。
   SHA-256：`cc410235fd0fb6fef4b8702141af89af4f72f5ccfbfd2ec8dd3c01ddd59fe94b`（53,923 bytes）。一致しなければ中止して報告する。
2. 展開してできる `conversational-intent-compiler/` を、`<ワークスペース>/.agents/skills/` に置く。全プロジェクト共通にする場合の置き場は、CLIが `~/.gemini/antigravity-cli/skills`、2.0とIDEが `~/.gemini/config/skills` です。
3. 方法Aと方法Bを**同時に有効にしない**（同じskillが二重になります）。

### 動作確認
1. 新しい会話で、skill `conversational-intent-compiler` が認識されることを確認する。
2. skillの手順書（`references/operation-guide.md`）に従い、`PLUGIN_ROOT` を解決する。**`scripts/cic_cli.py` の存在確認は、検索ではなく、パスを直接指定した確認（`Test-Path` など）**で行う。単独配置なら `SKILL_ROOT` 自体、plugin配置なら `SKILL_ROOT` の2階層上が `PLUGIN_ROOT` になる。
3. 一時フォルダのDBで、`python <PLUGIN_ROOT>/scripts/cic_cli.py --db <一時フォルダ>/check.db init --conversation c --branch main` を**1回だけ**実行し、`"ok": true` を確認する。
4. 確認後、一時DBを削除してよい（自分で作った一時ファイルだけを削除する）。

### 人間入力の自動記録フック（任意。有効にするかは私が決めます）
- 方法Aで導入すると、プラグイン直下の `hooks.json` により `PreInvocation` のフックが組み込まれます。**既定では何も記録しません。** `CIC_CAPTURE=1` を付けて `agy` を起動したときだけ、人間の入力原文を `~/.cic/ledgers/<会話ID>.db`（`CIC_LEDGER_DIR` で変更可）へ逐語で追記します。入力原文は平文で残ります。
- 有効にする場合は、私の指示があるときだけ行ってください。無効のまま検証を終えても構いません。
- 方法Bで使う場合は、`python <skill>/scripts/install_antigravity_hook.py --workspace <ワークスペース>` で `hooks.json` を書けます（パスに空白があると拒否されます）。
- 記録されるのは人間入力だけです。AIの応答・toolの結果・意味差分は記録されません。

### 報告してほしい内容
- 導入方法（AかB）と、`agy plugin list` の結果、導入された `version`
- skillが認識されたか、`PLUGIN_ROOT` をどう解決したか（実行した確認コマンド）
- `init` の結果（`ok` の値）。許可確認が出たか、どれを選んだか
- 確認できなかったこと、起きた問題（原文のまま）。IDE/2.0版は未検証であることを前提に、確認していない環境を「動いた」と言わないこと

### 元に戻す
- 方法A：`agy plugin uninstall conversational-intent-compiler-plugin`
- 方法B：置いた `conversational-intent-compiler/` フォルダを削除する（自分で置いたものだけ）

---

## コマンドだけ見たい場合（人間向け）
```bash
agy plugin install https://github.com/ray-works-jp/conversational-intent-compiler
agy plugin list
```
自動記録を使う場合のみ、次のように起動します（PowerShell）。
```bash
$env:CIC_CAPTURE = "1"; agy
```
