"""Tests para Prompt Repetition (arxiv 2512.14982).

Verifica que la tecnica de repetir el prompt se aplique correctamente
a modelos sin reasoning y se omita en modelos con chain-of-thought.
"""

import unittest

from core.providers import (
    NON_REASONING_MODELS,
    apply_prompt_repetition,
    should_repeat_prompt,
)


class TestShouldRepeatPrompt(unittest.TestCase):
    """Tests para should_repeat_prompt()."""

    def test_non_reasoning_model_detected(self):
        """deepseek, minimax y groq deben detectarse como non-reasoning."""
        self.assertTrue(should_repeat_prompt("deepseek-chat"))
        self.assertTrue(should_repeat_prompt("minimax-m2.5"))
        self.assertTrue(should_repeat_prompt("groq/llama-3.3-70b"))

    def test_reasoning_model_not_repeated(self):
        """claude-opus y claude-sonnet NO deben repetirse."""
        self.assertFalse(should_repeat_prompt("claude-opus-4"))
        self.assertFalse(should_repeat_prompt("claude-sonnet-4"))

    def test_case_insensitive(self):
        """DeepSeek-V3 con mayusculas debe detectarse correctamente."""
        self.assertTrue(should_repeat_prompt("DeepSeek-V3"))
        self.assertTrue(should_repeat_prompt("GROQ/Llama-3"))
        self.assertTrue(should_repeat_prompt("MiniMax-M2.1"))

    def test_all_non_reasoning_models_detected(self):
        """Cada modelo en NON_REASONING_MODELS debe ser detectado."""
        for model in NON_REASONING_MODELS:
            with self.subTest(model=model):
                self.assertTrue(
                    should_repeat_prompt(model),
                    f"{model} deberia detectarse como non-reasoning",
                )

    def test_other_reasoning_models_excluded(self):
        """Modelos reasoning conocidos no deben repetirse."""
        reasoning_models = ["o1-preview", "o3-mini", "gpt-4o"]
        for model in reasoning_models:
            with self.subTest(model=model):
                self.assertFalse(should_repeat_prompt(model))


class TestApplyPromptRepetition(unittest.TestCase):
    """Tests para apply_prompt_repetition()."""

    PROMPT = "Explain quantum computing in simple terms."

    def test_double_repetition(self):
        """Prompt duplicado correctamente con separador."""
        result = apply_prompt_repetition(self.PROMPT, "deepseek-chat", times=2)
        expected = f"{self.PROMPT}\n\nLet me repeat that:\n\n{self.PROMPT}"
        self.assertEqual(result, expected)

    def test_triple_repetition(self):
        """Prompt triplicado con dos separadores."""
        result = apply_prompt_repetition(self.PROMPT, "deepseek-chat", times=3)
        expected = (
            f"{self.PROMPT}\n\nLet me repeat that:\n\n{self.PROMPT}"
            f"\n\nLet me repeat that one more time:\n\n{self.PROMPT}"
        )
        self.assertEqual(result, expected)

    def test_original_unchanged(self):
        """Modelo reasoning devuelve prompt sin cambio."""
        result = apply_prompt_repetition(self.PROMPT, "claude-sonnet-4", times=2)
        self.assertEqual(result, self.PROMPT)

    def test_empty_prompt(self):
        """Prompt vacio no rompe la funcion."""
        result = apply_prompt_repetition("", "deepseek-chat", times=2)
        self.assertEqual(result, "\n\nLet me repeat that:\n\n")
        # Para reasoning model, devuelve vacio sin cambio
        result_reasoning = apply_prompt_repetition("", "claude-opus-4", times=2)
        self.assertEqual(result_reasoning, "")

    def test_times_one_returns_original(self):
        """times=1 devuelve el prompt original sin repetir."""
        result = apply_prompt_repetition(self.PROMPT, "deepseek-chat", times=1)
        self.assertEqual(result, self.PROMPT)

    def test_times_four_uses_triple_format(self):
        """times>=3 usa el formato triple (maximo)."""
        result_3 = apply_prompt_repetition(self.PROMPT, "groq/llama", times=3)
        result_4 = apply_prompt_repetition(self.PROMPT, "groq/llama", times=4)
        self.assertEqual(result_3, result_4)

    def test_prompt_contains_original(self):
        """El resultado siempre contiene el prompt original."""
        result = apply_prompt_repetition(self.PROMPT, "minimax-m2.5", times=2)
        self.assertIn(self.PROMPT, result)
        count = result.count(self.PROMPT)
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
