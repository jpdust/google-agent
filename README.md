# google-agent — ADK Customer Support Multi-Agent

A multi-agent customer support assistant built on Google's [Agent Development
Kit (ADK)](https://adk.dev/). A conversational orchestrator handles the
customer; a dedicated retrieval sub-agent is the only thing allowed to touch
the datastore, so every factual claim in a reply is grounded in a real
record instead of the model's imagination.

Agent generated with `agents-cli` version `1.7.0`, then hand-built on top of
the scaffold.

## Architecture

```
                         ┌─────────────────────────────────┐
   user ───turn───────▶  │  customer_support_orchestrator   │
                         │  (root agent)                    │
                         │  - polite, empathetic, direct    │
                         │  - owns the conversation          │
                         └───────────────┬───────────────────┘
                                         │ AgentTool call
                                         │ "kb_retriever_agent"
                                         ▼
                         ┌───────────────────────────────────┐
                         │  kb_retriever_agent                │
                         │  (sub-agent, exposed as a tool)    │
                         │  - lookup_user / lookup_order / …  │
                         │  - never answers from "knowledge"  │
                         └───────────────┬─────────────────────┘
                                         │ calls get_datastore()
                                         ▼
                         ┌───────────────────────────────────┐
                         │  BaseDataStore  (datastore.py)     │
                         │  abstract interface                │
                         └───────────────┬─────────────────────┘
                                         │ default implementation
                                         ▼
                         ┌───────────────────────────────────┐
                         │  JSONDataStore                     │
                         │  reads app/data/entities.json      │
                         └─────────────────────────────────────┘
```

- **`customer_support_orchestrator`** (`app/agent.py`) is the root agent the
  user talks to. It never queries the datastore directly — it delegates any
  question that needs a real record to `kb_retriever_agent` via an
  [`AgentTool`](https://adk.dev), and otherwise handles tone, routing, and
  conversation flow itself.
- **`kb_retriever_agent`** (`app/agent.py`) is a second `LlmAgent` wrapped in
  `AgentTool`. The parent stays in control — this is "invoke another agent
  as a tool," not open-ended delegation — and its only job is calling the
  retrieval functions in `app/tools.py` and returning what they find.
- **`app/tools.py`** holds the plain `FunctionTool`s (`lookup_user`,
  `lookup_order`, `lookup_orders_for_user`, `lookup_subscription`,
  `lookup_return_policy`, `search_faqs`). Each is a thin wrapper around
  whatever datastore is currently active.
- **`app/datastore.py`** defines `BaseDataStore`, the abstract contract every
  tool is written against, and `JSONDataStore`, the default implementation
  backed by `app/data/entities.json`. See *Swapping the Datastore* below.

## Directory Layout

```
google-agent/
├── app/
│   ├── agent.py            # customer_support_orchestrator + kb_retriever_agent + App
│   ├── datastore.py         # BaseDataStore (abstract) + JSONDataStore (default)
│   ├── tools.py              # Retrieval FunctionTools used by kb_retriever_agent
│   ├── data/
│   │   └── entities.json     # Users, orders, subscriptions, return policies, FAQs
│   ├── fast_api_app.py        # FastAPI server (adk web / agents-cli playground / A2A)
│   └── app_utils/              # Session/artifact services, A2A wiring (scaffold-generated)
├── tests/
│   ├── unit/
│   │   ├── test_datastore.py   # BaseDataStore / JSONDataStore / set_datastore()
│   │   └── test_tools.py        # Retrieval tool behavior, incl. not-found handling
│   ├── integration/
│   │   ├── test_agent.py         # End-to-end streaming smoke test (needs model creds)
│   │   └── test_server_e2e.py
│   └── eval/
│       ├── eval_config.yaml        # Metric definitions + selection
│       ├── grounding_accuracy.py    # Rubric (a): datastore-grounded facts
│       ├── routing_accuracy.py       # Rubric (b): kb_retriever_agent delegation
│       ├── response_quality.py        # General LLM-judge quality (scaffold default)
│       └── datasets/
│           ├── basic-dataset.json      # Scaffold default smoke cases
│           ├── grounding-dataset.json   # Rubric (a) cases
│           ├── routing-dataset.json      # Rubric (b) cases
│           └── tone-dataset.json          # Rubric (c) cases (graded via tone_empathy in eval_config.yaml)
├── requirements.txt         # Pip-compatible dependency mirror (uv.lock is authoritative)
├── pyproject.toml
├── CLAUDE.md                 # AI coding agent guide (workflow, operational rules)
└── Dockerfile
```

## Build

Step-by-step from a fresh clone to a working local environment.

> **Copy-paste note:** every `bash` block below contains only commands meant
> to run as-is — no comments mixed in. (zsh, unlike bash, doesn't treat `#`
> as a comment in an interactive shell by default, so a pasted comment line
> fails with `command not found: #` — harmless, but noisy. If you see that,
> just ignore it or paste commands one at a time.) The commands assume your
> shell is already in the project root (the directory containing this
> README and `pyproject.toml`) — if you just cloned the repo, `cd` into it
> first: `cd google-agent`.

**1. Install prerequisites** — [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
(Python package manager) and `agents-cli` (wraps `adk` with install/eval/deploy
helpers):

```bash
uv tool install google-agents-cli
```

**2. Install project dependencies** — creates `.venv/` and installs everything
pinned in `uv.lock`:

```bash
agents-cli install
```

This is equivalent to running `uv sync` directly. If you don't use `uv` at
all, `pip install -r requirements.txt` works too, but won't get the exact
pinned/locked versions.

**3. Configure model credentials** — this is `.env` *file content* to edit,
not a shell command to run. Open `.env` in an editor and set exactly one
option:

```
# Option A: Vertex AI (default). Requires a GCP project and
# `gcloud auth application-default login` beforehand.
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global

# Option B: Google AI Studio -- comment out the three lines above, then:
GEMINI_API_KEY=your-api-key-here
```

**4. Verify the build** — confirms the code imports cleanly and the project
is recognized:

```bash
uv run python -c "from app.agent import root_agent; print(root_agent.name)"
```

Expect `customer_support_orchestrator` printed back.

```bash
agents-cli info
```

Expect `Root agent name: customer_support_orchestrator` and
`Agent directory: app` in the output.

## Run

### Option A — one-off prompt (CLI)

```bash
agents-cli run "What's the status of order ORD-1007?"
```

Native ADK CLI equivalent:

```bash
uv run adk run app
```

### Option B — interactive multi-turn web UI

```bash
agents-cli playground
```

Native ADK CLI equivalent:

```bash
uv run adk web
```

Opens a local web UI (default `http://localhost:8000`) for multi-turn
conversations with `customer_support_orchestrator`, with full visibility
into the `kb_retriever_agent` delegation and its tool calls — expand an
agent turn in the UI to see the `kb_retriever_agent` function call/response
pair.

### Option C — serve the FastAPI app directly

```bash
uv run python -m app.fast_api_app
```

Serves on `http://0.0.0.0:8000` (REST, ADK web routes, and the A2A endpoint).

## Swapping the Datastore

The agent and tools are written entirely against `BaseDataStore`
(`app/datastore.py`) — nothing in `app/tools.py` or `app/agent.py` knows
it's reading a JSON file. To move to SQL, a vector store, or any other
backend:

1. Implement `BaseDataStore` (six methods: `get_user`, `get_order`,
   `get_orders_by_user`, `get_subscription_by_user`, `get_return_policy`,
   `search_faqs`).
2. Call `set_datastore(YourImplementation(...))` once at startup, before the
   agent handles a request (e.g. in a module-level block in `app/agent.py`,
   or in `fast_api_app.py`'s `lifespan`).

```python
from app.datastore import BaseDataStore, set_datastore

class PostgresDataStore(BaseDataStore):
    def __init__(self, dsn: str) -> None:
        self._conn = connect(dsn)

    def get_user(self, user_id: str) -> dict | None:
        ...  # SELECT ... WHERE user_id = %s

    # ...implement the remaining five methods...

set_datastore(PostgresDataStore(dsn=os.environ["DATABASE_URL"]))
```

No changes to `tools.py`, `agent.py`, or the eval datasets are needed.

## Test

Testing happens in two layers: deterministic `pytest` for code correctness,
and `agents-cli eval` for agent *behavior* (response quality, grounding,
routing, tone). LLM output is non-deterministic, so behavioral checks live
only in eval, never in `pytest` assertions on response content.

### 1. Unit tests — deterministic, no credentials needed

```bash
uv run pytest tests/unit -v
```

Covers `app/datastore.py` and `app/tools.py`: `JSONDataStore` loading and
lookups, `set_datastore()` swapping, and tool not-found handling (11 tests).
No model calls, no credentials required — safe to run anywhere, including CI.

### 2. Integration test — needs model credentials

```bash
uv run pytest tests/integration -v
```

`test_agent.py` makes a real streaming call through `root_agent` and asserts
it returns text. Requires the credentials configured in **Build step 3**.

### 3. Agent behavior evaluation — the three rubrics

Three rubric-specific datasets and metrics live in `tests/eval/`, on top of
the scaffold's generic `basic-dataset.json`. See
`tests/eval/datasets/README.md` for the full dataset format reference.

| Rubric | Dataset | Metric | What it catches |
|---|---|---|---|
| (a) Grounding & Datastore Accuracy | `grounding-dataset.json` | `grounding_accuracy` (deterministic) | Missing facts, or fabricated facts on records that don't exist |
| (b) Multi-step Sub-agent Routing Accuracy | `routing-dataset.json` | `routing_accuracy` (deterministic) | Skipped lookups on factual questions, or unnecessary lookups on chit-chat |
| (c) Response Tone & Empathy | `tone-dataset.json` | `tone_empathy` (LLM-as-judge) | Curt, robotic, or unempathetic replies — persona only, independent of facts |

Run each rubric in isolation:

```bash
agents-cli eval run --dataset tests/eval/datasets/grounding-dataset.json --metrics grounding_accuracy
agents-cli eval run --dataset tests/eval/datasets/routing-dataset.json --metrics routing_accuracy
agents-cli eval run --dataset tests/eval/datasets/tone-dataset.json --metrics tone_empathy
```

Or run everything configured in `eval_config.yaml` (all four metrics) against
the default dataset:

```bash
agents-cli eval run
```

Results are written to `artifacts/grade_results/results_<timestamp>.{json,html}`
— open the `.html` file for per-case scores and judge rationale.

### 4. Everything at once

```bash
uv run pytest tests/unit tests/integration && agents-cli eval run
```

## Other Commands

| Command | Purpose |
|---|---|
| `agents-cli lint` | Run `ruff` + `ty` code quality checks |
| `agents-cli eval dataset synthesize` | Generate additional multi-turn eval scenarios |
| `agents-cli eval compare <base>.json <candidate>.json` | Regression-check two eval runs |
| `agents-cli scaffold enhance . --deployment-target <target>` | Add Cloud Run / GKE / Agent Runtime deployment later |

This project was scaffolded with `--deployment-target none --prototype`, so
there's no CI/CD or Terraform yet — it's local-first. See
`/google-agents-cli-deploy` when you're ready to add a deployment target.
