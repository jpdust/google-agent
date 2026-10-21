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

"""Decoupled data-access layer for the customer support agent.

`BaseDataStore` is the contract every tool in `tools.py` is written against.
`JSONDataStore` is the default, file-backed implementation. To move to a
SQL, vector, or NoSQL backend, implement `BaseDataStore` and call
`set_datastore()` with an instance before the agent runs — `tools.py` and
`agent.py` never need to change.
"""

from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

DEFAULT_ENTITIES_PATH = Path(__file__).parent / "data" / "entities.json"


class BaseDataStore(ABC):
    """Abstract read interface over customer support entities."""

    @abstractmethod
    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Returns the user record for `user_id`, or None if not found."""

    @abstractmethod
    def get_order(self, order_id: str) -> dict[str, Any] | None:
        """Returns the order record for `order_id`, or None if not found."""

    @abstractmethod
    def get_orders_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Returns every order placed by `user_id` (empty list if none)."""

    @abstractmethod
    def get_subscription_by_user(self, user_id: str) -> dict[str, Any] | None:
        """Returns `user_id`'s subscription record, or None if not found."""

    @abstractmethod
    def get_return_policy(self, category: str) -> dict[str, Any] | None:
        """Returns the return policy for `category`, or None if not found."""

    @abstractmethod
    def search_faqs(self, query: str) -> list[dict[str, Any]]:
        """Returns FAQ entries relevant to `query`, best match first."""


class JSONDataStore(BaseDataStore):
    """Default datastore: loads a static JSON file into memory."""

    def __init__(self, path: str | Path = DEFAULT_ENTITIES_PATH) -> None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._users: dict[str, dict[str, Any]] = {
            u["user_id"]: u for u in data.get("users", [])
        }
        self._orders: dict[str, dict[str, Any]] = {
            o["order_id"]: o for o in data.get("orders", [])
        }
        self._subscriptions: list[dict[str, Any]] = data.get("subscriptions", [])
        self._return_policies: list[dict[str, Any]] = data.get(
            "return_policies", []
        )
        self._faqs: list[dict[str, Any]] = data.get("faqs", [])

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._users.get(user_id)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self._orders.get(order_id)

    def get_orders_by_user(self, user_id: str) -> list[dict[str, Any]]:
        return [o for o in self._orders.values() if o["user_id"] == user_id]

    def get_subscription_by_user(self, user_id: str) -> dict[str, Any] | None:
        for sub in self._subscriptions:
            if sub["user_id"] == user_id:
                return sub
        return None

    def get_return_policy(self, category: str) -> dict[str, Any] | None:
        for policy in self._return_policies:
            if policy["category"].lower() == category.strip().lower():
                return policy
        return None

    def search_faqs(self, query: str) -> list[dict[str, Any]]:
        terms = [t for t in query.lower().split() if t]
        scored: list[tuple[int, dict[str, Any]]] = []
        for faq in self._faqs:
            haystack = (
                f"{faq['question']} {faq['answer']} {' '.join(faq.get('tags', []))}"
            ).lower()
            score = sum(1 for t in terms if t in haystack)
            if score:
                scored.append((score, faq))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [faq for _, faq in scored[:5]]


_lock = threading.Lock()
_datastore: BaseDataStore | None = None


def get_datastore() -> BaseDataStore:
    """Returns the active datastore, lazily creating the default JSON one."""
    global _datastore
    with _lock:
        if _datastore is None:
            _datastore = JSONDataStore(
                os.getenv("ENTITIES_PATH", DEFAULT_ENTITIES_PATH)
            )
        return _datastore


def set_datastore(store: BaseDataStore) -> None:
    """Swaps the active datastore (e.g. to a SQL/vector implementation).

    Call this once at startup, before the agent handles any request.
    """
    global _datastore
    with _lock:
        _datastore = store
