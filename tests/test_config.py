import unittest

from src.config import PROVIDERS, detect_provider


class ProviderDetection(unittest.TestCase):
    def test_explicit_provider_wins(self):
        self.assertEqual(detect_provider({"LLM_PROVIDER": "Gemini", "ANTHROPIC_API_KEY": "x"}), "gemini")

    def test_single_key_is_enough(self):
        self.assertEqual(detect_provider({"OPENAI_API_KEY": "k"}), "openai")
        self.assertEqual(detect_provider({"GEMINI_API_KEY": "k"}), "gemini")
        self.assertEqual(detect_provider({"OPENROUTER_API_KEY": "k"}), "openrouter")

    def test_defaults_to_anthropic(self):
        self.assertEqual(detect_provider({}), "anthropic")

    def test_every_preset_names_an_sdk(self):
        for name, preset in PROVIDERS.items():
            self.assertIn(preset["sdk"], {"anthropic", "openai"}, name)
            self.assertTrue(preset["key_env"], name)


if __name__ == "__main__":
    unittest.main()
