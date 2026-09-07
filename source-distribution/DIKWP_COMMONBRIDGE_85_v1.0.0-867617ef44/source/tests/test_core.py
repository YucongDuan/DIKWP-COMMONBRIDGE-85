from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from commonbridge85.core import (
    CAPABILITY_TIERS,
    TRUE_VALUE_DIMENSIONS,
    compile_capsule,
    normalize_environment_profile,
    route_capsule,
    record_contribution,
    issue_true_value_receipt,
    create_exchange_bundle,
    verify_exchange_bundle,
    generate_open_calls,
    portfolio_snapshot,
    summary,
)


PAYLOAD = {
    "title": "Local knowledge collaboration",
    "purpose": "Preserve and verify local knowledge across AI access levels.",
    "problem": "Local records are difficult to share.",
    "sources": ["source-a", "source-b"],
    "differences": ["terminology mismatch", "raw data local only"],
    "understanding": "Build the source map first.",
    "affected": ["community", "reviewers"],
    "constraints": ["offline", "low compute"],
    "true_values": ["truth_access", "autonomy", "recognition"],
}


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = compile_capsule(PAYLOAD)

    def test_summary(self):
        s = summary()
        self.assertEqual(s["status"], "ok")
        self.assertTrue(s["invariants"]["no_person_grading"])
        self.assertFalse(s["invariants"]["no_control_circumvention"] is False)

    def test_portfolio_snapshot_current_count(self):
        self.assertEqual(portfolio_snapshot()["public_repositories"], 363)

    def test_capability_tiers_are_environment_profiles(self):
        self.assertEqual(CAPABILITY_TIERS["H0_MANUAL"]["rank"], 0)
        self.assertEqual(CAPABILITY_TIERS["A5_INSTITUTIONAL_AGENT"]["rank"], 5)

    def test_capsule_schema(self):
        self.assertEqual(self.capsule["schema"], "dikwp-commonbridge.capsule/1.0")
        self.assertTrue(self.capsule["capsule_id"].startswith("bridge-"))
        self.assertEqual(len(self.capsule["sha256"]), 64)

    def test_capsule_has_all_dikwp(self):
        self.assertEqual(set(self.capsule["dikwp"]), {"D", "I", "K", "W", "P"})
        self.assertTrue(self.capsule["mesh85"]["semantic_11111"])

    def test_capsule_has_manual_tasks(self):
        self.assertTrue(any(t["min_tier"] == "H0_MANUAL" for t in self.capsule["tasks"]))
        self.assertTrue(all(t["result_required"] for t in self.capsule["tasks"]))

    def test_capsule_no_person_grade(self):
        self.assertTrue(self.capsule["identity_policy"]["person_grade_absent"])
        self.assertFalse(self.capsule["lawful_resilience"]["bypass_controls"])

    def test_explicit_tasks(self):
        c = compile_capsule({**PAYLOAD, "tasks": [{"title": "Manual review", "min_tier": "H0_MANUAL"}]})
        self.assertEqual(len(c["tasks"]), 1)
        self.assertEqual(c["tasks"][0]["title_zh"], "Manual review")

    def test_unknown_tier_normalizes_manual(self):
        p = normalize_environment_profile({"tier": "unknown"})
        self.assertEqual(p["tier"], "H0_MANUAL")
        self.assertFalse(p["tier_is_person_grade"])

    def test_manual_route(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        self.assertTrue(r["lawful_resilience"]["tasks_transformed_not_evaded"])
        self.assertFalse(r["lawful_resilience"]["controls_bypassed"])
        self.assertGreater(r["inclusion"]["manual_path_count"], 0)

    def test_small_local_route(self):
        r = route_capsule(self.capsule, {"tier": "A2_SMALL_LOCAL", "local_ai_allowed": True})
        self.assertGreaterEqual(r["inclusion"]["ready_count"], 4)

    def test_high_stakes_requires_reviewer(self):
        c = compile_capsule({**PAYLOAD, "domain": "medical"})
        r = route_capsule(c, {"tier": "A4_ADVANCED_HOSTED", "qualified_review_available": False})
        held = [x for x in r["tasks"] if x["status"] == "HOLD_POLICY_OR_REVIEW"]
        self.assertGreaterEqual(len(held), 1)

    def test_high_stakes_reviewer_unlocks(self):
        c = compile_capsule({**PAYLOAD, "domain": "medical"})
        r = route_capsule(c, {"tier": "A4_ADVANCED_HOSTED", "qualified_review_available": True})
        self.assertFalse(any("qualified_review_missing" in " ".join(x["policy_reasons"]) for x in r["tasks"]))

    def test_contribution(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        task_id = r["primary_action"]["task_id"]
        c = record_contribution(self.capsule, r, {"task_id": task_id, "summary": "Mapped sources."})
        self.assertTrue(c["contribution_id"].startswith("contrib-"))
        self.assertTrue(c["contributor"]["person_score_absent"])
        self.assertTrue(c["rights"]["attribution_required"])


    def test_placeholder_task_uses_primary_action(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": "REPLACE_WITH_TASK_ID", "summary": "Mapped."})
        self.assertEqual(c["task"]["task_id"], r["primary_action"]["task_id"])

    def test_invalid_task_rejected(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        with self.assertRaises(ValueError):
            record_contribution(self.capsule, r, {"task_id": "missing"})

    def test_true_value_dimensions(self):
        self.assertIn("time_return", TRUE_VALUE_DIMENSIONS)
        self.assertIn("ecological_continuity", TRUE_VALUE_DIMENSIONS)

    def test_provisional_receipt(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": r["primary_action"]["task_id"], "summary": "Mapped."})
        v = issue_true_value_receipt(c, {"observed": False, "categories": ["truth_access"]})
        self.assertEqual(v["status"], "PROVISIONAL_NOT_YET_OBSERVED")
        self.assertFalse(v["currency_boundary"]["financial_asset"])

    def test_observed_receipt(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": r["primary_action"]["task_id"], "summary": "Mapped."})
        v = issue_true_value_receipt(c, {"observed": True, "categories": ["truth_access"], "evidence": ["e1"]})
        self.assertEqual(v["status"], "OBSERVED_SCOPE_LIMITED")
        self.assertTrue(v["true_value_vector"]["truth_access"]["observed"])

    def test_burden_reopens_receipt(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": r["primary_action"]["task_id"], "summary": "Mapped."})
        v = issue_true_value_receipt(c, {"observed": True, "categories": ["care"], "evidence": ["e1"], "burdened": ["reviewer"]})
        self.assertEqual(v["status"], "REOPENED_FOR_CORRECTION")

    def test_invalid_value_category(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": r["primary_action"]["task_id"], "summary": "Mapped."})
        with self.assertRaises(ValueError):
            issue_true_value_receipt(c, {"categories": ["money_rank"]})

    def test_bundle_and_verify(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bundle.zip"
            meta = create_exchange_bundle(self.capsule, r, path)
            self.assertTrue(path.exists())
            self.assertEqual(meta["file_count"], 4)
            self.assertTrue(verify_exchange_bundle(path)["valid"])

    def test_bundle_contains_no_bypass_claim(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bundle.zip"
            meta = create_exchange_bundle(self.capsule, r, path)
            safety = meta["manifest"]["safety"]
            self.assertFalse(safety["contains_proxy_or_vpn"])
            self.assertFalse(safety["contains_credentials"])

    def test_open_calls_inclusion_first(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        calls = generate_open_calls([self.capsule], [r], [])
        self.assertGreater(calls["count"], 0)
        self.assertFalse(calls["calls"][0]["money_required"])
        self.assertFalse(calls["calls"][0]["person_rank_required"])
        self.assertEqual(calls["calls"][0]["min_tier"], "H0_MANUAL")

    def test_open_calls_remove_completed(self):
        r = route_capsule(self.capsule, {"tier": "H0_MANUAL"})
        c = record_contribution(self.capsule, r, {"task_id": r["primary_action"]["task_id"], "summary": "done"})
        calls = generate_open_calls([self.capsule], [r], [c])
        self.assertNotIn(c["task"]["task_id"], {x["task_id"] for x in calls["calls"]})


if __name__ == "__main__":
    unittest.main()
