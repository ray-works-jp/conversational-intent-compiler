# ファイル実行・永続保存が使えない環境の引継ぎ

手動の原文保全handoffを作る。自動の会話state保存やCLI検査を行えたと報告しない。handoffは運用方式であり、ローカルTurn IRのrouting enumへ独自の値を加えるものではない。

## 保持するもの

1. 今回human rawを逐語で保持する。
2. 解釈に使った過去human / assistant / tool / external rawを別source recordとして保持する。元の話者、event IDまたはローカル仮ID、版、引用・資料境界、原文を含める。仮IDはhostの安定conversation IDと偽らない。
3. 添付・成果物は、実際に存在する元ファイル/見えた版への参照と併せて渡す。原ファイルの代わりに抽出テキストだけを「原本」としない。
4. 上記sourceから得た候補Delta、関連有効状態、採用scope、未決/latitude、権限境界、取得できない根拠を別overlayとして示す。overlayは原文を置換しない。

ファイル生成だけは使える場合、raw source bundleとoverlayを別ファイルで新規保存して実在リンクを返す。ファイル生成も使えない場合、本文内にsource recordsを省略せず載せる。長さ制限等で載せられない原文は未収録として明記し、完全なlossless handoffを作れたと主張しない。欠落sourceを記憶・要約から生成しない。

source保全、必要source取得、今回入力への配送、overlay意味の正しさは別の確認項目である。「rawがある」だけで全て検証済みとしない。

## 最小packetの形

この表示は説明用のhandoff形式であり、CLIへそのまま投入するDeltaではない。ユーザーの指定形式があればそれに合わせる。

```text
Operating mode: manual handoff; persistent state and CLI validation not performed
Conversation / branch: known host IDs, or explicitly provisional local labels
Current raw: verbatim human input
Sources: separate verbatim records with original speaker, event ID and seen version
Intent delta: candidate changes, unchanged fields, source bindings
Relevant state: only needed active conditions, exceptions, dependencies
Adoption: proposal/set/version/fields/exceptions; original origin retained
Open / latitude: unresolved choices and delegated decisions kept distinct
Authority boundary: existing grants with scope; new grants only if explicit human source supports them
Artifacts: stable IDs and seen versions where actually available
Coverage / known omissions: missing source IDs and affected decisions
Validation: raw-preservation checks performed; semantic interpretation candidate; CLI not run
```

次turnではこのpacketの要約だけを入力にせず、原文source bundleも引き継ぐ。以前のpacketがrawを含まない場合は「この要約からは元の条件の正確な確認ができない」と記録する。根拠のある継続部分を進め、重要な差が生じる参照・権限・撤回対象だけを保留する。

## 状態がない場合

- state snapshotなし、原文台帳あり: ホストAIは原文から候補状態を再構成できるが、決定論的replayを実行したとは説明しない。
- state snapshotあり、必要原文なし: snapshotを根拠正本とせず、欠けたeventと影響を示す。外部操作の許可をsnapshotだけで確定しない。
- 原文台帳もsnapshotもなし: 今回入力と実際に見えるsourceだけを処理し、長期条件の完全保持を主張しない。
- 原文が提供されているのに再提出を要求しない。提供済みsourceを読んで処理する。

この方式は機械的なCAS、再送dedup、branch隔離、hash検査を保証しない。移動先が永続実行環境を持つ場合は、原文とorigin/版を確認して新しい台帳へ捕捉し、解釈候補を再検証する。
