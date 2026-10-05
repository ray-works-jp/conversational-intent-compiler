# Conversational Intent Compiler vNext — 一次資料調査

調査日: 2026-10-04（Asia/Tokyo）。論文・著者の研究リポジトリを実際に開き、以下の範囲を確認した。網羅的サーベイではない。論文の成績は当時の課題・モデル・条件についての結果であり、今回のCompilerの改善率ではない。記載された過去のモデル名から現在の提供機能・価格を推定しない。

「研究結果」は資料で報告されたこと、「適用推論」は本設計への応用判断、「未検証仮説」は今回の比較実験で確かめることとして分離する。数値の転載を最小限にし、改善率の転用を避ける。

## R01 — Task-Oriented Dialogue as Dataflow Synthesis（2020）

資料: [TACL論文](https://aclanthology.org/2020.tacl-1.36.pdf)、[Microsoftの実装意味論](https://github.com/microsoft/task_oriented_dialogue_as_dataflow_synthesis/blob/master/README-SEMANTICS.md)。

- 読めた範囲: 論文 §1–4 の表現・参照・訂正、§7 の評価指標とTable 2–3周辺。リポジトリのREADME-SEMANTICSにある制約、Preflight/Commit、確認、参照・訂正の説明。実行コードを動かしたとは扱わない。
- 研究結果: 会話状態をデータフローグラフ、発話をグラフを拡張するプログラムとして表現。`refer` と `revise` が過去の構造を再利用する。SMCalFlowでメタ計算ありの表現が展開済み表現を上回る。一方、MultiWOZのJoint Goalではメタ計算なしの比較条件が良い箇所もある。
- 適用推論: 参照・部分変更を全文再生成から分け、型付き対象IDとDeltaで表す。参照候補を型・役割・属性で絞る。PreflightとCommitの分離は副作用直前の検査に参考になる。
- 未検証仮説: 根拠付きDeltaは、今回の自由会話で参照誤りと「それ以外はそのまま」の脱落を減らす。
- 限界: 主に予定・人・場所などの限定領域。予測する実行プログラムを意味の完全な表現と同一視できない。既存のヒューリスティック既定値注入は、そのままユーザー明示制約へ取り込まない。採用範囲・委任・権限の今回の区分は追加設計である。

## R02 — Towards Scalable Multi-Domain Conversational Agents: The Schema-Guided Dialogue Dataset（2020）

資料: [AAAI論文公開ページ](https://ojs.aaai.org/index.php/AAAI/article/view/6394)、[Googleの公式データリポジトリ](https://github.com/google-research-datasets/dstc8-schema-guided-dialogue)。

- 読めた範囲: 論文Abstract・書誌、公式READMEのSchema/Dialogue Representation、評価説明、SGD-Xの説明。論文PDF全文は未読。
- 研究結果: 動的なintent/slot schemaと自然言語説明を入力し、未知APIへの一般化を試験するDST課題を提示。公式schemaは検索と取引を`is_transactional`で区別し、必須・任意・結果slotを表現する。
- 適用推論: schemaの意味説明と機械検証を併用し、Stateのslot値だけでなくDelta対象・適用範囲を明示する。取引分類は行動影響Rの一入力にできる。
- 未検証仮説: schemaの言い換えや項目順序に対する頑健性を、IR形式比較にも転用できる。
- 限界: 取引フラグはユーザー許可ではない。固定されたslot状態を、長期の任意要求・撤回・参照・latitudeの十分な表現と扱わない。API説明の内容から実行権限を生成しない。

## R03 — Truth Maintenance Systems for Problem Solving（1977）／A Truth Maintenance System（1979）

資料: [IJCAI 1977の著者報告](https://www.ijcai.org/Proceedings/77-1/Papers/035.pdf)、[1979論文の出版社Abstract](https://www.sciencedirect.com/science/article/pii/0004370279900080)。

- 読めた範囲: IJCAIの1ページ報告にある非単調依存表現・justification・更新手順。1979論文は検索結果に表示された出版社Abstractのみで、ページ取得はエラー。MIT長報告や1979全文を読んだとは扱わない。
- 研究結果: 信念と、それを支持する理由を保持し、新情報に応じて依存する信念を更新する方法を記述する。依存関係に基づくバックトラックと仮説推論を可能にする。
- 適用推論: 要求・参照・作業仮説に`depends_on`を持たせ、依存元の訂正後は下流項目を再検証またはsuspendedへ移す。単純な「最後の発言優先」から対象・支持関係の検査へ移る。
- 未検証仮説: 局所的な依存失効は、全状態の毎回再生成より撤回漏れを減らす。
- 限界: 形式化された信念更新であり、自然言語の解釈や誰が許可できるかは解かない。古典理論の整合性を、曖昧な会話の正解保証へ転用しない。サイクルや複数支持の処理は別途試験が必要。

## R04 — Selective Classification for Deep Neural Networks（2017）

資料: [NeurIPS論文](https://papers.nips.cc/paper_files/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf)。

- 読めた範囲: §2–3 のrisk/coverage定義と選択手法、§5 のCIFAR/ImageNet実験条件と結論。
- 研究結果: 予測を拒否する選択関数で、予測した集合の誤りとcoverageのトレードオフを測る。保証は標本抽出・分布などの前提を伴う。画像分類で実験している。
- 適用推論: Routerの保留率と保留しなかった意味誤り率を同時に測る。PASS、意味判定のabstain、ユーザー確認を別の判断として記録する。短文だからPASSとは決めない。
- 未検証仮説: T/R別に校正した選択的Verifierが、全件Verifierより少ない負荷で重要な意味誤りを減らす。
- 限界: 画像分類の確率保証は、分布変動・ターン依存・多解釈のある会話へ直接適用できない。LLMの自己申告confidenceを校正済み確率と扱わない。unknownと委任されたlatitudeを同じ拒否理由にしない。

## R05 — Chain-of-Verification Reduces Hallucination in Large Language Models（2024、preprint 2023）

資料: [ACL Findings論文](https://aclanthology.org/2024.findings-acl.212.pdf)。

- 読めた範囲: §1・3 のjoint/2-step/factored手順、§4 の課題・モデル・評価条件、結果表周辺。
- 研究結果: 草稿から検証質問を作り、質問に独立に答えて再検討する。Wikidataの集合質問、closed-book MultiSpanQA、人物紹介などで幻覚減少を報告。検証回答に草稿を入れると元の誤りを繰り返しやすく、factored構成で改善した条件がある。
- 適用推論: Verifierへ原文・文脈・検査対象を渡し、Compiler結論への同意を求めるだけにしない。source→overlayの要求網羅とoverlay→sourceの支持を独立に検査する。
- 未検証仮説: 対象を限定した独立検証が、過剰採用や否定反転の検出を改善する。
- 限界: 主に事実生成であり、会話意図・権限・状態遷移の検証ではない。同じモデルを使うため、入力を分離しても独立誤差は保証されない。呼出回数と入力再送が増える。

## R06 — Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena（2023）

資料: [NeurIPS論文](https://proceedings.neurips.cc/paper_files/paper/2023/file/91f18a1287b398d378ef22505bf41832-Paper-Datasets_and_Benchmarks.pdf)。

- 読めた範囲: §3.3–3.4 の位置・冗長性・自己選好候補・推論限界と対策、§4の一致定義・Table 5–6、Appendix D.3。
- 研究結果: 当時のLLM judgeは人間選好と高い一致を示す条件があるが、位置と冗長性などの偏りが存在。Table 5のGPT-4 pairwise対humanは非tie条件で85%、tie等を含む条件で66%となり、分母と処理規則で値が変わる。自己選好については限定データから確定できないと述べる。
- 適用推論: 方式名を伏せ、提示順を入れ替え、根拠spanと違反カテゴリを先に判定する。重要な権限違反は人間adjudicationを行う。
- 未検証仮説: 意図・状態遷移に特化したrubricと監査により、judge誤差を測定・制御できる。
- 限界: 人間選好への一致は、意味・権限の正しさではない。複数judgeの一致を独立な証拠数と数えない。今回のモデル・課題で再校正が必要。

## R07 — Large Language Models Cannot Self-Correct Reasoning Yet（2024）

資料: [ICLR論文](https://proceedings.iclr.cc/paper_files/paper/2024/file/8b4add8b0aa8749d80a34ca5d941c355-Paper-Conference.pdf)。

- 読めた範囲: §2のintrinsic/external feedback区分、§3のGSM8K・CommonSenseQA・closed-book HotpotQA条件とTable 2–6、§4の公平性の論点。
- 研究結果: 当時の対象モデル・プロンプトでは、正解ラベルを外部feedbackとして利用しない自己訂正が推論成績を悪化させる条件を報告。oracle feedback、初期prompt品質、応答数を揃えない比較が改善主張を歪めうる。
- 適用推論: 「もう一度考えて」の全件追加を標準化しない。根拠・決定論的検査と、追加生成回数を揃えたablationを重視する。
- 未検証仮説: 原文と状態差分を渡すVerifierは、結論だけを再考させる自己訂正より有効である。
- 限界: 論文タイトルを現在の全モデル・全課題への不可能性定理として引用しない。CoVeとは課題と検証構成が違う。今回のsemantic overlayに対する改善・悪化は未測定。

## R08 — Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs（2024）

資料: [ICML/PMLR公開ページ](https://proceedings.mlr.press/v235/smit24a.html)、[著者preprint](https://arxiv.org/abs/2311.17371)。

- 読めた範囲: 出版者Abstract・書誌、著者preprint Abstract。PMLRのPDFリンク取得はエラーになり全文未読。詳細なモデル別数値は引用しない。
- 研究結果: 費用・時間・精度を比較し、既存debateがself-consistencyや複数推論経路のensembleを安定して上回らないことを報告。調整した一部方式の改善もあり、プロトコル感度を示す。
- 適用推論: 複数モデル、同一モデル複数試行、debate、単一Verifierを同じ予算で比較する。多数決で未解決の意味差を強制確定しない。
- 未検証仮説: 原文根拠による反証を求める少数の検証は、自由討論より少ない入力で状態変更誤りを発見する。
- 限界: Abstractだけでは条件別結論を細分化できない。別モデルでも同じ根拠欠落・学習偏りを共有しうるが、今回の誤り相関は未測定。debateによるCompiler改善を示した資料ではない。

## R09 — Metamorphic Testing: A New Approach for Generating Next Test Cases（1998、著者arXiv再掲2020）

資料: [HKUST技術報告](https://www.cse.ust.hk/~scc/publ/CS98-01-metamorphictesting.pdf)、[著者arXiv再掲](https://arxiv.org/abs/2002.12543)。

- 読めた範囲: 書誌・著者再掲Abstract。PDFを開いたが本文抽出に文字化けがあり、本文の詳細・実験数値は未確認。
- 研究結果: 既に成功したテストから次のケースを導き、完全なoracleが得られない場面の追加検査に用いる手法を提案する。
- 適用推論: 原文内容を保つID付替え、無関係イベント挿入、重複再送、候補の順序変更に対する状態の対応関係を試験する。撤回追加では対象だけが失効するという期待差分を試験する。
- 未検証仮説: これらの変換試験は、少数のgold IR exact matchより投影・参照の実装誤りを発見しやすい。
- 限界: 変換が意味を保つこと自体を確認する必要がある。発話順序、時刻、文体、候補順の変更は参照や適用範囲を変える場合があり、無条件の不変条件にしない。関係試験の合格は自然言語の正解証明ではない。

## R10 — LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory（ICLR 2025、preprint 2024）

資料: [著者本文v2](https://arxiv.org/html/2410.10813v2)、[公式リポジトリ](https://github.com/xiaowu0162/longmemeval)。

- 読めた範囲: 本文§3の課題構成・QA/recall評価、§4–5の記録単位・索引・時間情報・読み方、公式READMEのdataset format・実行説明。OpenReview PDFはブラウザ確認で読めず代替の著者本文を使用。READMEがリンクするV2の内容は未調査。
- 研究結果: 500問で抽出、複数session推論、更新、時間推論、abstentionを評価する。§5.2では要約・抽出factsによる原文値の置換がQAを悪化させる条件があり、索引keyの拡張と原文valueの保持を分けて考えられる。
- 適用推論: 原文保存、取得recall、下流への提示、回答成功を別々に測る。時間・更新・未決情報のケースをvNext評価に転用する。
- 未検証仮説: 原文に戻れる索引と有効状態の組合せは、IR要約継承より長距離制約を保持する。
- 限界: 主に固定履歴後のQAであり、今回の権限・採用範囲・trajectory成功は測らない。公式READMEは2025年のhistory cleanupを告知しており、使用revision・ファイルhashを固定する。論文時点と更新データの結果を混在させない。

## R11 — Evaluating Very Long-Term Conversational Memory of LLM Agents / LoCoMo（2024）

資料: [ACL論文](https://aclanthology.org/2024.acl-long.747.pdf)、[Snap Research公式リポジトリ](https://github.com/snap-research/locomo)。

- 読めた範囲: 論文Abstract・§3–4の生成と評価、結果説明、§8の限界、公式READMEの公開データ・タスク説明。
- 研究結果: personaと時間的event graphに基づく機械生成を人間が編集し、非常に長い会話のQA・event要約・multimodal生成を評価。公開評価集合は10会話、論文で平均約600ターンと報告。長文脈/RAGにも時間・因果関係理解の難しさを報告する。
- 適用推論: 数十ターン離れた根拠、話題移動、時間関係、視覚成果物参照を含む長期stress testの参考にする。
- 未検証仮説: 同じ原文アクセスのbaselineとvNextを比較し、長さ・参照距離によるsemantic drift傾向を測れる。
- 限界: 主に人間同士に似せた機械生成会話であり、実ユーザーの委任や実行撤回を直接代表しない。10会話では会話内ターンを独立標本として数えず、会話単位の不確実性を報告する。外部judgeとgoldも監査対象とする。

## 研究領域への対応と補完が必要な箇所

| 研究領域 | この調査で読んだ根拠 | 設計に移す範囲／補完 |
|---|---|---|
| Semantic parsing / typed IR | R01、R02 | 型付き参照・訂正、schema説明。自由会話での忠実性は未検証 |
| Provenance / source grounding | R03、R05（隣接領域） | 支持理由と原文検証。生成元・採用者の独立軸には別のprovenance仕様が必要 |
| Event sourcing / state projection | R01の非破壊グラフ（隣接領域） | 原文台帳・再投影の永続化契約はevent-sourcing公式資料で補完 |
| Dialogue state tracking | R01、R02 | 更新対象・維持対象の評価。slot以外の要求に拡張が必要 |
| Coreference / discourse resolution | R01 | 型・役割・属性で候補を制限。版・表示履歴・候補集合を追加 |
| Belief revision / truth maintenance | R03 | 依存と理由を保存。権威・scope・再解釈版を追加 |
| Temporal reasoning / versioning | R10、R11 | 時刻と更新の評価。成果物version採用は別途goldを作成 |
| Capability / authority separation | R01のPreflight/Commit、R02の取引分類（隣接領域） | 行動分類を許可と混同しない。実行権限の一次資料は別途補完 |
| Selective prediction / abstention | R04、R10 | risk/coverageとunknown。会話分布で校正・再評価 |
| Generator-verifier / semantic diff | R05–R08 | 根拠付き独立検証と追加呼出数を揃えた比較。意味の正しさは未保証 |
| Prompt injection / confused deputy | この担当では直接の一次資料未読 | 権限・注入の担当調査で補完。既存資料に命令があることを許可根拠にしない |
| Metamorphic / differential testing | R09、R07の公平性 | 不変・期待差分と同予算比較。gold trajectoryとの併用 |

## 設計への合成判断（研究結果そのものではない）

推奨するMVPは、原文台帳＋小さい派生状態＋型付きDelta＋決定論的Validatorとする。参照と修正を第一級の操作にし、意味Compilerの出力をユーザー権限へ直結させない。原文を置換する圧縮、全件多モデル討論、無条件の自己訂正は標準化しない。

選択的Verifierは追加候補である。重要なDelta、版の異なる参照、採用範囲、撤回依存、権限境界を対象に、Compilerの結論を見る前の独立検査と結論後のsemantic diffを比較する。同じモデル・別モデル・複数試行の誤り重複率、正解から誤りへの修正、入力の再送量とp95遅延を記録する。

LongMemEvalとLoCoMoは外部妥当性の一部として使い、専用trajectory benchmarkを置き換えない。固定履歴Replayでは同じ履歴を比較し、closed-loopでは応答に応じたユーザー方策を使う。主要評価は有効制約の生存、撤回、AI提案の混入、参照version、unknown、latitude、権限、最終成功とする。曖昧さには許容解釈・許容行動の集合をgoldとして与える。

この調査に、vNextがraw baselineを上回る実測結果は含まれない。優位性、非劣性、許容負荷は、今回の実装と同じ情報アクセスを使った比較で初めて判断する。
