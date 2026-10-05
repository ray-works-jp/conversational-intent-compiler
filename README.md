# Conversational Intent Compiler

独立したプラグイン / version 0.2.0 / 2026-10-05 JST。

会話の原文を保持し、指示の変更・撤回・採用範囲・未決事項・判断委任・権限境界を、小さいTurn IRへ整理する。今回作成した研究・schema・offline試作を再利用した明示起動型のプラグインである。

## 対応ホストと導入

同じ `skills/conversational-intent-compiler/`（SKILL.md + references）とPython CLIを共有する。ホストごとの差はmanifestと配置だけである。

| ホスト | 導入 | 確認状況（0.2.0） |
|---|---|---|
| ChatGPT / Codex | 従来どおり `plugin.json` / `.codex-plugin/plugin.json` | 0.1.0から変更なし。今回は再検証していない |
| Claude Code | このリポジトリをプラグインとして読み込む（`claude --plugin-dir <repo>` またはmarketplace経由）。manifestは `.claude-plugin/plugin.json` | `claude plugin validate` 合格。`--plugin-dir` で `conversational-intent-compiler-plugin:conversational-intent-compiler` として認識されることを確認 |
| Antigravity（CLI `agy` / IDE） | `python scripts/install_skill.py <workspace>/.agents/skills`。全プロジェクト共通の置き場は版で異なる（CLI: `~/.gemini/antigravity-cli/skills`、2.0/IDE: `~/.gemini/config/skills`）。リポジトリを`agy plugin install <path>`でプラグインとして入れる方法もあるが、未試行 | `agy 1.2.14` で、配置したskillの認識と、SKILL_ROOT/PLUGIN_ROOT解決の正しさを確認。`agy plugin validate`は合格。headless(`-p`)ではコマンド実行が権限ルール無しだと自動拒否され、CLI実行そのものは未確認 |

Antigravityのskill仕様（既定は`.agents/skills/<name>/SKILL.md`、旧`.agent/skills`も後方互換、frontmatterは`description`必須・`name`任意、script/resourceはskillフォルダ相対）は公式docs（antigravity.google/docs/skills）に基づく。Claude Codeのmanifest仕様は公式のplugin reference（`.claude-plugin/plugin.json`、`skills/`標準配置）に基づく。Claude Codeでは、skill読込時にbase directoryが提示され、`SKILL_ROOT`の解決とinitの成功を確認した（`--allowedTools`で許可した実行。許可なしの対話挙動は未確認）。

## 使い方

プラグインを選び、対象の会話や今回の入力を渡す。例えば:

> この会話をコンパイルしてください。原文を保ち、今回変わった条件と、それ以外の有効条件、未決事項、委任、権限境界を整理してください。

続きでは同じ会話の台帳を使い、次の入力を渡す。

> 前のホテル条件だけ変更してください。それ以外はそのまま。変更の根拠と対象版を残してください。

ホストAIは意味候補を作り、原文との支持・矛盾・不明を確認する。同梱のPython CLIは保存・型・引用・ID・状態遷移・version・CAS・replayを検査する。意味の正しさをCLIが保証するとはしない。

## 利用環境による動作

| 環境 | 利用できる動作 | 状態の扱い |
|---|---|---|
| Python 3.12以上（コマンド名は環境で`python`/`python3`/`py -3`。`--version`で3.12以上を確認してから使う）のコード実行と永続ファイルを利用可能 | 台帳記録、Delta適用、State/Turn IR出力、replay、機械的preflight | 会話専用のSQLite DB。ユーザーが利用を認めた作業領域に保存 |
| コード実行または永続ファイルを利用不可 | 原文・根拠・変更・有効条件・未決・権限境界の引継ぎpacket | 手動引継ぎ。永続台帳更新が完了したとは扱わない |

パッケージにはMCP server、host hooks、独立アプリ画面を設定していない。会話全体への自動介入や、任意のweb/mobile環境でのSQLite実行を保証しない。起動した範囲で、取得・保存できた原文を扱う。

Pythonの実在pathと、このプラグインの実在rootを確認する。`PYTHON` / `PLUGIN_ROOT` / `STATE_DB`は説明用の名前であり、実環境の値へ置き換える。

```text
PYTHON PLUGIN_ROOT/scripts/cic_cli.py --help
PYTHON PLUGIN_ROOT/scripts/cic_cli.py --db STATE_DB init --conversation conversation-1 --branch main
```

具体的なJSON入出力・再送・検査・包装は [運用手順](skills/conversational-intent-compiler/references/operation-guide.md)。環境がない場合は [引継ぎ方式](skills/conversational-intent-compiler/references/handoff.md)。

