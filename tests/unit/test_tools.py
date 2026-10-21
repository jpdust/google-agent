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

from app import tools


def test_lookup_order_success() -> None:
    result = tools.lookup_order("ORD-1007")
    assert result["status"] == "success"
    assert result["order"]["status"] == "shipped"


def test_lookup_order_not_found_reports_error_not_fabrication() -> None:
    result = tools.lookup_order("ORD-9999")
    assert result["status"] == "error"
    assert "order" not in result


def test_lookup_subscription_success() -> None:
    result = tools.lookup_subscription("u_1002")
    assert result["status"] == "success"
    assert result["subscription"]["plan"] == "Basic"


def test_lookup_return_policy_success() -> None:
    result = tools.lookup_return_policy("apparel")
    assert result["status"] == "success"
    assert result["policy"]["window_days"] == 45


def test_search_faqs_returns_matches() -> None:
    result = tools.search_faqs("payment methods")
    assert result["status"] == "success"
    assert any(faq["faq_id"] == "FAQ-3" for faq in result["results"])
