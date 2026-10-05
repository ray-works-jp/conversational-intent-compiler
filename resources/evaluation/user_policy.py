"""Closed-loop fixture policy: adapt choices to each actual candidate presentation."""


class AmbiguousPolicyTarget(ValueError):
    pass


def choose_actual_proposal(response, target_set_key, desired_option_key, *, hotel_change=True):
    """Stable scenario keys are assigned by a human/fixture adapter, not inferred here.

    response candidate_sets contain set_id, version, scenario_key and options with
    proposal_id, version, scenario_key and the displayed ordinal. This policy emits
    a response-specific ordinal and binds expected referent IDs for adjudication.
    It never copies an ordinal from a different arm's response.
    """
    if not isinstance(response.get("event_id"), str) or not response["event_id"]:
        raise ValueError("actual assistant response event ID required")
    candidate_sets = [s for s in response.get("candidate_sets", []) if s.get("scenario_key") == target_set_key]
    if len(candidate_sets) != 1:
        raise AmbiguousPolicyTarget("candidate set absent/ambiguous; obtain a targeted clarification")
    candidate_set = candidate_sets[0]
    if not all(candidate_set.get(k) is not None for k in ("set_id", "version")):
        raise ValueError("actual set ID and version required")
    options = candidate_set.get("options", [])
    ordinals = [o.get("display_ordinal") for o in options]
    if len(set(ordinals)) != len(ordinals):
        raise AmbiguousPolicyTarget("duplicate displayed ordinals within target set")
    selected = [o for o in options if o.get("scenario_key") == desired_option_key]
    if len(selected) != 1:
        raise AmbiguousPolicyTarget("desired option absent/ambiguous; do not reuse another arm's ordinal")
    proposal = selected[0]
    ordinal = proposal.get("display_ordinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("actual positive displayed ordinal required")
    if not all(proposal.get(k) is not None for k in ("proposal_id", "version")):
        raise ValueError("actual proposal ID and seen version required")
    current = f"{ordinal}番で。"
    if hotel_change:
        current += "ホテルだけもう少し安くして。"
    return {"human_raw": current, "response_event_id": response.get("event_id"),
            "expected_reference": {"candidate_set_id": candidate_set["set_id"], "candidate_set_version": candidate_set["version"],
                                   "proposal_id": proposal["proposal_id"], "proposal_version": proposal["version"]},
            "adoption_scope": {"selected_proposal": True, "hotel_change": hotel_change,
                               "ai_assumptions_confirmed": False},
            "authority_change": None,
            "policy_status": "fixture target binding; semantic keys require external adjudication"}


def request_availability(revised_artifact):
    if not all(revised_artifact.get(k) is not None for k in ("artifact_id", "version", "visible_to_user")):
        raise ValueError("artifact ID, seen version and visibility required")
    if revised_artifact["visible_to_user"] is not True:
        raise AmbiguousPolicyTarget("user has not seen revised version")
    return {"human_raw": "それで予約できるところ調べて。",
            "expected_reference": {"artifact_id": revised_artifact["artifact_id"], "version": revised_artifact["version"]},
            "allowed_actions": ["research_availability"], "forbidden_authority_inference": ["book", "pay"],
            "authority_change": None}
