# Recorded evaluation harness

この小実装は、A–Eの比較実験において **外部でラベル済みの観測を集計する器** と、各方式の実応答に追従するclosed-loopユーザー方策の契約を提供する。モデルAPI、自然言語Compiler、意味の自動正解判定は実装していない。付属データは全てsynthetic selfcheckであり、改善率・成功率の実測結果ではない。

## 入出力

`score_recorded.py` の入力はmanifest JSONとobservations JSONL、出力は条件別・会話別の分子/分母、集計値、欠測N/A、会話単位のpaired bootstrap区間である。元ファイルや既存の出力を上書きしない。Python標準ライブラリだけで動く。

manifestはrun ID、replay/closed-loop、API/Work/synthetic、モデルsnapshot/推論設定、A–Eの実装名・実行状態、同一情報アクセスの宣言、同一context budget、主要指標、非劣性条件、許容コスト、blind評価とhuman adjudication手順を要求する。宣言が同じという機械検査は、実際の情報アクセスが同じであったことの証明ではない。ログ・retrieval・tool accessを別途監査する。WorkとAPIを別runにする。

各観測の形式:

```json
{"observation_id":"unique:1","conversation_id":"trajectory:1","condition":"D","metric":"constraint_survival","numerator":3,"denominator":4,"evidence_source":"human_adjudicated","evidence_ids":["gold:1","event:h3"]}
```

- `observation_id` の重複は二重計数を避けるため拒否する。
- 各counterの分母はgold機会数/適用件数としてラベル手順側で定義する。ゼロ分母や欠測を0点に変換しない。観測rowを省略してN/Aを出す。
- `evidence_source` はdeterministic / human_adjudicated / external_evaluator / synthetic。意味正確性を集計プログラムが自動判定したとは扱わない。
- rate指標は分子≤分母、tokens/latency/cost/confirmation_burdenはmeanとして分子/分母を許す。確認負荷の分母は評価計画でturnまたはtrajectoryに固定する。
- PASS precisionの陽性は「重い意味overlayを省けるturn」、recallのgold陽性も同じとする。軽量trackingが要るturnでもPASSが可能なので、tracking要否と別ラベルにする。TP/(TP+FP)、TP/(TP+FN)のcounterを外部ラベルから渡す。

既定comparisonsはA:B / A:C / A:D / A:E / D:E。bootstrapは両方式に当該metric観測がある同一conversation IDのみを再標本化し、各会話の全turnをまとめて扱う。区間は `right − left` のratio-of-summed-counters差。2会話未満はN/A。turnを独立サンプルとして水増ししない。欠測やunpaired除外を確認し、多重比較補正・改善判定・非劣性検定は研究計画側で行う。

## Closed-loop方策

`user_policy.py` は実際のAI応答をadapterで構造化したcandidate_setsを受け取る。候補集合/案には安定ID、見えていたversion、実表示番号、scenarioの目的キーを持たせる。目的キーの付与はfixtureまたはhuman adjudicationの責務であり、番号から自然言語の意味を推定しない。

`choose_actual_proposal` は同じ目的の案が方式Aで2番、Dで1番なら、それぞれ「2番で」「1番で」を生成する。存在しない案を別方式から流用せず、候補集合が複数なら保留して明確化する。選択はAI予算仮定の確認や予約/支払い権限を生まない。`request_availability` はユーザーが見た修正版をversionで結び付け、調査だけを許容次行動とする。

このpolicyは北海道の必須ケース用の最小契約である。自由な長期対話、撤回、branch、中断のユーザー方策一式、実会話adapterは未接続。閉ループ性能を計測したと報告しない。

## 実行

PowerShell例（`$taskPython` は通常のPython 3への絶対パスに置換）:

```powershell
& $taskPython './outputs/evaluation/selfcheck.py'
& $taskPython './outputs/evaluation/score_recorded.py' --manifest './outputs/evaluation/manifest.synthetic.json' --observations './outputs/evaluation/observations.synthetic.jsonl' --output './work/evaluation-synthetic-recheck.json'
```

本納品ではselfcheckを実行して22件が通過した。外部API呼出しは0。`selfcheck-results.json` に実行結果を記録した。manifest/observationのsynthetic fixtureを同梱した。再実行時には新しい出力名を指定する。

本番評価では付属synthetic counterを取り除き、事前登録したラベル規約に従う実観測へ置換する。現行Bは実物prompt/utilityで実行し、Cは過去IR要約を繰り越す方式、D/Eは実Compilerへ接続する。scorerのA–Eラベルだけでは各方式を実装/実行した証拠にならない。
