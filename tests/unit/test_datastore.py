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

from app.datastore import BaseDataStore, JSONDataStore, get_datastore, set_datastore


def test_json_datastore_loads_default_entities() -> None:
    store = JSONDataStore()
    assert store.get_user("u_1001")["name"] == "Maria Chen"
    assert store.get_order("ORD-1007")["status"] == "shipped"
    assert store.get_order("ORD-404") is None


def test_json_datastore_orders_by_user() -> None:
    store = JSONDataStore()
    orders = store.get_orders_by_user("u_1001")
    assert {o["order_id"] for o in orders} == {"ORD-1007", "ORD-1022"}


def test_json_datastore_return_policy_is_case_insensitive() -> None:
    store = JSONDataStore()
    assert store.get_return_policy("Electronics")["window_days"] == 30
    assert store.get_return_policy("nonexistent") is None


def test_json_datastore_search_faqs_ranks_by_term_overlap() -> None:
    store = JSONDataStore()
    results = store.search_faqs("cancel subscription")
    assert results
    assert results[0]["faq_id"] == "FAQ-2"


def test_set_datastore_swaps_implementation() -> None:
    class FakeDataStore(BaseDataStore):
        def get_user(self, user_id):
            return {"user_id": user_id, "name": "Fake"}

        def get_order(self, order_id):
            return None

        def get_orders_by_user(self, user_id):
            return []

        def get_subscription_by_user(self, user_id):
            return None

        def get_return_policy(self, category):
            return None

        def search_faqs(self, query):
            return []

    original = get_datastore()
    try:
        fake = FakeDataStore()
        set_datastore(fake)
        assert get_datastore() is fake
        assert get_datastore().get_user("anyone")["name"] == "Fake"
    finally:
        set_datastore(original)
