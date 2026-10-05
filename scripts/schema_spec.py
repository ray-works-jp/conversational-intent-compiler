"""The exact, deliberately limited schema vocabulary used by this prototype."""
import json
from pathlib import Path

VERSION = "cic-prototype-0.1"

def obj(props, required=None):
    return {"type": "object", "properties": props,
            "required": list(props) if required is None else required,
            "additionalProperties": False}

def arr(item): return {"type": "array", "items": item}
def enum(*values): return {"enum": list(values)}
S = {"type": "string"}
ID = {"type": "string", "minLength": 1}
N = {"type": "integer", "minimum": 0}
B = {"type": "boolean"}
STRINGS = arr(ID)
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
ANY = {}  # JSON-compatible metadata or unspecified business-domain values.

EVIDENCE = obj({"event_id": ID, "start": N, "end": N, "quote": S})
SCOPE = obj({"kind": enum("conversation", "task", "turn"),
             "targets": STRINGS, "turn_id": {"type": ["string", "null"]},
             "task_id": {"type": ["string", "null"]},
             "valid_from": {"type": ["string", "null"]},
             "valid_until": {"type": ["string", "null"]}})
NULL_STRING = {"type": ["string", "null"]}
SEMANTICS = obj({"actor": NULL_STRING, "action": NULL_STRING,
                 "object": {"type": ["string", "object", "null"]}, "goal": NULL_STRING,
                 "deadline": NULL_STRING,
                 "time_range": {"type": ["object", "null"], "properties": {"start": NULL_STRING, "end": NULL_STRING}, "required": ["start", "end"], "additionalProperties": False},
                 "quantity": {"type": ["object", "null"], "properties": {"value": {"type": "number"}, "unit": ID, "epistemic": enum("USER_EXPLICIT", "AI_assumption", "COMPILER_INFERRED"), "comparator": enum("eq", "lt", "lte", "gt", "gte")}, "required": ["value", "unit"], "additionalProperties": False},
                 "sequence": {"type": ["array", "null"], "items": ID}}, [])
NODE = obj({"id": ID, "version": N, "content": S,
            "origin": enum("user", "assistant", "tool", "external", "compiler"),
            "relation": enum("explicit", "unadopted", "inferred", "observed"),
            "role": enum("goal", "constraint", "preference", "prohibition", "proposal", "latitude", "unknown"),
            "resolution": enum("unresolved", "resolved", "unverified", "verified"),
            "lifecycle": enum("active", "revoked", "superseded", "suspended", "completed", "expired"),
            "scope": SCOPE, "evidence": arr(EVIDENCE), "dependencies": STRINGS,
            "semantics": SEMANTICS})
ARTIFACT = obj({"artifact_id": ID, "version": N, "path": ID, "sha256": HASH,
                "created_by": ID, "media_type": S})
ADOPTION = obj({"id": ID, "target_id": ID, "target_version": N,
                "relation": enum("selected", "confirmed", "referenced"),
                "fields": STRINGS, "exceptions": STRINGS, "evidence": arr(EVIDENCE),
                "artifact_version": {"type": ["integer", "null"]}})
REFERENCE = obj({"id": ID, "expression": S, "evidence": arr(EVIDENCE),
                 "candidates": arr(obj({"target_id": ID, "version": N,
                                         "type": enum("node", "event", "artifact")})),
                 "resolved_target": {"type": ["string", "null"]},
                 "resolved_version": {"type": ["integer", "null"]},
                 "status": enum("resolved", "unresolved"),
                 "behavior_changes": B, "rationale": S})
AUTHORITY = obj({"id": ID, "principal": ID, "actor": ID, "action": ID,
                 "target_id": ID, "target_version": N, "conditions": arr(obj({"name": ID, "equals": ANY})),
                 "valid_from": {"type": ["string", "null"]},
                 "valid_until": {"type": ["string", "null"]},
                 "scope": SCOPE, "evidence": arr(EVIDENCE),
                 "lifecycle": enum("active", "revoked", "expired")})
OPCODES = ["ADD", "MODIFY", "REVOKE", "REPLACE", "SUPERSEDE", "CONFIRM", "SELECT", "REFERENCE", "RESOLVE", "REOPEN", "DELEGATE", "NARROW_SCOPE", "EXPAND_SCOPE", "NO_CHANGE", "COMPLETE", "SUSPEND"]
OP = obj({"op": enum(*OPCODES), "target_id": {"type": ["string", "null"]},
          "value": ANY, "patch": ANY, "evidence": arr(EVIDENCE),
          "scope": SCOPE, "resolution": enum("resolved", "unresolved")})
