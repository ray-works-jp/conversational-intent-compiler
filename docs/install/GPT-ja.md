# 導入指示書：ChatGPT / Codex 用（Conversational Intent Compiler）

この文書は、**ChatGPT（Plugin Creator）またはCodexのAIエージェントへそのまま渡して、導入を依頼するための指示書**です。人間が読む場合は、「あなたが行うこと」の節だけを見れば足ります。

## 依頼（AIへ）

次の配布物（**最新のRelease**）を、ChatGPTのprivateプラグインとして登録（既に0.1.0が登録済みなら更新）し、導入結果を検証・報告してください。外部への公開・共有・送信、権限設定の変更は行わないでください。

### 対象ファイル
- 配布元：https://github.com/ray-works-jp/conversational-intent-compiler/releases/latest
- ファイル：`conversational-intent-compiler-plugin-<バージョン>.zip`（以下、**そのReleaseの版**を `<バージョン>` とする）
- SHA-256：Releaseページに表示される、そのファイルの **digest（sha256）** と照合する（この文書にはハッシュを書きません。ZIPの中にこの文書自体が入るため）。
- ファイル数：ZIPを展開して数える（展開すると `conversational-intent-compiler-plugin/` が1つできる）。
- 展開すると `conversational-intent-compiler-plugin/` が1つできます。

### 手順
1. ZIPを取得し、**SHA-256がReleaseページのdigestと一致すること**を確認する。一致しなければ中止して報告する。
2. 展開し、次を確認する：`plugin.json` と `.codex-plugin/plugin.json` の `version` が Release の版（`<バージョン>`）、`name` が `conversational-intent-compiler-plugin`、`skills/conversational-intent-compiler/SKILL.md` があること。
3. Plugin Creatorへ、**ZIPをそのまま**（中身を書き換えず、ディレクトリを含む形で）渡し、**privateプラグイン**として保存する。既存の0.1.0がある場合は新しいreleaseとして更新する。
4. 登録後、登録されたファイル数が、展開したZIPのファイル数と一致すること、`plugin.json` と `SKILL.md` の内容がZIPと一致することを確認する。
5. 登録したプラグインを新しい会話で有効化し、スキル `conversational-intent-compiler` が選べることを確認する。

### 注意（正確に扱うこと）
- このプラグインのフック（`hooks/`、`hooks.json`）は、**Claude CodeとAntigravity用**です。ChatGPT/Codexでは動作せず、自動捕捉は使えません。「全ターンを自動で追跡できる」とは説明しないでください。
- Python実行と永続ファイルが使える環境では、同梱CLI（`scripts/cic_cli.py`）で台帳を扱えます。使えない環境では、`skills/.../references/handoff.md` の引継ぎ方式になります。**どちらで動いたかを区別して報告**してください。永続台帳が更新できていないのに「保存した」と言わないこと。
- 検証に使う会話は架空のものにし、実際の個人情報・機密を入れない。
- 本プラグインは外部操作（送信・予約・購入など）を実行も許可もしません。登録の確認でも、そうした操作を行わないでください。
- 意味解釈の精度、ChatGPT上での動作は、未検証の部分があります。確認できたことと、確認できていないことを分けて報告してください。

### 報告してほしい内容
- ZIPのSHA-256照合結果（一致／不一致）
- 登録結果：plugin ID、release ID、version、公開範囲（private）、登録ファイル数
- スキルが選べたか、Pythonコード実行・永続ファイルが使えたか（使えた場合は `init` の結果）
- 確認できなかったこと、起きた問題（原文のまま）

登録結果（plugin ID／release ID／リンク）は、プラグインのZIPの**外**の記録（creation receipt）へ残してください。ZIPの中へ書き戻さないこと。

---

## あなたが行うこと（人間向けの要約）
1. 上のReleaseから `conversational-intent-compiler-plugin-<バージョン>.zip` をダウンロードする。
2. このページの「依頼（AIへ）」の節を、ChatGPT（Plugin Creator）またはCodexの会話へ貼り、ZIPを添付する。
3. AIの報告を確認する。フックが使えないことは、仕様どおりです。
