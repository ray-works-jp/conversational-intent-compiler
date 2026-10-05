"""Offline deterministic event-sourcing prototype. No natural-language compiler.

Interpretation is supplied by fixtures or a reviewed candidate producer. Schema
validity, evidence matching and transition checks are NOT semantic correctness.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from schema_spec import SCHEMAS, VERSION

COMPILER_VERSION = "deterministic-projector-0.1"

class CICError(ValueError): pass
class Conflict(CICError): pass
class MissingSource(CICError): pass
class IntegrityError(CICError): pass

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value): return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()
def raw_digest(raw): return hashlib.sha256(raw.encode("utf-8", errors="strict")).hexdigest()

def parse_time(value):
    if value is None: return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise CICError("Timestamp must be ISO 8601 with an explicit timezone") from exc
    if dt.tzinfo is None: raise CICError("Timezone required")
    return dt.astimezone(timezone.utc)

def utc_now(): return datetime.now(timezone.utc).isoformat()

def validate_schema(value, schema, path="$", *, root=True):
    """Implemented subset only; unsupported keywords fail closed.

    This validates schemas bundled here, not arbitrary Draft 2020-12 schemas.
    """
    allowed = {"$schema", "$id", "type", "properties", "required", "additionalProperties", "items", "enum", "const", "minimum", "maximum", "minLength", "pattern"}
    if root:
        def check_definition(definition):
            if not isinstance(definition, dict): raise CICError("Boolean/nonobject schemas unsupported")
            if set(definition) - allowed: raise CICError("Unsupported schema keywords: " + str(sorted(set(definition) - allowed)))
            for child in definition.get("properties", {}).values(): check_definition(child)
            if isinstance(definition.get("additionalProperties"), dict): check_definition(definition["additionalProperties"])
            if "items" in definition: check_definition(definition["items"])
        check_definition(schema)
    unknown = set(schema) - allowed
    if unknown: raise CICError(f"Unsupported schema keywords: {sorted(unknown)}")
    canonical(value)  # Reject NaN, non-JSON input and invalid surrogate strings below.
    if "const" in schema and value != schema["const"]: raise CICError(path + ": const mismatch")
    if "enum" in schema and value not in schema["enum"]: raise CICError(path + ": enum mismatch")
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        checks = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
                  "string": lambda x: isinstance(x, str), "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
                  "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
                  "boolean": lambda x: isinstance(x, bool), "null": lambda x: x is None}
        if any(t not in checks for t in types): raise CICError("Unsupported schema type")
        if not any(checks[t](value) for t in types): raise CICError(path + ": type mismatch")
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        if len(value) < schema.get("minLength", 0): raise CICError(path + ": short string")
        if "pattern" in schema and not re.search(schema["pattern"], value): raise CICError(path + ": pattern mismatch")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise CICError(path + ": numeric range")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value: raise CICError(path + ": missing " + key)
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props: validate_schema(item, props[key], path + "." + key, root=False)
            elif additional is False: raise CICError(path + ": unexpected " + key)
            elif isinstance(additional, dict): validate_schema(item, additional, path + "." + key, root=False)
    if isinstance(value, list) and "items" in schema:
        for idx, item in enumerate(value): validate_schema(item, schema["items"], path + f"[{idx}]", root=False)

def validate_named(name, value): validate_schema(value, SCHEMAS[name])

def scope(kind="conversation", targets=None, turn_id=None, task_id=None, valid_from=None, valid_until=None):
    return {"kind": kind, "targets": targets or [], "turn_id": turn_id, "task_id": task_id,
            "valid_from": valid_from, "valid_until": valid_until}

def validate_scope(item):
    validate_schema(item, SCHEMAS["node"]["properties"]["scope"])
    if item["kind"] == "turn" and not item["turn_id"]: raise CICError("Turn scope requires turn_id")
    if item["kind"] == "task" and not item["task_id"]: raise CICError("Task scope requires task_id")
    begin, end = parse_time(item["valid_from"]), parse_time(item["valid_until"])
    if begin and end and end <= begin: raise CICError("Invalid validity range")

def evidence(event, text=None, start=None, end=None):
    raw = event["raw"]
    if start is None:
        if text is None: start, end = 0, len(raw)
        else:
            start = raw.index(text)
            end = start + len(text)
    if end is None: end = len(raw)
    return {"event_id": event["event_id"], "start": start, "end": end, "quote": raw[start:end]}

def node(node_id, content, origin, role, source, *, relation=None, dependencies=None, node_scope=None, semantics=None, resolution="unverified"):
    relation = relation or {"user": "explicit", "assistant": "unadopted", "tool": "observed", "external": "observed", "compiler": "inferred"}[origin]
    return {"id": node_id, "version": 1, "content": content, "origin": origin, "relation": relation,
            "role": role, "resolution": resolution, "lifecycle": "active", "scope": node_scope or scope(),
            "evidence": source, "dependencies": dependencies or [], "semantics": semantics or {}}

def operation(op, target_id=None, value=None, patch=None, sources=None, op_scope=None, resolution="resolved"):
    return {"op": op, "target_id": target_id, "value": value, "patch": patch, "evidence": sources or [],
            "scope": op_scope or scope(), "resolution": resolution}

def empty_state(conversation, branch):
    return {"schema_version": VERSION, "conversation_id": conversation, "branch_id": branch,
            "state_version": 0, "watermark": 0, "nodes": {}, "adoptions": {}, "references": {},
            "authorities": {}, "artifacts": {}, "pending_human": [], "last_delta": None,
            "lineage": [], "history": [], "clock": None}

def effective(item, now, turn_id=None, task_id=None):
    if item["lifecycle"] != "active": return False
    sc = item["scope"]
    t = parse_time(now)
    for interval in (sc, item if "valid_until" in item else {}):
        if interval.get("valid_from") and t < parse_time(interval["valid_from"]): return False
        if interval.get("valid_until") and t >= parse_time(interval["valid_until"]): return False
    if sc["kind"] == "turn" and sc["turn_id"] != turn_id: return False
    if sc["kind"] == "task" and sc["task_id"] != task_id: return False
    return True

def validate_evidence(items, lookup, *, user=False, principal=None):
    if not items: raise CICError("A meaningful change requires source evidence")
    found = []
    for item in items:
        validate_schema(item, SCHEMAS["node"]["properties"]["evidence"]["items"])
        ev = lookup(item["event_id"])
        if ev is None: raise MissingSource("Missing source: " + item["event_id"])
        if raw_digest(ev["raw"]) != ev["raw_sha256"]: raise IntegrityError("Raw hash mismatch")
        if not 0 <= item["start"] <= item["end"] <= len(ev["raw"]): raise CICError("Source span out of bounds")
        if ev["raw"][item["start"]:item["end"]] != item["quote"]: raise CICError("Source quote mismatch")
        if item["start"] == item["end"]: raise CICError("Empty evidence is not support")
        if user and (ev["origin"] != "user" or not ev["trusted_identity"] or ev["kind"] != "human"):
            raise CICError("Authority/adoption requires trusted user source envelope")
        if principal and ev["principal"] != principal: raise CICError("Authority principal mismatch")
        found.append(ev)
    return found

def invalidate_dependents(state, changed):
    """Conservative suspension, never manufacture an automatic replacement."""
    queue = list(changed)
    visited = set()
    while queue:
        parent = queue.pop(0)
        if parent in visited: continue
        visited.add(parent)
        for nid, item in state["nodes"].items():
            if parent in item["dependencies"] and item["lifecycle"] == "active":
                item["lifecycle"] = "suspended"
                item["version"] += 1
                queue.append(nid)

def check_dependencies(state):
    visiting, visited = set(), set()
    def visit(nid):
        if nid in visiting: raise CICError("Dependency cycle")
        if nid in visited: return
        if nid not in state["nodes"]: raise CICError("Missing dependency: " + nid)
        visiting.add(nid)
        for parent in state["nodes"][nid]["dependencies"]: visit(parent)
        visiting.remove(nid)
        visited.add(nid)
    for nid in state["nodes"]: visit(nid)
    for item in state["nodes"].values():
        if item["lifecycle"] == "active" and any(state["nodes"][p]["lifecycle"] != "active" for p in item["dependencies"]):
            raise CICError("Active node depends on inactive source")

def apply_delta(state, delta, lookup):
    validate_named("delta", delta)
    if (delta["conversation_id"], delta["branch_id"]) != (state["conversation_id"], state["branch_id"]): raise Conflict("Delta branch mismatch")
    if (delta["base_state_version"], delta["base_watermark"]) != (state["state_version"], state["watermark"]): raise Conflict("Stale base state/watermark")
    human = lookup(delta["human_event_id"])
    if human is None or human["origin"] != "user" or human["kind"] != "human": raise CICError("Missing current human event")
    if delta["human_event_id"] not in state["pending_human"]: raise Conflict("Human event already compiled or outside branch")
    out = copy.deepcopy(state)
    def source(items, user=False, principal=None): return validate_evidence(items, lookup, user=user, principal=principal)
    def get_node(nid):
        if nid not in out["nodes"]: raise CICError("Missing target node: " + str(nid))
        return out["nodes"][nid]
    def add_node(value):
        validate_named("node", value)
        validate_scope(value["scope"])
        if value["id"] in out["nodes"]: raise Conflict("Node ID already exists")
        if value["version"] != 1 or value["lifecycle"] != "active": raise CICError("New node must be active version 1")
        sources = source(value["evidence"])
        # Mixed sources may support an inference; origin must still be explicit.
        if value["origin"] != "compiler" and not any(e["origin"] == value["origin"] for e in sources): raise CICError("Origin source mismatch")
        if value["relation"] == "explicit" and value["origin"] != "user": raise CICError("Non-user content cannot become user explicit")
        if value["relation"] == "explicit": source(value["evidence"], user=True)
        if value["role"] == "unknown" and value["resolution"] == "verified": raise CICError("Unknown cannot be verified fact")
        out["nodes"][value["id"]] = copy.deepcopy(value)
    for op in delta["operations"]:
        validate_scope(op["scope"])
        opcode, tid = op["op"], op["target_id"]
        if opcode in {"ADD", "DELEGATE", "REFERENCE", "NO_CHANGE"}:
            if tid is not None: raise CICError("Operation must not have a target_id")
        elif not tid: raise CICError("Operation requires target_id")
        if opcode not in {"MODIFY"} and op["patch"] is not None: raise CICError("Unused patch is prohibited")
        if opcode in {"MODIFY", "REVOKE", "REOPEN", "SUSPEND", "COMPLETE", "NO_CHANGE"} and op["value"] is not None:
            raise CICError("Unused value is prohibited")
        if op["resolution"] == "unresolved":
            if opcode != "REFERENCE": raise CICError("Unresolved mutations must stay outside committed operations")
        if opcode != "NO_CHANGE": source(op["evidence"])
        if opcode in {"ADD", "DELEGATE"}:
            if opcode == "DELEGATE":
                if not isinstance(op["value"], dict) or op["value"].get("role") != "latitude": raise CICError("DELEGATE creates latitude, not authority")
                source(op["evidence"], user=True)
            add_node(op["value"])
        elif opcode == "MODIFY":
            item = get_node(tid)
            if item["lifecycle"] != "active": raise CICError("Cannot modify inactive node")
            if item["origin"] == "user" and item["relation"] == "explicit": source(op["evidence"], user=True)
            patch = op["patch"]
            if not isinstance(patch, dict) or not patch or set(patch) - {"content", "semantics", "resolution"}: raise CICError("MODIFY may change content/semantics/resolution only")
            item.update(copy.deepcopy(patch))
            item["version"] += 1
            item["evidence"] += copy.deepcopy(op["evidence"])
            validate_named("node", item)
            invalidate_dependents(out, [tid])
        elif opcode in {"REVOKE", "SUSPEND", "COMPLETE"}:
            item = get_node(tid)
            source(op["evidence"], user=True)
            if item["lifecycle"] != "active": raise CICError("Lifecycle mutation requires active target")
            item["lifecycle"] = {"REVOKE": "revoked", "SUSPEND": "suspended", "COMPLETE": "completed"}[opcode]
            item["version"] += 1
            item["evidence"] += copy.deepcopy(op["evidence"])
            invalidate_dependents(out, [tid])
        elif opcode in {"REPLACE", "SUPERSEDE"}:
            item = get_node(tid)
            if item["lifecycle"] != "active": raise CICError("Replacement target inactive")
            source(op["evidence"], user=True)
            item["lifecycle"] = "superseded"
            item["version"] += 1
            item["evidence"] += copy.deepcopy(op["evidence"])
            add_node(op["value"])
            invalidate_dependents(out, [tid])
        elif opcode in {"CONFIRM", "SELECT"}:
            item = get_node(tid)
            if item["lifecycle"] != "active": raise CICError("Cannot adopt inactive target")
            value = op["value"]
            validate_named("adoption", value)
            source(value["evidence"], user=True)
            source(op["evidence"], user=True)
            expected = "confirmed" if opcode == "CONFIRM" else "selected"
            if value["relation"] != expected or value["target_id"] != tid or value["target_version"] != item["version"]: raise CICError("Adoption target/relation/version mismatch")
            if not value["fields"]: raise CICError("Adoption scope fields required")
            if set(value["fields"]) & set(value["exceptions"]): raise CICError("Adoption fields and exceptions overlap")
            if value["id"] in out["adoptions"]: raise Conflict("Adoption ID exists")
            if value["artifact_version"] is not None and f"{tid}@{value['artifact_version']}" not in out["artifacts"]: raise CICError("Unknown adopted artifact version")
            out["adoptions"][value["id"]] = copy.deepcopy(value)
            # Original origin/relation NEVER rewritten by selection/confirmation.
        elif opcode == "REFERENCE":
            value = op["value"]
            validate_named("reference", value)
            source(value["evidence"])
            if value["id"] in out["references"]: raise Conflict("Reference ID exists")
            validate_reference(value, out, lookup)
            out["references"][value["id"]] = copy.deepcopy(value)
        elif opcode == "RESOLVE":
            if tid in out["references"]:
                old = out["references"][tid]
                value = op["value"]
                validate_named("reference", value)
                if old["status"] != "unresolved" or value["status"] != "resolved" or value["id"] != tid: raise CICError("Invalid reference resolution")
                source(value["evidence"])
                validate_reference(value, out, lookup)
                out["references"][tid] = copy.deepcopy(value)
            else:
                item = get_node(tid)
                if item["role"] != "unknown" or item["resolution"] != "unresolved": raise CICError("RESOLVE targets an unresolved unknown/reference")
                if item["origin"] == "user" and item["relation"] == "explicit": source(op["evidence"], user=True)
                if not isinstance(op["value"], dict) or set(op["value"]) != {"content", "resolution"}: raise CICError("Resolution value requires content/resolution")
                if op["value"]["resolution"] not in {"resolved", "unverified"}: raise CICError("Resolution does not prove verification")
                item.update(op["value"])
                item["version"] += 1
                item["evidence"] += copy.deepcopy(op["evidence"])
        elif opcode == "REOPEN":
            item = get_node(tid)
            source(op["evidence"], user=True)
            if item["lifecycle"] not in {"suspended", "completed", "revoked", "expired"}: raise CICError("Target cannot reopen")
            item["lifecycle"] = "active"
            item["version"] += 1
            item["evidence"] += copy.deepcopy(op["evidence"])
        elif opcode in {"NARROW_SCOPE", "EXPAND_SCOPE"}:
            item = get_node(tid)
            source(op["evidence"], user=True)
            new_scope = op["value"]
            validate_scope(new_scope)
            old_scope = item["scope"]
            # Only finite target-set changes are supported. Empty means global.
            if {k: v for k, v in old_scope.items() if k != "targets"} != {k: v for k, v in new_scope.items() if k != "targets"}: raise CICError("Scope time/kind changes need REPLACE")
            a, b = set(old_scope["targets"]), set(new_scope["targets"])
            if opcode == "NARROW_SCOPE" and (not b or (a and not b < a)): raise CICError("Scope is not narrower")
            if opcode == "EXPAND_SCOPE" and (not a or (b and not a < b)): raise CICError("Scope is not wider")
            item["scope"] = copy.deepcopy(new_scope)
            item["version"] += 1
            item["evidence"] += copy.deepcopy(op["evidence"])
            invalidate_dependents(out, [tid])
        elif opcode == "NO_CHANGE":
            if tid is not None or op["value"] is not None or op["patch"] is not None: raise CICError("NO_CHANGE cannot hide mutations")
        else: raise CICError("Unsupported intent opcode")
        out["history"].append({"delta_id": delta["delta_id"], "operation": opcode, "target_id": tid, "evidence": copy.deepcopy(op["evidence"])})
    for ref in delta["unresolved"]:
        validate_named("reference", ref)
        if ref["status"] != "unresolved": raise CICError("Unresolved list contains resolved reference")
        source(ref["evidence"])
        validate_reference(ref, out, lookup)
        if ref["id"] in out["references"]: raise Conflict("Reference ID exists")
        out["references"][ref["id"]] = copy.deepcopy(ref)
    for op in delta["authority_operations"]:
        source(op["evidence"], user=True)
        if op["op"] == "GRANT" and op["target_id"] is not None: raise CICError("GRANT cannot target an existing authority")
        if op["op"] in {"REVOKE", "EXPIRE"} and op["value"] is not None: raise CICError("Unused authority value prohibited")
        if op["op"] == "GRANT":
            value = op["value"]
            validate_named("authority", value)
            validate_scope(value["scope"])
            source(value["evidence"], user=True, principal=value["principal"])
            if value["id"] in out["authorities"]: raise Conflict("Authority ID exists")
            if value["lifecycle"] != "active": raise CICError("Grant must be active")
            begin, end = parse_time(value["valid_from"]), parse_time(value["valid_until"])
            if begin and end and end <= begin: raise CICError("Authority interval invalid")
            if value["target_id"] not in out["nodes"]: raise CICError("Prototype authority targets are current node revisions only")
            if not target_exists(value["target_id"], value["target_version"], out, lookup): raise CICError("Authority target version missing")
            out["authorities"][value["id"]] = copy.deepcopy(value)
        else:
            aid = op["target_id"]
            if aid not in out["authorities"]: raise CICError("Unknown authority")
            item = out["authorities"][aid]
            source(op["evidence"], user=True, principal=item["principal"])
            if item["lifecycle"] != "active": raise CICError("Authority inactive")
            if op["op"] in {"REVOKE", "EXPIRE"}:
                item["lifecycle"] = "revoked" if op["op"] == "REVOKE" else "expired"
            elif op["op"] == "NARROW":
                patch = op["value"]
                if not isinstance(patch, dict) or not patch or set(patch) - {"conditions", "valid_until"}: raise CICError("Authority NARROW may add conditions/shorten duration only")
                if "conditions" in patch and not all(c in patch["conditions"] for c in item["conditions"]): raise CICError("Cannot remove authority condition")
                if "valid_until" in patch:
                    new_end = parse_time(patch["valid_until"])
                    old_end = parse_time(item["valid_until"])
                    if new_end is None or (old_end and new_end >= old_end): raise CICError("Cannot extend authority duration")
                item.update(copy.deepcopy(patch))
                validate_named("authority", item)
            else: raise CICError("Unsupported authority opcode")
            item["evidence"] += copy.deepcopy(op["evidence"])
    check_dependencies(out)
    out["pending_human"].remove(delta["human_event_id"])
    out["last_delta"] = copy.deepcopy(delta)
    validate_named("state", out)
    return out

def target_exists(tid, version, state, lookup):
    if tid in state["nodes"]: return state["nodes"][tid]["version"] == version
    if f"{tid}@{version}" in state["artifacts"]: return True
    ev = lookup(tid)
    return ev is not None and version == 1

def validate_reference(ref, state, lookup):
    seen = {}
    for candidate in ref["candidates"]:
        tid, ver = candidate["target_id"], candidate["version"]
        key = (tid, ver)
        if key in seen: raise CICError("Duplicate/ambiguous candidate ID-version; resolved target type not represented in this subset")
        seen[key] = candidate["type"]
        if candidate["type"] == "node": valid = tid in state["nodes"] and state["nodes"][tid]["version"] == ver
        elif candidate["type"] == "artifact": valid = f"{tid}@{ver}" in state["artifacts"]
        else: valid = lookup(tid) is not None and ver == 1
        if not valid: raise CICError("Reference candidate/version missing")
    if ref["status"] == "resolved":
        if not any(c["target_id"] == ref["resolved_target"] and c["version"] == ref["resolved_version"] for c in ref["candidates"]): raise CICError("Resolved target not among candidates")
    elif ref["resolved_target"] is not None or ref["resolved_version"] is not None: raise CICError("Unresolved reference cannot have committed target")

def reduce_event(state, event, lookup):
    out = copy.deepcopy(state)
    if event["kind"] == "interpretation":
        out = apply_delta(out, event["attrs"]["delta"], lookup)
    elif event["kind"] == "human":
        out["pending_human"].append(event["event_id"])
    elif event["kind"] == "artifact":
        artifact = event["attrs"]["artifact"]
        validate_named("artifact", artifact)
        key = f"{artifact['artifact_id']}@{artifact['version']}"
        if key in out["artifacts"]: raise Conflict("Artifact version immutable")
        if lookup(artifact["created_by"]) is None: raise MissingSource("Artifact source missing")
        out["artifacts"][key] = copy.deepcopy(artifact)
    elif event["kind"] == "tick":
        now = event["attrs"]["now"]
        parse_time(now)
        if out["clock"] and parse_time(now) < parse_time(out["clock"]): raise CICError("Projection clock cannot move backwards")
        out["clock"] = now
        expired = []
        for nid, item in out["nodes"].items():
            until = item["scope"]["valid_until"]
            if item["lifecycle"] == "active" and until and parse_time(now) >= parse_time(until):
                item["lifecycle"] = "expired"
                item["version"] += 1
                expired.append(nid)
        invalidate_dependents(out, expired)
        for item in out["authorities"].values():
            ends = [parse_time(t) for t in [item["valid_until"], item["scope"]["valid_until"]] if t]
            if item["lifecycle"] == "active" and ends and parse_time(now) >= min(ends): item["lifecycle"] = "expired"
    elif event["kind"] == "fork":
        out["lineage"].append({"branch_id": event["attrs"]["parent_branch"], "watermark": event["attrs"]["parent_watermark"]})
    out["state_version"] += 1
    out["watermark"] = event["seq"]
    validate_named("state", out)
    return out

class Ledger:
    def __init__(self, path=":memory:"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          event_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, branch_id TEXT NOT NULL,
          seq INTEGER NOT NULL, payload TEXT NOT NULL, request_sha256 TEXT NOT NULL,
          UNIQUE(conversation_id,branch_id,seq));
        CREATE TABLE IF NOT EXISTS projections (
          conversation_id TEXT NOT NULL, branch_id TEXT NOT NULL,
          state TEXT NOT NULL, PRIMARY KEY(conversation_id,branch_id));
        CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
          BEGIN SELECT RAISE(ABORT,'immutable ledger: UPDATE prohibited'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
          BEGIN SELECT RAISE(ABORT,'immutable ledger: DELETE prohibited'); END;
        """)

    def close(self): self.db.close()

    def state(self, conversation="c1", branch="main"):
        row = self.db.execute("SELECT state FROM projections WHERE conversation_id=? AND branch_id=?", (conversation, branch)).fetchone()
        if row:
            value = json.loads(row[0])
            validate_named("state", value)
            return value
        return empty_state(conversation, branch)

    def _save(self, state):
        self.db.execute("INSERT INTO projections VALUES (?,?,?) ON CONFLICT(conversation_id,branch_id) DO UPDATE SET state=excluded.state",
                        (state["conversation_id"], state["branch_id"], canonical(state)))

    def event(self, event_id):
        row = self.db.execute("SELECT payload FROM events WHERE event_id=?", (event_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def events(self, conversation="c1", branch="main", watermark=None):
        query = "SELECT payload FROM events WHERE conversation_id=? AND branch_id=?"
        params = [conversation, branch]
        if watermark is not None:
            query += " AND seq<=?"
            params.append(watermark)
        query += " ORDER BY seq"
        return [json.loads(r[0]) for r in self.db.execute(query, params)]

    def allowed_event_ids(self, conversation, branch, watermark=None, _seen=None):
        seen = _seen or set()
        if branch in seen: raise IntegrityError("Branch lineage cycle")
        seen = seen | {branch}
        events = self.events(conversation, branch, watermark)
        allowed = {ev["event_id"] for ev in events}
        for ev in events:
            if ev["kind"] == "fork":
                allowed |= self.allowed_event_ids(conversation, ev["attrs"]["parent_branch"], ev["attrs"]["parent_watermark"], seen)
        return allowed

    def _lookup(self, conversation, branch, watermark=None):
        allowed = self.allowed_event_ids(conversation, branch, watermark)
        def find(eid):
            if eid not in allowed: return None
            return self.event(eid)
        return find

    def _append(self, request):
        fingerprint = digest(request)
        existing = self.event(request["event_id"])
        if existing:
            if existing["request_sha256"] != fingerprint: raise Conflict("Same event ID with different content")
            return existing, True
        conversation, branch = request["conversation_id"], request["branch_id"]
        state = self.state(conversation, branch)
        previous = self.events(conversation, branch)
        # Cache corruption is detected before a new event can hide it.
        replayed = self.replay(conversation, branch)
        if replayed != state: raise IntegrityError("Projection cache differs from replay; rebuild explicitly")
        ev = {"schema_version": VERSION, "compiler_version": COMPILER_VERSION, **copy.deepcopy(request),
              "seq": state["watermark"] + 1, "recorded_at": utc_now(), "raw_sha256": raw_digest(request["raw"]),
              "request_sha256": fingerprint, "prev_event_hash": previous[-1]["event_hash"] if previous else None}
        ev["event_hash"] = digest(ev)
        validate_named("event", ev)
        lookup = self._lookup(conversation, branch)
        if any(lookup(eid) is None for eid in ev["parent_ids"] + ev["reference_ids"]): raise MissingSource("Event parent/reference missing or outside branch")
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (ev["event_id"], conversation, branch, ev["seq"], canonical(ev), fingerprint))
        projected = reduce_event(state, ev, self._lookup(conversation, branch))
        self._save(projected)
        return ev, False

    def capture(self, event_id, raw, *, conversation="c1", branch="main", origin="user", kind=None,
                principal="human-1", trusted_identity=True, attrs=None, parent_ids=None, reference_ids=None, effective_at=None):
        kind = kind or {"user": "human", "assistant": "assistant", "tool": "tool_result", "external": "external", "compiler": "external"}[origin]
        if kind in {"interpretation", "fork"}: raise CICError("Use commit/fork for structural events")
        if kind == "human" and origin != "user": raise CICError("Human event must originate with user")
        if kind != "human" and origin == "user": raise CICError("User origin requires human event")
        parse_time(effective_at)
        request = {"event_id": event_id, "conversation_id": conversation, "branch_id": branch,
                   "origin": origin, "kind": kind, "principal": principal if origin == "user" else None,
                   "trusted_identity": trusted_identity if origin == "user" else False,
                   "raw": raw, "effective_at": effective_at, "parent_ids": parent_ids or [],
                   "reference_ids": reference_ids or [], "attrs": attrs or {}}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            ev, duplicate = self._append(request)
            self.db.execute("COMMIT")
            return {"event": ev, "duplicate": duplicate, "state": self.state(conversation, branch)}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def delta(self, human_event_id, operations=None, authority_operations=None, unresolved=None, delta_id=None):
        human = self.event(human_event_id)
        if not human: raise MissingSource(human_event_id)
        state = self.state(human["conversation_id"], human["branch_id"])
        return {"schema_version": VERSION, "delta_id": delta_id or "d-" + human_event_id,
                "conversation_id": human["conversation_id"], "branch_id": human["branch_id"],
                "human_event_id": human_event_id, "base_state_version": state["state_version"],
                "base_watermark": state["watermark"], "operations": operations or [],
                "authority_operations": authority_operations or [], "unresolved": unresolved or [],
                "interpretation_method": "hand_authored_fixture"}

    def commit(self, delta):
        validate_named("delta", delta)
        conversation, branch = delta["conversation_id"], delta["branch_id"]
        request = {"event_id": "interpretation:" + delta["delta_id"], "conversation_id": conversation, "branch_id": branch,
                   "origin": "compiler", "kind": "interpretation", "principal": None, "trusted_identity": False,
                   "raw": "", "effective_at": None, "parent_ids": [delta["human_event_id"]],
                   "reference_ids": [], "attrs": {"delta": copy.deepcopy(delta), "semantic_correctness": "unverified"}}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            ev, duplicate = self._append(request)
            self.db.execute("COMMIT")
            return {"event": ev, "duplicate": duplicate, "state": self.state(conversation, branch)}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def fork(self, new_branch, *, conversation="c1", parent_branch="main", parent_watermark=None):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.events(conversation, new_branch): raise Conflict("Branch already exists")
            parent = self.replay(conversation, parent_branch, parent_watermark)
            if parent["pending_human"]: raise CICError("Prototype requires parent pending human inputs to be committed before fork")
            parent_watermark = parent["watermark"]
            inherited = copy.deepcopy(parent)
            inherited["branch_id"] = new_branch
            inherited["watermark"] = 0
            self._save(inherited)
            request = {"event_id": f"fork:{conversation}:{new_branch}", "conversation_id": conversation, "branch_id": new_branch,
                       "origin": "compiler", "kind": "fork", "principal": None, "trusted_identity": False,
                       "raw": "", "effective_at": None, "parent_ids": [], "reference_ids": [],
                       "attrs": {"parent_branch": parent_branch, "parent_watermark": parent_watermark, "parent_state_hash": digest(parent)}}
            # Initial inherited cache is matched by replay below via seed override.
            fingerprint = digest(request)
            ev = {"schema_version": VERSION, "compiler_version": COMPILER_VERSION, **request, "seq": 1,
                  "recorded_at": utc_now(), "raw_sha256": raw_digest(""), "request_sha256": fingerprint, "prev_event_hash": None}
            ev["event_hash"] = digest(ev)
            validate_named("event", ev)
            self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (ev["event_id"], conversation, new_branch, 1, canonical(ev), fingerprint))
            self._save(reduce_event(inherited, ev, self._lookup(conversation, new_branch)))
            self.db.execute("COMMIT")
            return self.state(conversation, new_branch)
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def replay(self, conversation="c1", branch="main", watermark=None, _seen=None):
        seen = _seen or set()
        if branch in seen: raise IntegrityError("Branch lineage cycle")
        events = self.events(conversation, branch, watermark)
        state = empty_state(conversation, branch)
        prev_hash = None
        for index, ev in enumerate(events, 1):
            validate_named("event", ev)
            content = {k: v for k, v in ev.items() if k != "event_hash"}
            if ev["seq"] != index or ev["prev_event_hash"] != prev_hash or digest(content) != ev["event_hash"] or raw_digest(ev["raw"]) != ev["raw_sha256"]:
                raise IntegrityError("Ledger chain/raw integrity mismatch")
            if ev["compiler_version"] != COMPILER_VERSION or ev["schema_version"] != VERSION: raise CICError("Unsupported historical projector/schema version; migration required")
            if ev["kind"] == "fork":
                if index != 1: raise IntegrityError("Fork must be branch's first event")
                attrs = ev["attrs"]
                state = self.replay(conversation, attrs["parent_branch"], attrs["parent_watermark"], seen | {branch})
                if digest(state) != attrs["parent_state_hash"]: raise IntegrityError("Fork parent state mismatch")
                state["branch_id"] = branch
                state["watermark"] = 0
            lookup = self._lookup(conversation, branch, ev["seq"])
            if any(lookup(eid) is None for eid in ev["parent_ids"] + ev["reference_ids"]): raise MissingSource("Ledger reference missing")
            state = reduce_event(state, ev, lookup)
            prev_hash = ev["event_hash"]
        return state

    def rebuild(self, conversation="c1", branch="main"):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rebuilt = self.replay(conversation, branch)
            self._save(rebuilt)
            self.db.execute("COMMIT")
            return rebuilt
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def add_artifact(self, event_id, artifact_id, version, path, created_by, *, conversation="c1", branch="main", media_type="text/plain"):
        p = Path(path).resolve(strict=True)
        value = {"artifact_id": artifact_id, "version": version, "path": str(p),
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "created_by": created_by, "media_type": media_type}
        return self.capture(event_id, "", conversation=conversation, branch=branch, origin="tool", kind="artifact",
                            attrs={"artifact": value}, reference_ids=[created_by])

    def tick(self, event_id, now, *, conversation="c1", branch="main"):
        parse_time(now)
        return self.capture(event_id, "", conversation=conversation, branch=branch, origin="compiler", kind="tick", attrs={"now": now})

    def preflight(self, actor, action, target_id, target_version, *, now, conversation="c1", branch="main", conditions=None, turn_id=None, task_id=None):
        """Read-only preflight certificate, NOT a side effect or durable permission."""
        parse_time(now)
        state = self.state(conversation, branch)
        if state != self.replay(conversation, branch): raise IntegrityError("Projection stale/corrupt")
        reasons = []
        if state["pending_human"]: reasons.append("pending_human_interpretation")
        if any(r["status"] == "unresolved" and r["behavior_changes"] for r in state["references"].values()): reasons.append("unresolved_behavior_changing_reference")
        target_ok = target_exists(target_id, target_version, state, self._lookup(conversation, branch))
        if target_id in state["nodes"] and not effective(state["nodes"][target_id], now, turn_id, task_id): target_ok = False
        if not target_ok: reasons.append("target_version_unavailable_or_inactive")
        conditions = conditions or {}
        matches = []
        for aid, item in state["authorities"].items():
            if (item["actor"], item["action"], item["target_id"], item["target_version"]) != (actor, action, target_id, target_version): continue
            if item["scope"]["targets"] and target_id not in item["scope"]["targets"]: continue
            if not effective(item, now, turn_id, task_id): continue
            if any(conditions.get(c["name"], object()) != c["equals"] for c in item["conditions"]): continue
            validate_evidence(item["evidence"], self._lookup(conversation, branch), user=True, principal=item["principal"])
            matches.append(aid)
        if not matches: reasons.append("no_applicable_authority")
        return {"allowed": not reasons, "reasons": reasons, "authority_ids": matches,
                "conversation_id": conversation, "branch_id": branch, "state_version": state["state_version"],
                "watermark": state["watermark"], "checked_at": now, "target_id": target_id, "target_version": target_version,
                "actor": actor, "action": action, "conditions": conditions, "turn_id": turn_id, "task_id": task_id,
                "warning": "External executor must recheck immediately before side effect; this prototype never executes it."}

    def gate_is_current(self, gate, *, now):
        state = self.state(gate["conversation_id"], gate["branch_id"])
        if parse_time(now) < parse_time(gate["checked_at"]): raise CICError("Gate clock cannot move backwards")
        if not gate["allowed"] or (state["state_version"], state["watermark"]) != (gate["state_version"], gate["watermark"]): return False
        fresh = self.preflight(gate["actor"], gate["action"], gate["target_id"], gate["target_version"], now=now,
                               conversation=gate["conversation_id"], branch=gate["branch_id"], conditions=gate["conditions"],
                               turn_id=gate["turn_id"], task_id=gate["task_id"])
        return fresh["allowed"]

    def package(self, human_event_id, *, now, routing="ANNOTATE", node_ids=None, task_id=None, required_event_ids=None):
        human = self.event(human_event_id)
        if human is None: raise MissingSource("Current human raw missing")
        if human["kind"] != "human": raise CICError("Turn requires human event")
        state = self.state(human["conversation_id"], human["branch_id"])
        if state != self.replay(human["conversation_id"], human["branch_id"]): raise IntegrityError("Projection differs from replay")
        if state["pending_human"]: raise CICError("All captured human corrections must be interpreted/committed before packaging")
        if not state["last_delta"] or state["last_delta"]["human_event_id"] != human_event_id: raise Conflict("Package current committed human turn only")
        lookup = self._lookup(human["conversation_id"], human["branch_id"])
        chosen = set(node_ids or [])
        # Baseline conservative closure: all applicable constraints/prohibitions/latitude/unknown.
        chosen |= {nid for nid, n in state["nodes"].items() if n["role"] in {"constraint", "prohibition", "latitude", "unknown"} and effective(n, now, human_event_id, task_id)}
        for adoption in state["adoptions"].values():
            if adoption["relation"] in {"selected", "confirmed"}: chosen.add(adoption["target_id"])
        pending = list(chosen)
        while pending:
            nid = pending.pop()
            if nid not in state["nodes"]: raise CICError("Context node missing: " + nid)
            for parent in state["nodes"][nid]["dependencies"]:
                if parent not in chosen:
                    chosen.add(parent)
                    pending.append(parent)
        active = [copy.deepcopy(state["nodes"][nid]) for nid in sorted(chosen) if effective(state["nodes"][nid], now, human_event_id, task_id)]
        evs = [evidence(human)]
        for item in active: evs += item["evidence"]
        adoptions = [copy.deepcopy(a) for a in state["adoptions"].values() if a["target_id"] in chosen]
        refs = list(copy.deepcopy(state["references"]).values())
        authorities = list(copy.deepcopy(state["authorities"]).values())  # Include revoked boundaries, not only grants.
        for item in adoptions + refs + authorities: evs += item["evidence"]
        # Include source history for modifications/revocations affecting dependency closure.
        for hist in state["history"]:
            if hist["target_id"] in chosen: evs += hist["evidence"]
        required = set(required_event_ids or []) | {e["event_id"] for e in evs}
        delivered, missing, source_rows = set(), set(), []
        unique = {}
        for e in evs: unique[(e["event_id"], e["start"], e["end"])] = e
        for eid in sorted(required):
            ev = lookup(eid)
            if ev is None: missing.add(eid)
            else:
                delivered.add(eid)
                matching = [e for e in unique.values() if e["event_id"] == eid] or [evidence(ev)]
                for e in matching:
                    validate_evidence([e], lookup)
                    source_rows.append({"evidence": copy.deepcopy(e), "origin": ev["origin"], "raw_sha256": ev["raw_sha256"]})
        omissions = ["Nonselected goals/proposals and unrelated raw history omitted by finite closure policy.",
                     "Coverage ratio measures declared required-event set, not semantic sufficiency."]
        artifacts = []
        for item in state["artifacts"].values():
            artifacts.append(copy.deepcopy(item))
            p = Path(item["path"])
            if not p.exists(): omissions.append(f"Artifact content missing: {item['artifact_id']}@{item['version']}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]: omissions.append(f"Artifact content hash changed: {item['artifact_id']}@{item['version']}")
        ir = {"schema_version": VERSION, "compiler_version": COMPILER_VERSION,
              "conversation_id": state["conversation_id"], "branch_id": state["branch_id"], "turn_id": human_event_id,
              "human_raw": human["raw"], "human_raw_sha256": human["raw_sha256"],
              "base_state_version": state["state_version"], "ledger_watermark": state["watermark"],
              "routing": routing, "intent_delta": copy.deepcopy(state["last_delta"]),
              "active_requirements": active, "adoptions": adoptions, "references": refs,
              "authority_boundaries": authorities, "artifacts": artifacts, "source_evidence": source_rows,
              "open_unknown": [n["id"] for n in active if n["resolution"] == "unresolved" or (n["role"] == "unknown" and n["resolution"] not in {"resolved", "verified"})] + [r["id"] for r in refs if r["status"] == "unresolved"],
              "context_coverage": {"required_event_ids": sorted(required), "delivered_event_ids": sorted(delivered),
                                   "missing_event_ids": sorted(missing), "ratio": len(delivered) / len(required) if required else 1.0,
                                   "missing_sources": [{"event_id": eid, "retrieval_status": "unavailable", "detail": "Not in allowed ledger view; absent versus deleted is not established."} for eid in sorted(missing)],
                                   "selection_policy": "conservative invariant + selected-node dependency/evidence closure v0.1",
                                   "known_omissions": omissions},
              "validation": {"schema": True, "deterministic": True, "semantic": "not_run"},
              "limitations": ["Candidate deltas are hand authored; natural-language parsing/routing/resolution is not implemented.",
                              "Schema/evidence/transition validation does not prove semantic correctness.",
                              "Missing evidence/artifact content must block affected work; independent read-only work may continue."]}
        validate_named("turn_ir", ir)
        return ir