AUTH_OP = obj({"op": enum("GRANT", "REVOKE", "NARROW", "EXPIRE"),
               "target_id": {"type": ["string", "null"]}, "value": ANY,
               "evidence": arr(EVIDENCE)})
DELTA = obj({"schema_version": {"const": VERSION}, "delta_id": ID,
             "conversation_id": ID, "branch_id": ID, "human_event_id": ID,
             "base_state_version": N, "base_watermark": N,
             "operations": arr(OP), "authority_operations": arr(AUTH_OP),
             "unresolved": arr(REFERENCE),
             "interpretation_method": enum("hand_authored_fixture", "reviewed_external_candidate")})
EVENT = obj({"schema_version": {"const": VERSION}, "compiler_version": S,
             "event_id": ID, "conversation_id": ID, "branch_id": ID, "seq": N,
             "origin": enum("user", "assistant", "tool", "external", "compiler"),
             "principal": {"type": ["string", "null"]}, "trusted_identity": B,
             "kind": enum("human", "assistant", "tool_result", "external", "interpretation", "artifact", "fork", "tick", "action_status"),
             "recorded_at": ID, "effective_at": {"type": ["string", "null"]},
             "raw": S, "raw_sha256": HASH, "parent_ids": STRINGS, "reference_ids": STRINGS,
             "attrs": {"type": "object"}, "request_sha256": HASH,
             "prev_event_hash": {"type": ["string", "null"]}, "event_hash": HASH})
STATE = obj({"schema_version": {"const": VERSION}, "conversation_id": ID,
             "branch_id": ID, "state_version": N, "watermark": N,
             "nodes": {"type": "object", "additionalProperties": NODE},
             "adoptions": {"type": "object", "additionalProperties": ADOPTION},
             "references": {"type": "object", "additionalProperties": REFERENCE},
             "authorities": {"type": "object", "additionalProperties": AUTHORITY},
             "artifacts": {"type": "object", "additionalProperties": ARTIFACT},
             "pending_human": STRINGS, "last_delta": {"type": ["object", "null"]},
             "lineage": arr(obj({"branch_id": ID, "watermark": N})),
             "history": arr(obj({"delta_id": ID, "operation": ID, "target_id": {"type": ["string", "null"]}, "evidence": arr(EVIDENCE)})),
             "clock": {"type": ["string", "null"]}})
TURN = obj({"schema_version": {"const": VERSION}, "compiler_version": S,
            "conversation_id": ID, "branch_id": ID, "turn_id": ID,
            "human_raw": S, "human_raw_sha256": HASH,
            "base_state_version": N, "ledger_watermark": N,
            "routing": enum("PASS", "ANNOTATE", "CONTRACT", "VERIFY"),
            "intent_delta": {"type": ["object", "null"]},
            "active_requirements": arr(NODE), "adoptions": arr(ADOPTION),
            "references": arr(REFERENCE), "authority_boundaries": arr(AUTHORITY),
            "artifacts": arr(ARTIFACT), "source_evidence": arr(obj({"evidence": EVIDENCE, "origin": S, "raw_sha256": HASH})),
            "open_unknown": STRINGS,
            "context_coverage": obj({"required_event_ids": STRINGS, "delivered_event_ids": STRINGS, "missing_event_ids": STRINGS,
                                      "missing_sources": arr(obj({"event_id": ID, "retrieval_status": enum("unavailable", "deleted", "not_provided"), "detail": S})),
                                      "ratio": {"type": "number", "minimum": 0, "maximum": 1}, "selection_policy": S, "known_omissions": arr(S)}),
            "validation": obj({"schema": B, "deterministic": B, "semantic": enum("not_run", "unverified")}),
            "limitations": arr(S)})
SCHEMAS = {"event": EVENT, "state": STATE, "delta": DELTA, "turn_ir": TURN, "artifact": ARTIFACT,
           "node": NODE, "adoption": ADOPTION, "reference": REFERENCE, "authority": AUTHORITY}

def write_schemas():
    folder = Path(__file__).parent / "schemas"
    folder.mkdir(exist_ok=True)
    for name, schema in SCHEMAS.items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:cic:" + VERSION + ":" + name, **schema}
        (folder / (name + ".schema.json")).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__": write_schemas()
