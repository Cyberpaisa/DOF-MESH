"""Tests for core.cognitive_map — CognitiveMap model family profiles and routing.

30+ tests covering:
- Profile retrieval (7 tests)
- Task routing (9 tests)
- Synergy scoring (6 tests)
- Diversity score (4 tests)
- Recommendation (3 tests)
- Print map (2 tests)
- Unknown model handling (3 tests)

Run:
    python3 -m unittest tests.test_cognitive_map
"""

import unittest
from core.cognitive_map import (
    CognitiveMap,
    CognitiveProfile,
    SynergyScore,
    get_cognitive_map,
)


class TestProfileRetrieval(unittest.TestCase):
    """Tests for get_profile and get_all_profiles."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_get_all_profiles_returns_7_families(self):
        profiles = self.cmap.get_all_profiles()
        self.assertEqual(len(profiles), 7)
        expected = {"claude", "gemini", "gpt", "deepseek", "kimi", "nvidia", "glm"}
        self.assertEqual(set(profiles.keys()), expected)

    def test_get_claude_profile(self):
        p = self.cmap.get_profile("claude")
        self.assertIsNotNone(p)
        self.assertEqual(p.model_family, "claude")
        self.assertEqual(p.code_capability, "excellent")
        self.assertIn("Constitutional AI", p.architecture)

    def test_get_deepseek_profile(self):
        p = self.cmap.get_profile("deepseek")
        self.assertIsNotNone(p)
        self.assertEqual(p.model_family, "deepseek")
        self.assertEqual(p.math_capability, "excellent")
        self.assertIn("MoE", p.architecture)

    def test_get_gemini_profile(self):
        p = self.cmap.get_profile("gemini")
        self.assertIsNotNone(p)
        self.assertEqual(p.context_window, 1_000_000)
        self.assertEqual(p.speed, "fast")

    def test_get_gpt_profile(self):
        p = self.cmap.get_profile("gpt")
        self.assertIsNotNone(p)
        self.assertEqual(p.creativity, "excellent")
        self.assertIn("DALL-E", " ".join(p.special_abilities))

    def test_profile_alias_anthropic(self):
        p = self.cmap.get_profile("anthropic")
        self.assertIsNotNone(p)
        self.assertEqual(p.model_family, "claude")

    def test_profile_alias_openai(self):
        p = self.cmap.get_profile("openai")
        self.assertIsNotNone(p)
        self.assertEqual(p.model_family, "gpt")


class TestTaskRouting(unittest.TestCase):
    """Tests for get_optimal_model — each model family gets routed correctly."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_route_math_to_deepseek(self):
        p = self.cmap.get_optimal_model("optimize the routing algorithm complexity")
        self.assertEqual(p.model_family, "deepseek")

    def test_route_proof_to_deepseek(self):
        p = self.cmap.get_optimal_model("write a formal proof for the invariant")
        self.assertEqual(p.model_family, "deepseek")

    def test_route_code_to_claude(self):
        p = self.cmap.get_optimal_model("implement the new supervisor module")
        self.assertEqual(p.model_family, "claude")

    def test_route_security_to_claude(self):
        p = self.cmap.get_optimal_model("audit the governance rules for security")
        self.assertEqual(p.model_family, "claude")

    def test_route_creative_to_gpt(self):
        p = self.cmap.get_optimal_model("brainstorm creative marketing ideas")
        self.assertEqual(p.model_family, "gpt")

    def test_route_image_to_gpt(self):
        p = self.cmap.get_optimal_model("generate an image for the presentation design")
        self.assertEqual(p.model_family, "gpt")

    def test_route_large_doc_to_gemini(self):
        p = self.cmap.get_optimal_model("analyze this large document with 1M context")
        self.assertEqual(p.model_family, "gemini")

    def test_route_translate_to_kimi(self):
        p = self.cmap.get_optimal_model("translate this document to chinese")
        self.assertEqual(p.model_family, "kimi")

    def test_route_gpu_to_nvidia(self):
        p = self.cmap.get_optimal_model("optimize gpu inference throughput with tensorrt")
        self.assertEqual(p.model_family, "nvidia")

    def test_fallback_to_claude(self):
        """Unknown task should default to Claude as most versatile."""
        p = self.cmap.get_optimal_model("do something completely unrelated and vague")
        self.assertEqual(p.model_family, "claude")


