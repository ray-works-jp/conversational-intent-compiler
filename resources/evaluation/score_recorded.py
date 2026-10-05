"""Score externally labeled observations. No model calls or semantic labeling."""
import argparse
import json
import math
import random
from pathlib import Path

CONDITIONS = ("A", "B", "C", "D", "E")
RATE_UP = {"constraint_survival", "intent_delta_accuracy", "revocation_compliance",
           "unresolved_state_preservation", "latitude_preservation", "reference_resolution",
           "context_coverage", "replay_consistency", "downstream_task_success", "request_recall",
           "negation_fidelity", "number_fidelity", "actor_fidelity", "datetime_fidelity",
           "tool_selection_accuracy", "tool_arguments_accuracy", "injection_resistance",
           "pass_precision", "pass_recall"}
RATE_DOWN = {"semantic_drift", "stale_intent_rate", "ai_proposal_contamination",
             "authority_drift", "invented_constraint_rate"}
MEANS = {"confirmation_burden", "input_tokens", "output_tokens", "tool_tokens",
         "latency_ms", "cost_usd"}
METRICS = sorted(RATE_UP | RATE_DOWN | MEANS)


def validate_manifest(manifest):
    required = {"run_id", "evaluation_kind", "environment", "model_settings", "conditions",
                "primary_metrics", "noninferiority", "max_cost", "labeling_protocol",
                "measurement_status"}
    missing = required - set(manifest)
    if missing:
        raise ValueError("missing manifest fields: " + ", ".join(sorted(missing)))
    if manifest["evaluation_kind"] not in {"replay", "closed_loop"}:
        raise ValueError("evaluation_kind must be replay or closed_loop")
    if manifest["environment"] not in {"api", "work", "synthetic"}:
        raise ValueError("environment must be api, work, or synthetic")
    if not isinstance(manifest["model_settings"], dict) or not {"model", "reasoning", "snapshot"} <= set(manifest["model_settings"]):
        raise ValueError("model_settings requires model, reasoning, snapshot")
    if manifest["measurement_status"] not in {"synthetic_selfcheck", "recorded_observations"}:
        raise ValueError("measurement_status invalid")
    if manifest["environment"] == "synthetic" and manifest["measurement_status"] != "synthetic_selfcheck":
        raise ValueError("synthetic environment cannot masquerade as measured model observations")
    if set(manifest["conditions"]) != set(CONDITIONS):
        raise ValueError("conditions must include A through E; mark unavailable arms unexecuted")
    shared = []
    for condition, details in manifest["conditions"].items():
        if not {"implementation", "access_manifest", "context_budget_tokens", "status"} <= set(details):
            raise ValueError(f"condition {condition} lacks implementation/access/budget/status")
        if details["status"] not in {"executed", "unexecuted", "unavailable"}:
            raise ValueError("unknown condition status")
        if isinstance(details["context_budget_tokens"], bool) or not isinstance(details["context_budget_tokens"], int) or details["context_budget_tokens"] <= 0:
            raise ValueError("positive integer context budget required")
        if not isinstance(details["access_manifest"], dict) or not details["access_manifest"]:
            raise ValueError("nonempty access manifest required, including raw/artifact/tool access")
        shared.append((json.dumps(details["access_manifest"], sort_keys=True), details["context_budget_tokens"]))
    if len(set(shared)) != 1:
        raise ValueError("comparison rejected: unequal declared information access or context budget")
    if not manifest["primary_metrics"] or any(m not in METRICS for m in manifest["primary_metrics"]):
        raise ValueError("known primary metrics required")
    if not isinstance(manifest["noninferiority"], dict) or not manifest["noninferiority"]:
        raise ValueError("predeclared noninferiority margins required")
    if not isinstance(manifest["max_cost"], dict) or not manifest["max_cost"]:
        raise ValueError("predeclared acceptable cost limits required")
    if not isinstance(manifest["labeling_protocol"], dict) or not {"gold_source", "blind", "human_adjudication"} <= set(manifest["labeling_protocol"]):
        raise ValueError("gold, blind-evaluation and human-adjudication protocol required")


def validate_observation(row, manifest):
    required = {"observation_id", "conversation_id", "condition", "metric", "numerator",
                "denominator", "evidence_source", "evidence_ids"}
    if not required <= set(row):
        raise ValueError("observation missing required fields")
    if not all(isinstance(row[k], str) and row[k] for k in ("observation_id", "conversation_id")):
        raise ValueError("observation/conversation IDs must be nonempty strings")
    if row["condition"] not in CONDITIONS or row["metric"] not in METRICS:
        raise ValueError("unknown condition/metric")
    if manifest["conditions"][row["condition"]]["status"] != "executed":
        raise ValueError("observations supplied for an unexecuted/unavailable condition")
    for field in ("numerator", "denominator"):
        if isinstance(row[field], bool) or not isinstance(row[field], (int, float)) or not math.isfinite(row[field]) or row[field] < 0:
            raise ValueError("finite nonnegative numeric counter required")
    if row["denominator"] == 0:
        raise ValueError("omit missing/nonapplicable observations; denominator must be positive")
    if row["metric"] not in MEANS and row["numerator"] > row["denominator"]:
        raise ValueError("rate numerator exceeds denominator")
    if row["evidence_source"] not in {"deterministic", "human_adjudicated", "external_evaluator", "synthetic"}:
        raise ValueError("evidence source invalid")
    if not isinstance(row["evidence_ids"], list) or not row["evidence_ids"] or not all(isinstance(v, str) and v for v in row["evidence_ids"]):
        raise ValueError("nonempty source/adjudication evidence IDs required")
    if row["evidence_source"] == "synthetic" and manifest["measurement_status"] != "synthetic_selfcheck":
        raise ValueError("synthetic labels cannot be counted as real observations")
    if manifest["measurement_status"] == "synthetic_selfcheck" and row["evidence_source"] != "synthetic":
        raise ValueError("selfcheck observations must be explicitly synthetic")


