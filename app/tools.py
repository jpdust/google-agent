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

"""Retrieval tools for `kb_retriever_agent`.

Every function here is a thin wrapper around the active `BaseDataStore`
(see `datastore.py`). Swapping the datastore implementation never requires
touching this file.
"""

from __future__ import annotations

from app.datastore import get_datastore


def lookup_user(user_id: str) -> dict:
    """Looks up a customer's account details by user ID.

    Args:
        user_id: The customer's unique identifier, e.g. "u_1001".

    Returns:
        A dict with 'status' ('success' or 'error') and either 'user' or 'error'.
    """
    user = get_datastore().get_user(user_id)
    if user is None:
        return {"status": "error", "error": f"No user found with id '{user_id}'."}
    return {"status": "success", "user": user}


def lookup_order(order_id: str) -> dict:
    """Looks up a single order by order ID.

    Args:
        order_id: The order's unique identifier, e.g. "ORD-1007".

    Returns:
        A dict with 'status' ('success' or 'error') and either 'order' or 'error'.
    """
    order = get_datastore().get_order(order_id)
    if order is None:
        return {"status": "error", "error": f"No order found with id '{order_id}'."}
    return {"status": "success", "order": order}


def lookup_orders_for_user(user_id: str) -> dict:
    """Lists every order placed by a given user.

    Args:
        user_id: The customer's unique identifier, e.g. "u_1001".

    Returns:
        A dict with 'status' and 'orders' (a list, possibly empty).
    """
    orders = get_datastore().get_orders_by_user(user_id)
    return {"status": "success", "orders": orders}


def lookup_subscription(user_id: str) -> dict:
    """Looks up a user's subscription plan, status, and billing details.

    Args:
        user_id: The customer's unique identifier, e.g. "u_1001".

    Returns:
        A dict with 'status' ('success' or 'error') and either 'subscription' or 'error'.
    """
    subscription = get_datastore().get_subscription_by_user(user_id)
    if subscription is None:
        return {
            "status": "error",
            "error": f"No subscription found for user '{user_id}'.",
        }
    return {"status": "success", "subscription": subscription}


def lookup_return_policy(category: str) -> dict:
    """Looks up the return policy for a product category.

    Args:
        category: The product category, e.g. "electronics" or "apparel".

    Returns:
        A dict with 'status' ('success' or 'error') and either 'policy' or 'error'.
    """
    policy = get_datastore().get_return_policy(category)
    if policy is None:
        return {
            "status": "error",
            "error": f"No return policy found for category '{category}'.",
        }
    return {"status": "success", "policy": policy}


def search_faqs(query: str) -> dict:
    """Searches the knowledge base FAQs for entries relevant to a query.

    Args:
        query: A natural-language question or keywords to search for.

    Returns:
        A dict with 'status' and 'results' (a list of matching FAQ entries, possibly empty).
    """
    results = get_datastore().search_faqs(query)
    return {"status": "success", "results": results}