class TestSynergyScoring(unittest.TestCase):
    """Tests for get_synergy."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_claude_deepseek_highest(self):
        syn = self.cmap.get_synergy("claude", "deepseek")
        self.assertIsNotNone(syn)
        self.assertEqual(syn.score, 0.95)
        self.assertEqual(syn.synergy_type, "complementary")

    def test_synergy_is_symmetric(self):
        syn_ab = self.cmap.get_synergy("claude", "deepseek")
        syn_ba = self.cmap.get_synergy("deepseek", "claude")
        self.assertIsNotNone(syn_ab)
        self.assertIsNotNone(syn_ba)
        self.assertEqual(syn_ab.score, syn_ba.score)

    def test_same_model_synergy(self):
        syn = self.cmap.get_synergy("claude", "claude")
        self.assertIsNotNone(syn)
        self.assertEqual(syn.score, 0.50)
        self.assertEqual(syn.synergy_type, "overlapping")

    def test_claude_gemini_synergy(self):
        syn = self.cmap.get_synergy("claude", "gemini")
        self.assertIsNotNone(syn)
        self.assertEqual(syn.score, 0.85)

    def test_gpt_glm_low_synergy(self):
        syn = self.cmap.get_synergy("gpt", "glm")
        self.assertIsNotNone(syn)
        self.assertLess(syn.score, 0.60)

    def test_synergy_has_description(self):
        syn = self.cmap.get_synergy("claude", "deepseek")
        self.assertIsNotNone(syn)
        self.assertGreater(len(syn.best_collaboration), 20)


class TestDiversityScore(unittest.TestCase):
    """Tests for get_mesh_diversity_score."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_all_families_is_1(self):
        all_fams = list(self.cmap.get_all_profiles().keys())
        score = self.cmap.get_mesh_diversity_score(active_families=all_fams)
        self.assertAlmostEqual(score, 1.0)

    def test_single_family(self):
        score = self.cmap.get_mesh_diversity_score(active_families=["claude"])
        expected = 1.0 / 7.0
        self.assertAlmostEqual(score, expected, places=4)

    def test_three_families(self):
        score = self.cmap.get_mesh_diversity_score(
            active_families=["claude", "deepseek", "gemini"]
        )
        expected = 3.0 / 7.0
        self.assertAlmostEqual(score, expected, places=4)

    def test_empty_mesh(self):
        score = self.cmap.get_mesh_diversity_score(active_families=[])
        self.assertAlmostEqual(score, 0.0)


class TestRecommendation(unittest.TestCase):
    """Tests for recommend_next_model."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_empty_mesh_recommends_claude(self):
        rec = self.cmap.recommend_next_model(active_families=[])
        self.assertEqual(rec, "claude")

    def test_all_families_returns_empty(self):
        all_fams = list(self.cmap.get_all_profiles().keys())
        rec = self.cmap.recommend_next_model(active_families=all_fams)
        self.assertEqual(rec, "")

    def test_claude_only_recommends_deepseek(self):
        """With only Claude, DeepSeek should be recommended (highest synergy at 0.95)."""
        rec = self.cmap.recommend_next_model(active_families=["claude"])
        self.assertEqual(rec, "deepseek")


class TestPrintMap(unittest.TestCase):
    """Tests for print_map ASCII visualization."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_print_map_returns_string(self):
        result = self.cmap.print_map()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 200)

    def test_print_map_contains_all_families(self):
        result = self.cmap.print_map()
        for family in self.cmap.get_all_profiles():
            self.assertIn(family.upper(), result)


class TestUnknownModelHandling(unittest.TestCase):
    """Tests for graceful handling of unknown models."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_unknown_profile_returns_none(self):
        p = self.cmap.get_profile("nonexistent_model")
        self.assertIsNone(p)

    def test_unknown_synergy_returns_none(self):
        syn = self.cmap.get_synergy("claude", "nonexistent")
        self.assertIsNone(syn)

    def test_unknown_both_synergy_returns_none(self):
        syn = self.cmap.get_synergy("foo", "bar")
        self.assertIsNone(syn)


class TestDataclassIntegrity(unittest.TestCase):
    """Tests for dataclass structure and content integrity."""

    def setUp(self):
        self.cmap = CognitiveMap()

    def test_all_profiles_have_strengths(self):
        for name, p in self.cmap.get_all_profiles().items():
            self.assertGreater(len(p.strengths), 0, f"{name} has no strengths")

    def test_all_profiles_have_optimal_tasks(self):
        for name, p in self.cmap.get_all_profiles().items():
            self.assertGreater(len(p.optimal_tasks), 0, f"{name} has no optimal_tasks")

    def test_all_profiles_have_avoid_tasks(self):
        for name, p in self.cmap.get_all_profiles().items():
            self.assertGreater(len(p.avoid_tasks), 0, f"{name} has no avoid_tasks")

    def test_context_windows_are_positive(self):
        for name, p in self.cmap.get_all_profiles().items():
            self.assertGreater(p.context_window, 0, f"{name} context_window <= 0")

    def test_convenience_function(self):
        cmap = get_cognitive_map()
        self.assertIsInstance(cmap, CognitiveMap)
        self.assertEqual(len(cmap.get_all_profiles()), 7)


if __name__ == "__main__":
    unittest.main()
