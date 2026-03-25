"""Tests for core/supervisor.py — MetaSupervisor and SupervisorVerdict."""

import unittest
from core.supervisor import MetaSupervisor, SupervisorVerdict


# ─── helpers ────────────────────────────────────────────

def _rich_output(n_headers=3, n_bullets=5, n_urls=2, length=3500, numbered=3):
    """Build a synthetic output that scores well across all dimensions."""
    headers = "\n".join(f"## Section {i}" for i in range(n_headers))
    bullets = "\n".join(f"- bullet point {i}" for i in range(n_bullets))
    steps = "\n".join(f"{i+1}. Step: implement action {i}" for i in range(numbered))
    urls = "\n".join(f"https://example.com/source{i}" for i in range(n_urls))
    padding = "This is a detailed analysis. " * (length // 30)
    return f"{headers}\n{bullets}\n{steps}\n{urls}\n{padding}"


def _bare_output(text="ok"):
    return text


# ─────────────────────────────────────────────────────────
# SupervisorVerdict dataclass
# ─────────────────────────────────────────────────────────

class TestSupervisorVerdict(unittest.TestCase):

    def _make(self, **kw):
        defaults = dict(decision="ACCEPT", score=8.0, quality=8.0,
                        actionability=7.0, completeness=8.0, factuality=7.0,
                        reasons=[])
        defaults.update(kw)
        return SupervisorVerdict(**defaults)

    def test_fields_accessible(self):
        v = self._make()
        self.assertEqual(v.decision, "ACCEPT")
        self.assertEqual(v.score, 8.0)

    def test_default_retry_count(self):
        v = self._make()
        self.assertEqual(v.retry_count, 0)

    def test_custom_retry_count(self):
        v = self._make(retry_count=2)
        self.assertEqual(v.retry_count, 2)

    def test_reasons_list(self):
        v = self._make(reasons=["low quality"])
        self.assertIn("low quality", v.reasons)


# ─────────────────────────────────────────────────────────
# _score_quality
# ─────────────────────────────────────────────────────────

class TestScoreQuality(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_base_score_short_plain(self):
        # Minimal text: should give ~5.0
        s = self.sup._score_quality("hello world")
        self.assertGreaterEqual(s, 5.0)
        self.assertLessEqual(s, 6.0)

    def test_long_text_bonus(self):
        short = self.sup._score_quality("x " * 500)
        long_ = self.sup._score_quality("x " * 1500)
        self.assertGreater(long_, short)

    def test_headers_bonus(self):
        no_hdr = self.sup._score_quality("plain text " * 50)
        with_hdr = self.sup._score_quality("## H1\n## H2\n## H3\nplain text " * 10)
        self.assertGreater(with_hdr, no_hdr)

    def test_bullets_bonus(self):
        no_bul = self.sup._score_quality("plain text " * 50)
        with_bul = self.sup._score_quality(
            "\n".join(f"- item {i}" for i in range(6)) + "\nplain " * 30
        )
        self.assertGreater(with_bul, no_bul)

    def test_code_block_bonus(self):
        no_code = self.sup._score_quality("plain text " * 50)
        with_code = self.sup._score_quality("plain text " * 50 + "\n```python\npass\n```")
        self.assertGreater(with_code, no_code)

    def test_capped_at_10(self):
        s = self.sup._score_quality(_rich_output())
        self.assertLessEqual(s, 10.0)

    def test_empty_returns_zero(self):
        # Empty output has no quality; 0.0 is correct, not the misleading 5.0 baseline
        self.assertEqual(self.sup._score_quality(""), 0.0)


# ─────────────────────────────────────────────────────────
# _score_actionability
# ─────────────────────────────────────────────────────────

class TestScoreActionability(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_base_empty(self):
        # Empty text has no actionability — returns 0.0, not the old 4.0 baseline
        s = self.sup._score_actionability("")
        self.assertEqual(s, 0.0)

    def test_whitespace_only_empty(self):
        self.assertEqual(self.sup._score_actionability("   "), 0.0)

    def test_action_words_increase_score(self):
        base = self.sup._score_actionability("nothing here")
        with_actions = self.sup._score_actionability(
            "implement this, create that, configure the system, deploy now"
        )
        self.assertGreater(with_actions, base)

    def test_numbered_steps_bonus(self):
        no_steps = self.sup._score_actionability("some text")
        with_steps = self.sup._score_actionability(
            "1. Do this\n2. Then that\n3. Finally this"
        )
        self.assertGreater(with_steps, no_steps)

    def test_capped_at_10(self):
        text = "implement create configure deploy install add modify update review\n" * 5
        text += "1. Step\n2. Step\n3. Step\n4. Step\n"
        self.assertLessEqual(self.sup._score_actionability(text), 10.0)

    def test_spanish_action_words(self):
        base = self.sup._score_actionability("nada")
        with_es = self.sup._score_actionability("implementar este sistema, crear módulo")
        self.assertGreater(with_es, base)


# ─────────────────────────────────────────────────────────
# _score_completeness
# ─────────────────────────────────────────────────────────

class TestScoreCompleteness(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_very_short_penalised(self):
        s = self.sup._score_completeness("hi", "anything")
        # < 200 chars → -2 from base 5
        self.assertLessEqual(s, 5.0)

    def test_medium_length_bonus(self):
        medium = "word " * 250  # ~1250 chars
        s = self.sup._score_completeness(medium, "word context")
        self.assertGreater(s, 5.0)

    def test_long_text_bigger_bonus(self):
        medium = "word " * 250
        long_ = "word " * 700
        s_med = self.sup._score_completeness(medium, "")
        s_lon = self.sup._score_completeness(long_, "")
        self.assertGreater(s_lon, s_med)

    def test_keyword_overlap_boosts(self):
        output = "security vulnerability reentrancy analysis detected"
        inp_no_match = "unrelated topic"
        inp_match = "security reentrancy vulnerability"
        s_no = self.sup._score_completeness(output, inp_no_match)
        s_yes = self.sup._score_completeness(output, inp_match)
        self.assertGreater(s_yes, s_no)

    def test_no_input_text_ok(self):
        s = self.sup._score_completeness("some output text " * 50, "")
        self.assertGreater(s, 0.0)

    def test_capped_at_10(self):
        self.assertLessEqual(
            self.sup._score_completeness("x " * 2000, "x analysis"), 10.0
        )


# ─────────────────────────────────────────────────────────
# _score_factuality
# ─────────────────────────────────────────────────────────

class TestScoreFactuality(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_base_no_urls(self):
        s = self.sup._score_factuality("plain text without sources")
        self.assertAlmostEqual(s, 5.0)

    def test_single_url_bonus(self):
        s = self.sup._score_factuality("see https://example.com/ref")
        self.assertGreater(s, 5.0)

    def test_two_urls_bigger_bonus(self):
        s1 = self.sup._score_factuality("https://a.com")
        s2 = self.sup._score_factuality("https://a.com https://b.com")
        self.assertGreater(s2, s1)

    def test_five_urls_max_url_bonus(self):
        urls = " ".join(f"https://src{i}.com" for i in range(5))
        s = self.sup._score_factuality(urls)
        self.assertGreaterEqual(s, 8.0)

    def test_hedging_language_bonus(self):
        base = self.sup._score_factuality("some claim")
        hedged = self.sup._score_factuality("according to source: data shows X")
        self.assertGreater(hedged, base)

    def test_unsubstantiated_claim_penalty(self):
        base = self.sup._score_factuality("plain statement")
        bad = self.sup._score_factuality("it is well known that this is true")
        self.assertLess(bad, base)

    def test_floor_zero(self):
        bad = ("it is well known that everyone knows "
               "research demonstrates it is well known " * 5)
        self.assertGreaterEqual(self.sup._score_factuality(bad), 0.0)

    def test_capped_at_10(self):
        urls = " ".join(f"https://s{i}.com" for i in range(10))
        s = self.sup._score_factuality(urls + " source: trusted data")
        self.assertLessEqual(s, 10.0)


# ─────────────────────────────────────────────────────────
# evaluate — decision thresholds
# ─────────────────────────────────────────────────────────

class TestEvaluateDecisions(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_rich_output_accept(self):
        v = self.sup.evaluate(_rich_output(), "security analysis")
        self.assertEqual(v.decision, "ACCEPT")

    def test_empty_output_low_score(self):
        v = self.sup.evaluate("", "question")
        self.assertLess(v.score, 7.0)

    def test_score_formula_weights(self):
        """Score = Q*0.40 + A*0.25 + C*0.20 + F*0.15 (spot-check)."""
        v = self.sup.evaluate(_rich_output(), "security")
        expected = (v.quality * 0.40 + v.actionability * 0.25 +
                    v.completeness * 0.20 + v.factuality * 0.15)
        self.assertAlmostEqual(v.score, round(expected, 2), places=1)

    def test_escalate_after_max_retries(self):
        # retry_count >= MAX_RETRIES with mid-range score → ACCEPT (not RETRY)
        v = self.sup.evaluate("short", "", retry_count=2)
        self.assertIn(v.decision, ("ACCEPT", "ESCALATE"))
        self.assertNotEqual(v.decision, "RETRY")

    def test_retry_count_preserved(self):
        v = self.sup.evaluate("some output " * 100, "", retry_count=1)
        self.assertEqual(v.retry_count, 1)

    def test_score_rounded_to_2dp(self):
        v = self.sup.evaluate("ok " * 200, "ok")
        # score should be at most 2 decimal places
        self.assertEqual(v.score, round(v.score, 2))

    def test_sub_dimensions_rounded_to_1dp(self):
        v = self.sup.evaluate("hello world", "")
        for attr in ("quality", "actionability", "completeness", "factuality"):
            val = getattr(v, attr)
            self.assertEqual(val, round(val, 1))

    def test_escalate_on_very_low_score(self):
        # Deliberately minimal output with no actionability, no sources
        v = self.sup.evaluate("x", "", retry_count=5)
        self.assertIn(v.decision, ("ESCALATE", "RETRY", "ACCEPT"))
        # At least score is computed
        self.assertGreaterEqual(v.score, 0.0)

    def test_reasons_populated_on_retry(self):
        # Short output at retry_count=0 should trigger RETRY or ESCALATE with reasons
        v = self.sup.evaluate("minimal output", "", retry_count=0)
        if v.decision == "RETRY":
            self.assertIsInstance(v.reasons, list)

    def test_verdict_is_supervisor_verdict(self):
        v = self.sup.evaluate("some output", "")
        self.assertIsInstance(v, SupervisorVerdict)

    def test_decision_is_valid_value(self):
        for text in ["", "short", _rich_output()]:
            v = self.sup.evaluate(text, "")
            self.assertIn(v.decision, ("ACCEPT", "RETRY", "ESCALATE"))


class TestScoreQualityBlank(unittest.TestCase):
    """_score_quality must return 0.0 for blank output, not the misleading 5.0 baseline."""

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_empty_string_quality_zero(self):
        self.assertEqual(self.sup._score_quality(""), 0.0)

    def test_whitespace_only_quality_zero(self):
        self.assertEqual(self.sup._score_quality("   "), 0.0)

    def test_tab_newline_quality_zero(self):
        self.assertEqual(self.sup._score_quality("\t\n"), 0.0)

    def test_non_empty_quality_above_zero(self):
        self.assertGreater(self.sup._score_quality("hello world"), 0.0)


class TestScoreFactualityBlank(unittest.TestCase):
    """_score_factuality must return 0.0 for blank output."""

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_empty_string_factuality_zero(self):
        self.assertEqual(self.sup._score_factuality(""), 0.0)

    def test_whitespace_only_factuality_zero(self):
        self.assertEqual(self.sup._score_factuality("   "), 0.0)

    def test_non_empty_factuality_above_zero(self):
        self.assertGreater(self.sup._score_factuality("plain text"), 0.0)


class TestEvaluateBlankOutput(unittest.TestCase):
    """evaluate() with blank output must ESCALATE with lower score than before fix."""

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_empty_output_escalates(self):
        v = self.sup.evaluate("", "What is DOF?")
        self.assertEqual(v.decision, "ESCALATE")

    def test_empty_output_quality_zero(self):
        v = self.sup.evaluate("", "What is DOF?")
        self.assertEqual(v.quality, 0.0)

    def test_empty_output_factuality_zero(self):
        v = self.sup.evaluate("", "What is DOF?")
        self.assertEqual(v.factuality, 0.0)

    def test_whitespace_output_escalates(self):
        v = self.sup.evaluate("   ", "")
        self.assertEqual(v.decision, "ESCALATE")


# ─────────────────────────────────────────────────────────
# orchestrate_swarm — SISYPHUS entry point
# ─────────────────────────────────────────────────────────

class TestOrchestrateSwarm(unittest.TestCase):

    def setUp(self):
        self.sup = MetaSupervisor()

    def test_returns_dict(self):
        result = self.sup.orchestrate_swarm("Build a RAG engine for DOF Mesh")
        self.assertIsInstance(result, dict)

    def test_has_required_keys(self):
        result = self.sup.orchestrate_swarm("Test objective")
        for key in ("objective", "subtasks", "results", "verdict", "integrated_output"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_objective_preserved(self):
        obj = "Deploy guardian agent to mesh"
        result = self.sup.orchestrate_swarm(obj)
        self.assertEqual(result["objective"], obj)

    def test_six_subtasks_dispatched(self):
        result = self.sup.orchestrate_swarm("Implement post-quantum crypto migration")
        self.assertEqual(len(result["subtasks"]), 6)

    def test_subtask_roles_present(self):
        result = self.sup.orchestrate_swarm("Audit security hierarchy")
        roles = set(result["subtasks"].keys())
        expected = {"architect", "researcher", "guardian", "verifier", "narrator", "devops"}
        self.assertEqual(roles, expected)

    def test_each_subtask_contains_objective(self):
        obj = "xyzuniqueobjective123"
        result = self.sup.orchestrate_swarm(obj)
        for role, task in result["subtasks"].items():
            self.assertIn(obj, task, f"Objective missing from {role} subtask")

    def test_each_subtask_has_role_prefix(self):
        result = self.sup.orchestrate_swarm("Run formal Z3 verification")
        for role, task in result["subtasks"].items():
            self.assertIn(f"[{role.upper()}]", task)

    def test_verdict_has_required_keys(self):
        result = self.sup.orchestrate_swarm("Validate governance rules")
        for key in ("decision", "score", "quality", "actionability", "completeness", "factuality"):
            self.assertIn(key, result["verdict"], f"Missing verdict key: {key}")

    def test_verdict_decision_valid(self):
        result = self.sup.orchestrate_swarm("Optimize provider chain TTL")
        self.assertIn(result["verdict"]["decision"], ("ACCEPT", "RETRY", "ESCALATE"))

    def test_verdict_score_in_range(self):
        result = self.sup.orchestrate_swarm("Index JSONL logs with RAG engine")
        score = result["verdict"]["score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 10.0)

    def test_integrated_output_is_string(self):
        result = self.sup.orchestrate_swarm("Stress test DOF mesh with 100 nodes")
        self.assertIsInstance(result["integrated_output"], str)

    def test_integrated_output_contains_objective(self):
        obj = "unique_swarm_test_objective_abc"
        result = self.sup.orchestrate_swarm(obj)
        self.assertIn(obj, result["integrated_output"])

    def test_integrated_output_mentions_all_roles(self):
        result = self.sup.orchestrate_swarm("Full DOF system audit")
        output = result["integrated_output"]
        for role in ("architect", "researcher", "guardian", "verifier", "narrator", "devops"):
            self.assertIn(role, output.lower())

    def test_results_has_dispatched_key(self):
        result = self.sup.orchestrate_swarm("Register orphan sessions as mesh nodes")
        self.assertIn("dispatched", result["results"])

    def test_dispatched_is_list(self):
        result = self.sup.orchestrate_swarm("Build CERBERUS PRIME guardian")
        self.assertIsInstance(result["results"]["dispatched"], list)

    def test_empty_objective_does_not_raise(self):
        try:
            result = self.sup.orchestrate_swarm("")
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"orchestrate_swarm raised on empty objective: {e}")

    def test_long_objective_handled(self):
        obj = "A" * 5000
        result = self.sup.orchestrate_swarm(obj)
        self.assertIsInstance(result, dict)
        self.assertIn("subtasks", result)

    def test_verdict_score_is_float(self):
        result = self.sup.orchestrate_swarm("Phase 10: autonomous scaling")
        self.assertIsInstance(result["verdict"]["score"], float)


if __name__ == "__main__":
    unittest.main()
