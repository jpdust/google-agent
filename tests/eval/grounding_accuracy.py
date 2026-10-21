"""Deterministic grounding check for `grounding_accuracy` (see eval_config.yaml).

Checks that the agent's final response literally contains the facts the
datastore holds for the case (an order's status, a return window, an FAQ
answer, etc.) — not whether it merely *sounds* plausible. This catches
hallucinated IDs, dates, and amounts that an LLM judge might rubber-stamp
because the prose reads fine.

Each case must carry a custom `expected_facts: list[str]` field (eval
`reference`/`context` are reserved for other metrics, so this uses its own
field name), and may optionally carry `forbidden_facts: list[str]` — facts
that must NOT appear, for catching fabricated claims on records that don't
exist. Cases with neither field score 1 with a note, so mixed-dataset runs
don't fail on an unrelated case.
"""


def evaluate(instance):
    expected_facts = instance.get("expected_facts") or []
    forbidden_facts = instance.get("forbidden_facts") or []
    if not expected_facts and not forbidden_facts:
        return {"score": 1, "explanation": "No expected/forbidden facts; skipped."}

    response = instance.get("response") or {}
    text = " ".join(
        part.get("text", "") for part in response.get("parts", []) if part.get("text")
    )
    text_lower = text.lower()

    missing = [fact for fact in expected_facts if fact.lower() not in text_lower]
    fabricated = [fact for fact in forbidden_facts if fact.lower() in text_lower]

    total = len(expected_facts) + len(forbidden_facts)
    hits = (len(expected_facts) - len(missing)) + (len(forbidden_facts) - len(fabricated))
    score = hits / total if total else 1

    problems = []
    if missing:
        problems.append(f"missing expected facts: {missing}")
    if fabricated:
        problems.append(f"contains forbidden/fabricated facts: {fabricated}")
    explanation = (
        "; ".join(problems) if problems else "All checks passed."
    ) + f" Full response: {text!r}"
    return {"score": round(score, 2), "explanation": explanation}
