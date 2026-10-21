"""Delegation check for `routing_accuracy` (see eval_config.yaml).

Checks whether the orchestrator called the `kb_retriever_agent` tool (an
`AgentTool`, so it shows up in the trace as a `function_call`/
`function_response` named after the sub-agent — see
`google.adk.tools.agent_tool.AgentTool.__init__`, which sets
`name=agent.name`). This is a trajectory check, not a response-quality
check: a factually perfect answer that skipped the retrieval step is still
a routing failure (and vice versa for an unnecessary lookup on a case that
shouldn't need one).

Each case must carry a custom `expects_delegation: bool` field. Cases
without it score 1 with a note, so mixed-dataset runs don't fail on an
unrelated case.
"""

_SUB_AGENT_TOOL_NAME = "kb_retriever_agent"


def _called_sub_agent(agent_data) -> bool:
    for turn in (agent_data or {}).get("turns", []):
        for event in turn.get("events", []):
            for part in (event.get("content") or {}).get("parts", []):
                call = part.get("function_call")
                if call and call.get("name") == _SUB_AGENT_TOOL_NAME:
                    return True
    return False


def evaluate(instance):
    if "expects_delegation" not in instance:
        return {
            "score": 1,
            "explanation": "No expects_delegation on this case; skipped.",
        }

    expected = bool(instance["expects_delegation"])
    called = _called_sub_agent(instance.get("agent_data"))

    if expected == called:
        verb = "called" if called else "correctly skipped"
        return {"score": 1, "explanation": f"kb_retriever_agent was {verb}."}

    if expected and not called:
        explanation = (
            "Expected a kb_retriever_agent lookup before answering, but the "
            "orchestrator answered without one."
        )
    else:
        explanation = (
            "Expected the orchestrator to answer directly, but it called "
            "kb_retriever_agent unnecessarily."
        )
    return {"score": 0, "explanation": explanation}
