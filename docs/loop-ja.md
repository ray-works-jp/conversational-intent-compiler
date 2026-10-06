# ループ運転：人間の雑な入力 → AIコンパイラ → AIの応答 → … → 明示的に停止

`scripts/cic_loop.py` は、次の流れを、**明示的に停止するまで繰り返す**実行器です。これは初版XML Compilerの独立runnerです。プラグイン会話のState/Deltaへ接続する継続モードは [会話ループ手順](../skills/conversational-intent-compiler/references/continuous-loop.md) を使います。

```
人間の雑な入力 → コンパイラAI → （検査）→ 応答AI → 人間の雑な入力 → コンパイラAI → … → 停止
```

コンパイラAIは、[最初のコンパイラー（Intent Compiler 0.1.0）](../resources/intent-compiler/first-compiler-0.1.0/skills/compile-intent/references/system-prompt.md)の実行仕様を**そのまま**使います（同梱ファイルは無改変。ハッシュは `resources/intent-compiler/SHA256SUMS.txt`）。

## 使い方
```bash
python scripts/cic_loop.py                      # キーボード入力。コンパイラ・応答AIとも `claude -p`
python scripts/cic_loop.py --compiler agy --responder claude --allow-agent-tools
python scripts/cic_loop.py --script inputs.txt  # 1行1入力のファイルから（スクリプト運転）
python scripts/cic_loop.py --ledger loop.db     # 人間の入力とAIの応答を、CICの台帳へ逐語で記録
python scripts/cic_loop.py --ab                 # 「IRなし」で応答した結果も記録（比較用）
```
バックエンド：`claude`（プロンプトは標準入力、tool/skill/hook/MCPを制限）、`agy`（`agy -p=<プロンプト>`）、`cmd:<コマンド>`（プロンプトを標準入力へ渡す）。agy/cmdはtoolなしを保証できないため明示 `--allow-agent-tools` が必要。Windowsの引用付きargv、`cmd:["実行ファイル","引数"]` を扱い、shellは使わない。

## 1回の処理
1. 人間の雑な入力を1つ読む。
2. コンパイラAIが、次のどれか**1つ**を返す：`T0`（そのまま渡す）／`IR`（XMLの解釈メモ）／**質問1つ**。
3. IRは、コードが原文と照合して検査する（下記）。不合格なら1回だけ直させ、それでも不合格なら、**IRを捨てて原文をそのまま渡す**。
4. 応答AIが、原文（と、あればIR）で答える。質問のときは、質問を人間に見せ、人間の次の入力を答えとして続ける。
5. ログ（JSONL）に記録し、`--ledger` なら台帳にも逐語で記録する。
6. 1へ戻る。

## 停止（これだけが、ループを終わらせる）
- 入力：`:stop` `/stop` `:quit` `/quit` `:exit` `/exit` `:q` `コンパイラー停止` `コンパイラ停止`
- 入力の終わり（Ctrl-D、`--script` の最後）はsuspended（入力待ち）、Ctrl-Cはinterrupted。一つの処理を完了しても継続意思を撤回したとは扱わない。
- **次のものは、ループを止めません**：T0、質問、検査の不合格、バックエンドのエラー、空行。
- 「止めて」のような自然な依頼文は、停止ではなく、通常の入力として扱います（「サーバーを止めて」が停止になってしまうのを避けるため）。

## 機械の検査（IRを応答AIへ渡す前）
不合格にする：XML として読めない／`DOCTYPE`・エンティティ宣言・CDATA・処理命令を含む／2万文字超／`tier` が 1〜3 でない／`src="u"` で `q` がない／**`q` が原文の逐語でない**／`strength="must"` が `src=u`・`sys` 以外／`assume` に `if_wrong` がない／`infer` に `from` がない／`unknown` に `need`・`handle` がない／`id` の重複。
警告だけ：`<raw>` が原文の逐語の抜き出しでない、入力と履歴にない数値がある、`from="q:…"` が逐語でない。
この検査は構造の検査で、意味の正しさの証明ではありません。

## 限界と注意
- Claude backendは実物helpで確認した制限フラグを使う。OS隔離の保証とは別。agy/cmdは外部toolを持ち得るので、その環境の権限・隔離を確認する。XML `gate` は文章上の指示で、実サービスの強制gateではない。
- 履歴は既定で全turn・原文全文（`--history 0`）。500文字切断をしない。`--history N`（N>0）を指定した場合だけ直近N回とし、除外件数とknown omissionsを表示する。全履歴方式は長期対話のtoken/遅延を増やすため、性能優位は未測定。
- `--ledger` と同conversationで再開すると、原文・質問・AI応答とIDを台帳から復元する。JSONLだけの再起動復元は未実装。入力とcompiler出力を応答前に記録し、失敗通知はtool観測としてAI原文と区別する。停止入力もuser原文として記録する。
- XML runnerは意味Deltaを自動commitしない。humanはpendingに残る。State/Delta/IR配送と通常AI応答の接続には `cic_session.py` とホストCompilerを使う。
- 1回に、最大2〜3回のモデル呼び出し（コンパイラ、検査失敗時の再試行、応答、`--ab` 時は応答をもう1回）。利用枠・時間を消費します。
- 「コンパイルしたほうが、そのまま渡すより良い」ことは、**まだ測っていません**。`--ab` は同一履歴からの局所比較であり、方式別の会話trajectoryを使う正式raw baseline比較ではない。
- 入力はモデルへ送られます。個人情報を含む場合は、利用するサービスの方針を確認してください。