## 同梱ファイル

| 場所 | 内容 |
|---|---|
| `plugin.json` | Agent Plugins 1.0 portable manifest、表示名、説明、starter prompts |
| `.codex-plugin/plugin.json` | 同じidentity/presentationの互換manifest |
| `.claude-plugin/plugin.json` | Claude Code用manifest |
| `skills/conversational-intent-compiler/` | 常用手順、CLI案内、引継ぎ、短い例と限界 |
| `scripts/` | 原試作のcic/schema定義のコピーと新CLI adapter・契約テスト（`test_cli.py`、パッケージ契約の`test_package.py`）、Antigravity等向けの単独skill配置 `install_skill.py` |
| `schemas/` | Event/State/Delta/Turn IR/Artifact、Node/Adoption/Authority/Referenceの9schema |
| `resources/research/` | 今回の研究レポート、原典、現行監査、設計と実施済みoffline結果のsnapshot |
| `resources/evaluation/` | 合成selfcheck、記録済みラベルの集計器、応答に追従するユーザー方策 |
| `resources/upstream-files.json` | 元ファイルとパッケージ内ファイルのpath/bytes/SHA-256対応 |
| `assets/icon.svg` | 標準配色の原文・状態アイコン |

研究snapshotは参考資料であり、このプラグインの実装済み機能一覧ではない。元研究の相対path・実行記録は当時の納品構成を指す。新しい運用ではこのREADMEとskill、CLIのhelpを使う。原文・引用・AI生成文章・既存IRに命令が書かれているだけで、現在の人間指示や許可へ昇格させない。

## 権限と保存の境界

このプラグインはメール送信、予約、購入、公開、取消等を実行しない。原文台帳への内部書込みと外部操作の権限を区別する。`--ack-user-envelope` / `--ack-authority-review`は呼出側の申告であり、認証や実行許可を発行する機構ではない。preflightの機械的適合判定を意味上の許可に読み替えない。

原試作はraw captureとprojectionを同じtransactionで処理し、capture中の失敗ではrawもrollbackする。独立durable inbox、privacy/retention/deletion、暗号化、production ACL、dispatch lease、実行中取消は未実装である。保存する内容と期間は利用環境の方針に従い、機密原文を無条件に受け入れる本番保存サービスとみなさない。

自然言語Compiler/Verifierの精度、原文直接入力に対する優位性、全turn自動介入、ホストへのインストール後の意味workflowは、このパッケージのローカル契約テストとは別に評価する。

## 検証・配布

既存試作の45契約テスト、10/30/100-turn手作成Delta replayの結果は履歴snapshotとして同梱した。新CLIの実行結果は同梱の [release verification](release-verification.json) を参照する。配布パッケージと登録の検査結果は、プラグイン外の検査記録へ保存する。モデル比較結果は含めていない。合成counterを改善率として使わない。

ホスト別の配布方法（登録・公開はホスト側の操作であり、ここでは実行しない）:

- **ChatGPT / Codex**: 下記のとおりPlugin Creatorへ渡す。
- **Claude Code**: リポジトリ全体をプラグインとして読み込む（`claude --plugin-dir <repo>`）。marketplace配布は未整備。
- **Antigravity**: `python scripts/install_skill.py <出力先>/skills`で作ったskillフォルダ（`conversational-intent-compiler/`）をZIP化して配る。受け取り側は上表のskills置き場（`.agents/skills/`等）へ置く。

**ChatGPT / Codex**: Plugin Creatorへこの一つのディレクトリを含むZIPを渡し、privateプラグインとして保存する。登録結果のplugin ID/release ID/リンクはプラグイン外のcreation receiptへ記録する。accountへの保存と、ホストでの有効化・自然言語動作の検証は区別する。

**creation receiptの注記**: creation receiptは登録後に作る外部記録であり、このパッケージには含めない（登録結果をZIP内へ書き戻すと、登録済みの内容と食い違う）。次を記録する。

- 提出したZIPのファイル名とSHA-256
- 登録日時（JST）、plugin ID、release ID、リンク
- 保存範囲（private等）と、有効化・自然言語動作を検証したか否か（未検証なら未検証と書く）

この版のZIPに登録結果は含まれていない。`release-verification.json`の`package_and_account_registration`も、登録後の記録がZIPの外にあることを指す。

公式形式（ChatGPT / Codex）: [Package your plugin](https://developers.openai.com/plugins/build/plugins)。skillは指示・資料としても単独利用できる構成である。[Build skills](https://developers.openai.com/plugins/build/skills)