def counter_view(counter):
    numerator, denominator = counter
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None,
            "status": "observed" if denominator else "N/A"}


def quantile(values, p):
    values = sorted(values)
    at = (len(values) - 1) * p
    lo = int(at)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (at - lo)


def bootstrap_pair(clusters, left, right, metric, repetitions, seed, confidence):
    ids = sorted(cid for cid, group in clusters.items() if metric in group.get(left, {}) and metric in group.get(right, {}))
    if len(ids) < 2:
        return {"status": "N/A", "reason": "at least two paired conversations required", "paired_conversations": len(ids)}
    def difference(selected):
        totals = {}
        for arm in (left, right):
            n = sum(clusters[cid][arm][metric][0] for cid in selected)
            d = sum(clusters[cid][arm][metric][1] for cid in selected)
            totals[arm] = n / d
        return totals[right] - totals[left]
    rng = random.Random(seed)
    samples = [difference(rng.choices(ids, k=len(ids))) for _ in range(repetitions)]
    alpha = (1 - confidence) / 2
    return {"status": "observed", "paired_conversations": len(ids), "conversation_ids": ids,
            "estimand": f"{right} minus {left}: ratio of summed counters on paired trajectories",
            "difference": difference(ids), "ci_low": quantile(samples, alpha),
            "ci_high": quantile(samples, 1 - alpha), "confidence": confidence,
            "repetitions": repetitions, "seed": seed,
            "caution": "descriptive interval; no multiplicity correction or automatic improvement claim"}


def score(manifest, observations, repetitions=2000, seed=7, confidence=0.95):
    validate_manifest(manifest)
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1 or not 0 < confidence < 1:
        raise ValueError("positive repetitions and confidence in (0,1) required")
    clusters, seen, evidence_counts = {}, set(), {}
    for row in observations:
        validate_observation(row, manifest)
        if row["observation_id"] in seen:
            raise ValueError("duplicate observation ID; refusing double count")
        seen.add(row["observation_id"])
        counter = clusters.setdefault(row["conversation_id"], {}).setdefault(row["condition"], {}).setdefault(row["metric"], [0, 0])
        counter[0] += row["numerator"]
        counter[1] += row["denominator"]
        evidence_counts[row["evidence_source"]] = evidence_counts.get(row["evidence_source"], 0) + 1
    totals = {arm: {metric: [0, 0] for metric in METRICS} for arm in CONDITIONS}
    per_conversation = {}
    for cid, group in sorted(clusters.items()):
        per_conversation[cid] = {}
        for arm in CONDITIONS:
            per_conversation[cid][arm] = {}
            for metric in METRICS:
                counter = group.get(arm, {}).get(metric, [0, 0])
                totals[arm][metric][0] += counter[0]
                totals[arm][metric][1] += counter[1]
                per_conversation[cid][arm][metric] = counter_view(counter)
    comparisons = {}
    for left, right in [("A", "B"), ("A", "C"), ("A", "D"), ("A", "E"), ("D", "E")]:
        comparisons[f"{left}:{right}"] = {metric: bootstrap_pair(clusters, left, right, metric, repetitions, seed, confidence) for metric in METRICS}
    return {"run_id": manifest["run_id"], "evaluation_kind": manifest["evaluation_kind"],
            "environment": manifest["environment"], "measurement_status": manifest["measurement_status"],
            "model_called_by_scorer": False, "semantic_labels_generated_by_scorer": False,
            "fairness": "declared access/budgets match; factual equality requires external audit",
            "observation_count": len(seen), "conversation_count": len(clusters),
            "evidence_source_counts": evidence_counts, "per_conversation": per_conversation,
            "aggregate": {arm: {metric: counter_view(v) for metric, v in by_metric.items()} for arm, by_metric in totals.items()},
            "paired_cluster_bootstrap": comparisons,
            "metric_types": {metric: {"aggregation": "mean" if metric in MEANS else "rate",
                                      "preferred_direction": "increase" if metric in RATE_UP else "decrease"} for metric in METRICS},
            "limitations": ["Gold labels and their semantic validity are external inputs.",
                            "No automatic noninferiority or success decision is made.",
                            "Missing observations are N/A, never zero failures.",
                            "Paired bootstrap excludes unpaired conversations; inspect missingness.",
                            "Turn observations are clustered within whole conversation IDs."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    observations = [json.loads(line) for line in args.observations.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    result = score(manifest, observations, args.bootstrap_repetitions, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(args.output.resolve()), "measurement_status": result["measurement_status"], "observations": result["observation_count"]}))


if __name__ == "__main__":
    main()
