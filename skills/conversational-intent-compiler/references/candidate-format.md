# Delta候補の最小形式

自然言語からの意味解釈はホストAIが行う。候補JSONの必須fieldを埋めるために、原文にない目標・手順・期日・権限を作らない。schema詳細は `PLUGIN_ROOT/schemas/` を必要な型だけ読む。毎turn全schemaや研究レポートを読む必要はない。

## ひな形の取り出し

`delta-template` 保存結果の `result.candidate_delta` を、新しいcandidateファイルへそのまま取り出す。`schema_version`、`delta_id`、conversation/branch、human_event_id、capture後のbase_state_version/base_watermarkを保ち、operationsのNO_CHANGEを今回必要な操作へ置換する。authority_operationsとunresolvedは必要がなければ空配列。interpretation_methodは `reviewed_external_candidate`。

| field | 扱い |
|---|---|
| schema_version / delta_id | ひな形の値を使う。意味の変更を伴う再解釈は現在baseから新候補を作る |
| conversation_id / branch_id / human_event_id | 実際のcaptureの対応。別branchの根拠を混ぜない |
| base_state_version / base_watermark | ひな形取得時の現在値。CAS失敗なら取り直す |
| operations | 今回の意図変化。op-specific value/patchを検査する |
| authority_operations | 許可の変化。意図操作と別。人間原文による支持と独立意味監査が必要 |
| unresolved | 参照候補/版/行動差を持つ未解決事項 |
| interpretation_method | host候補はreviewed_external_candidate。fixtureと偽らない |

## ADDの実在field例

説明用のhuman rawは `今後は日本語で答えて`、そのevent IDは `c1:main:H1`。この10 Unicodeコードポイント全体をevidenceにする例。利用時は実際のevent ID・原文・spanへ置換する。この例自体は現在のユーザー指示ではない。

次のオブジェクトをcandidateの `operations` 配列へ入れる。Delta全体ではなく、単一operationの例である。

```json
{
  "op": "ADD",
  "target_id": null,
  "value": {
    "id": "response-language-ja",
    "version": 1,
    "content": "今後は日本語で答えて",
    "origin": "user",
    "relation": "explicit",
    "role": "constraint",
    "resolution": "unverified",
    "lifecycle": "active",
    "scope": {
      "kind": "conversation",
      "targets": [],
      "turn_id": null,
      "task_id": null,
      "valid_from": null,
      "valid_until": null
    },
    "evidence": [{"event_id":"c1:main:H1","start":0,"end":10,"quote":"今後は日本語で答えて"}],
    "dependencies": [],
    "semantics": {"action":"respond","object":{"language":"ja"}}
  },
  "patch": null,
  "evidence": [{"event_id":"c1:main:H1","start":0,"end":10,"quote":"今後は日本語で答えて"}],
  "scope": {
    "kind": "conversation",
    "targets": [],
    "turn_id": null,
    "task_id": null,
    "valid_from": null,
    "valid_until": null
  },
  "resolution": "resolved"
}
```

`resolution=unverified` は要求が存在しないという意味ではなく、解釈/外界検証状態の軸。明示されたユーザー条件は、出自を保ってactive要求として渡せる。schema passでverifiedへ昇格させない。`scope.targets=[]` はこのsubsetでは全対象の意味であり、未知の対象集合の代わりに使わない。新規nodeはversion 1、同IDの再ADDは拒否される。

## sourceと採用の型

evidenceは `{event_id,start,end,quote}`。実際のraw sliceとの完全一致が必要で、hashをホストAIが捏造して付けない。state/台帳側がhashを計算する。重複quoteがある場合は、正しい箇所のspanを選ぶ。本文が支持するかは意味監査の別責務。

Nodeはorigin / relation / role / resolution / lifecycle / scopeを独立に持つ。このschemaに `USER_CONFIRMED` 等の単一enumを追加しない。AI案は `origin=assistant, relation=unadopted, role=proposal`。人間によるSELECT/CONFIRMはAdoption valueで、`id,target_id,target_version,relation(selected|confirmed),fields,exceptions,evidence,artifact_version` を持つ。元nodeのorigin/relationを書き換えない。

`fields` は実際に採用された範囲、`exceptions` は採用しない条件。AI由来予算を人間が案番号だけで選んだ場合、USER_EXPLICIT quantityへ変えない。明示確認がある場合はその確認イベントと確認範囲を追加する。

`unknown/open` はrole=unknownのnode内容とresolutionに未決の種類・扱いを残す。`latitude` はrole=latitudeで判断domainを保つ。schemaに専用lookup/handling fieldはないため、必要な調査や保留の扱いはnodeの自然文contentまたはopaque semantics.objectに表し、ユーザー要求や権限として捏造しない。

## 変更・撤回・参照

MODIFYは既存active nodeのcontent/semantics/resolutionだけをpatchする。originの書換え、強引なscope変更、最新版への採用の付替えをpatchに含めない。変更元のuser explicit nodeには人間根拠を必要とする。

REVOKE/REPLACE等は対象IDとevidenceを持つ。元要求は台帳に残り、撤回済みをREFERENCEしただけでは復活しない。REOPENに人間根拠が必要。依存nodeは保守的にsuspendedとなり、機械が新しい意味を計算し直したとは扱わない。

Reference valueは `id,expression,evidence,candidates,resolved_target,resolved_version,status,behavior_changes,rationale`。候補は `{target_id,version,type(node|event|artifact)}`。unresolvedならresolved_target/resolved_versionをnullとし、合理的候補と行動差を残す。最も新しい候補を必ず選ぶ規則はない。

schema validationとtransition dry-runの両方を行う。opcodeのvalue/patchはschemaだけでは確定しない。未対応の型をschemaへ紛れ込ませず、handoffのknown omissions/unsupportedへ記録する。
