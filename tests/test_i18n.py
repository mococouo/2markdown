from __future__ import annotations

import unittest
from pathlib import Path

from two_markdown import i18n
from two_markdown.config import load_config, save_config


class I18nTests(unittest.TestCase):
    def setUp(self) -> None:
        i18n.set_language("en")

    def test_english_is_base(self) -> None:
        self.assertEqual(i18n.t("start"), "Convert")

    def test_chinese_translation(self) -> None:
        i18n.set_language("zh")
        self.assertEqual(i18n.t("start"), "开始转换")
        self.assertEqual(i18n.t("cancel"), "取消")

    def test_parameter_substitution(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.t("status_converting", index=3, total=10), "Converting 3 of 10…")
        i18n.set_language("zh")
        self.assertIn("3", i18n.t("status_converting", index=3, total=10))
        self.assertIn("10", i18n.t("status_converting", index=3, total=10))

    def test_fallback_to_english_for_missing_key(self) -> None:
        i18n.set_language("ko")
        self.assertEqual(i18n.t("app_title"), "2Markdown")

    def test_unknown_key_returns_key(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.t("does_not_exist_xyz"), "does_not_exist_xyz")

    def test_all_languages_have_display_names(self) -> None:
        codes = set(i18n.LANGUAGES)
        names = set(i18n.DISPLAY_NAMES)
        self.assertEqual(codes, names)

    def test_available_languages_includes_expected(self) -> None:
        codes = {code for code, _name in i18n.available_languages()}
        for expected in ("en", "zh", "zh-TW", "ja", "ko", "es", "fr", "de", "pt", "ru", "it", "ar"):
            self.assertIn(expected, codes)

    def test_set_language_falls_back_for_unknown(self) -> None:
        i18n.set_language("xx")
        self.assertEqual(i18n.current_language(), "en")

    def test_arabic_is_rtl(self) -> None:
        self.assertTrue(i18n.is_rtl("ar"))
        self.assertFalse(i18n.is_rtl("en"))

    def test_every_language_covers_core_keys(self) -> None:
        core = ("start", "cancel", "open_output", "install", "status_idle", "success", "failed", "skipped",
                "source_zone_title", "output_zone_title", "keep_tree", "attachments", "frontmatter",
                "dialog_install_title", "welcome_msg")
        for code, table in i18n.LANGUAGES.items():
            for key in core:
                self.assertIn(key, table, f"language {code} missing key {key}")


class ConfigTests(unittest.TestCase):
    def test_defaults_present(self) -> None:
        config = load_config()
        self.assertIn("language", config)
        self.assertIn("preserve_tree", config)
        self.assertTrue(config["preserve_tree"])

    def test_round_trip(self) -> None:
        save_config({"language": "ja", "last_source": "C:\\x", "ocr": True})
        config = load_config()
        self.assertEqual(config["language"], "ja")
        self.assertEqual(config["last_source"], "C:\\x")
        self.assertTrue(config["ocr"])

    def test_ignored_keys_dropped(self) -> None:
        save_config({"language": "de", "bogus_key": "junk"})
        config = load_config()
        self.assertNotIn("bogus_key", config)


if __name__ == "__main__":
    unittest.main()
