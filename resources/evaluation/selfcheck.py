"""Synthetic arithmetic/policy checks. Not a benchmark of any compiler/model."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from score_recorded import CONDITIONS, score
from user_policy import AmbiguousPolicyTarget, choose_actual_proposal, request_availability


def manifest_fixture():
    access = {"raw_event_ids": ["fixture:h1", "fixture:a1", "fixture:h2"],
              "artifacts": ["fixture:proposal-set@1"], "tools": ["fixture:availability"],
              "lookup_policy": "same access permissions and evidence pool in all arms"}
    return {"run_id": "synthetic-selfcheck-only", "evaluation_kind": "replay", "environment": "synthetic",
            "measurement_status": "synthetic_selfcheck", "model_settings": {"model": "none_called", "reasoning": "none", "snapshot": "not_applicable"},
            "conditions": {arm: {"implementation": "synthetic counter fixture; no arm executed as a model",
                                "access_manifest": copy.deepcopy(access), "context_budget_tokens": 8192, "status": "executed"} for arm in CONDITIONS},
            "primary_metrics": ["constraint_survival", "authority_drift"],
            "noninferiority": {"clear_task_success_margin": 0.02, "note": "example preregistration, not a chosen scientific threshold"},
            "max_cost": {"relative_total_cost_ratio": 1.25, "note": "example only; actual experiment must preregister"},
            "labeling_protocol": {"gold_source": "synthetic fixture", "blind": False, "human_adjudication": "not a real evaluation"}}


def observations_fixture():
    rows = []
    for cid in ("fixture:conversation1", "fixture:conversation2"):
        for arm in CONDITIONS:
            for metric, n, d in (("constraint_survival", 1, 2), ("input_tokens", 100, 1)):
                rows.append({"observation_id": f"{cid}:{arm}:{metric}", "conversation_id": cid, "condition": arm,
                             "metric": metric, "numerator": n, "denominator": d,
                             "evidence_source": "synthetic", "evidence_ids": ["fixture:counter"]})
    return rows


def expect_raises(fn, exception=ValueError):
    try:
        fn()
    except exception:
        return
    raise AssertionError("expected failure was not raised")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-fixtures", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest, rows = manifest_fixture(), observations_fixture()
    results = []
    def test(name, fn):
        fn()
        results.append({"test": name, "passed": True})
    result = score(manifest, rows, repetitions=200, seed=71)
    test("explicit_synthetic_status", lambda: assert_equal(result["measurement_status"], "synthetic_selfcheck"))
    test("per_conversation_numerator_denominator", lambda: assert_equal(result["per_conversation"]["fixture:conversation1"]["D"]["constraint_survival"], {"numerator": 1, "denominator": 2, "value": 0.5, "status": "observed"}))
    test("missing_is_NA", lambda: assert_equal(result["aggregate"]["A"]["authority_drift"]["status"], "N/A"))
    test("mean_tokens_are_not_rate_bounded", lambda: assert_equal(result["aggregate"]["A"]["input_tokens"]["value"], 100))
    test("paired_cluster_bootstrap_identical_arms_zero", lambda: assert_equal(result["paired_cluster_bootstrap"]["A:D"]["constraint_survival"]["difference"], 0))
    test("bootstrap_seed_reproducible", lambda: assert_equal(result, score(manifest, rows, repetitions=200, seed=71)))
    test("duplicate_observation_rejected", lambda: expect_raises(lambda: score(manifest, rows + [rows[0]], 20)))
    wrong = copy.deepcopy(manifest)
    wrong["conditions"]["D"]["context_budget_tokens"] = 16000
    test("unequal_context_budget_rejected", lambda: expect_raises(lambda: score(wrong, rows, 20)))
    wrong_access = copy.deepcopy(manifest)
    wrong_access["conditions"]["D"]["access_manifest"]["raw_event_ids"].append("extra evidence")
    test("unequal_declared_access_rejected", lambda: expect_raises(lambda: score(wrong_access, rows, 20)))
    invalid = copy.deepcopy(rows)
    invalid[0]["numerator"] = 3
    test("invalid_rate_counter_rejected", lambda: expect_raises(lambda: score(manifest, invalid, 20)))
    zero = copy.deepcopy(rows)
    zero[0]["denominator"] = 0
    test("zero_denominator_omitted_not_zero_score", lambda: expect_raises(lambda: score(manifest, zero, 20)))
    real = copy.deepcopy(manifest)
    real["environment"] = "api"
    real["measurement_status"] = "recorded_observations"
    test("synthetic_labels_cannot_masquerade_as_measurement", lambda: expect_raises(lambda: score(real, rows, 20)))
    one = [row for row in rows if row["conversation_id"] == "fixture:conversation1"]
    test("one_conversation_bootstrap_NA", lambda: assert_equal(score(manifest, one, 20)["paired_cluster_bootstrap"]["A:D"]["constraint_survival"]["status"], "N/A"))
    unexecuted = copy.deepcopy(manifest)
    unexecuted["conditions"]["B"]["status"] = "unexecuted"
    test("observations_for_unexecuted_arm_rejected", lambda: expect_raises(lambda: score(unexecuted, rows, 20)))
    response_a = {"event_id": "a:A", "candidate_sets": [{"set_id": "set:A", "version": 1, "scenario_key": "trip",
                 "options": [{"proposal_id": "p:cheap:A", "version": 1, "scenario_key": "cheap", "display_ordinal": 2},
                             {"proposal_id": "p:scenic:A", "version": 1, "scenario_key": "scenic", "display_ordinal": 1}]}]}
    response_d = {"event_id": "a:D", "candidate_sets": [{"set_id": "set:D", "version": 4, "scenario_key": "trip",
                 "options": [{"proposal_id": "p:cheap:D", "version": 3, "scenario_key": "cheap", "display_ordinal": 1},
                             {"proposal_id": "p:scenic:D", "version": 2, "scenario_key": "scenic", "display_ordinal": 2}]}]}
    choice_a = choose_actual_proposal(response_a, "trip", "cheap")
    choice_d = choose_actual_proposal(response_d, "trip", "cheap")
    test("closed_loop_adapts_number_to_each_actual_response", lambda: assert_equal((choice_a["human_raw"], choice_d["human_raw"]), ("2番で。ホテルだけもう少し安くして。", "1番で。ホテルだけもう少し安くして。")))
    test("closed_loop_preserves_seen_target_version", lambda: assert_equal(choice_d["expected_reference"]["proposal_version"], 3))
    test("choice_does_not_confirm_AI_assumptions", lambda: assert_equal(choice_d["adoption_scope"]["ai_assumptions_confirmed"], False))
    test("choice_does_not_grant_booking_authority", lambda: assert_equal(choice_d["authority_change"], None))
    missing = copy.deepcopy(response_d)
    missing["candidate_sets"][0]["options"] = []
    test("missing_target_requires_policy_clarification", lambda: expect_raises(lambda: choose_actual_proposal(missing, "trip", "cheap"), AmbiguousPolicyTarget))
    multiple = copy.deepcopy(response_a)
    multiple["candidate_sets"].append(copy.deepcopy(multiple["candidate_sets"][0]))
    test("multiple_numbered_sets_not_recency_guessed", lambda: expect_raises(lambda: choose_actual_proposal(multiple, "trip", "cheap"), AmbiguousPolicyTarget))
    test("unseen_artifact_cannot_be_user_referent", lambda: expect_raises(lambda: request_availability({"artifact_id": "trip", "version": 5, "visible_to_user": False}), AmbiguousPolicyTarget))
    test("availability_is_research_only", lambda: assert_equal(request_availability({"artifact_id": "trip", "version": 4, "visible_to_user": True})["allowed_actions"], ["research_availability"]))
    report = {"kind": "synthetic_selfcheck", "tests_passed": len(results), "tests": results,
              "model_calls": 0, "semantic_labels_generated": False,
              "scientific_interpretation": "Only arithmetic, validation and response-adaptive policy contracts were exercised. No compiler superiority result.",
              "synthetic_score_summary": {"all_arm_constraint_survival": 0.5, "identical_arms_difference": 0,
                                          "note": "fabricated counters for calculation checks, not model performance"}}
    if args.write_fixtures:
        args.write_fixtures.mkdir(parents=True, exist_ok=True)
        with (args.write_fixtures / "manifest.synthetic.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
        with (args.write_fixtures / "observations.synthetic.jsonl").open("x", encoding="utf-8") as stream:
            stream.write("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


def assert_equal(actual, expected):
    if actual != expected:
        raise AssertionError(f"{actual!r} != {expected!r}")


if __name__ == "__main__":
    main()
