"""test_i18n.py — тести системи перекладів."""
import pytest
from bot.i18n import t, get_translator, SUPPORTED_LANGS


class TestTranslations:
    def test_all_langs_supported(self):
        assert set(SUPPORTED_LANGS) == {"de", "ua", "ru", "en"}

    def test_basic_translation(self):
        assert t("cancel_text", "de") == "❌ Abbrechen"
        assert t("cancel_text", "ua") == "❌ Скасувати"
        assert t("cancel_text", "ru") == "❌ Отмена"
        assert t("cancel_text", "en") == "❌ Cancel"

    def test_format_kwargs(self):
        result = t("welcome_back", "ua", name="Іван")
        assert "Іван" in result

    def test_unknown_key_returns_placeholder(self):
        result = t("nonexistent_key_xyz", "de")
        assert "nonexistent_key_xyz" in result

    def test_unknown_lang_falls_back_to_de(self):
        result = t("cancel_text", "xx")
        assert result == t("cancel_text", "de")

    def test_get_translator(self):
        tr = get_translator("ru")
        assert "Отмена" in tr("cancel_text")
        assert "Max" in tr("welcome_back", name="Max")

    def test_all_keys_have_all_langs(self):
        from bot.i18n.translator import _TRANSLATIONS
        missing = []
        for key, translations in _TRANSLATIONS.items():
            for lang in SUPPORTED_LANGS:
                if lang not in translations:
                    missing.append(f"{key}:{lang}")
        assert not missing, f"Missing translations: {missing[:10]}"

    def test_trip_added_format(self):
        for lang in SUPPORTED_LANGS:
            result = t("trip_added", lang, date="01.01.2025", km=45.0, icon="💼", purpose="geschäftlich")
            assert "45" in result

    def test_track_stopped_format(self):
        for lang in SUPPORTED_LANGS:
            result = t("track_stopped", lang, h=2, m=15, trips=8, total=120.5, biz=80.0, priv=40.5)
            assert "120" in result or "120.5" in result

    def test_settings_title_format(self):
        for lang in SUPPORTED_LANGS:
            result = t("settings_title", lang,
                       name="Test", lang_label="🇩🇪 DE", radius=100, tg_id=123)
            assert "Test" in result
            assert "100" in result
