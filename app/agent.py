# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import AgentTool
from google.genai import types

from app import tools

MODEL = "gemini-3.8-flash"


kb_retriever_agent = Agent(
    name="kb_retriever_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "Retrieves factual customer support records — user accounts, orders, "
        "subscriptions, return policies, and FAQ answers — from the datastore. "
        "Call this for any question that needs a real record looked up; it "
        "never answers from general knowledge."
    ),
    instruction="""You are a retrieval specialist for a customer support system.

Use your tools to look up the exact record the caller asked about:
- lookup_user / lookup_orders_for_user / lookup_order for accounts and orders.
- lookup_subscription for billing/subscription status.
- lookup_return_policy for return windows and conditions by product category.
- search_faqs for general how-to questions.

Rules:
- Always call a tool before answering. Never invent IDs, dates, amounts, or
  policy terms.
- If a tool returns `status: error`, report plainly that no matching record
  was found — do not guess or fill in a plausible-looking value.
- Return the retrieved facts concisely and completely (IDs, statuses, dates,
  amounts) so the caller can relay them to the customer without re-asking.
""",
    tools=[
        tools.lookup_user,
        tools.lookup_order,
        tools.lookup_orders_for_user,
        tools.lookup_subscription,
        tools.lookup_return_policy,
        tools.search_faqs,
    ],
)

customer_support_orchestrator = Agent(
    # Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
    # from the project `name:` recorded there, and telemetry reports it as
    # gen_ai.agent.name. Renaming the agent only here makes the two disagree,
    # and anything selecting traces by name stops finding this agent's.
    name="customer_support_orchestrator",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a customer support agent: polite, empathetic, and direct.

Style:
- Acknowledge how the customer feels before diving into the fix, especially
  if they sound frustrated, confused, or upset.
- Be clear and concise — give the answer, not a run-around.
- Never be curt or dismissive, but don't pad responses with filler either.

Grounding — this is the most important rule:
- For ANY question about a specific user, order, subscription, return policy,
  or FAQ, you MUST call the kb_retriever_agent tool to retrieve the real
  record before answering. Never state an order status, date, amount, or
  policy term that didn't come from that tool.
- If kb_retriever_agent reports no matching record, tell the customer clearly
  that you couldn't find it and ask for the correct ID — never fabricate one.
- For greetings, thanks, or questions about what you can help with, answer
  directly yourself; there's no need to call the tool when there's no record
  to retrieve.

You can help with: order status and tracking, subscription and billing
questions, return policies, and general account FAQs.
""",
    tools=[AgentTool(kb_retriever_agent)],
)

# Kept as `root_agent` for ADK's convention (adk run / adk web / agents-cli
# playground all look for this name).
root_agent = customer_support_orchestrator

app = App(
    root_agent=root_agent,
    name="app",
)
