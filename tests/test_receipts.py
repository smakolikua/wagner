"""test_receipts.py — тести модуля чеків і OCR."""
import json
import pytest
from datetime import date
from bot.services.ocr_service import _parse_claude_response, format_ocr_preview, OCRResult
from bot.models import Receipt, Category, TaxCode


class TestOCRParser:
    def _sample(self, **kw):
        base = {
            "amount_gross": 59.50, "vat_rate": 19,
            "date": "15.01.2025", "vendor": "REWE",
            "suggested_category": "Bürobedarf",
            "is_business": True, "confidence": 0.92,
        }
        base.update(kw)
        return json.dumps(base)

    def test_basic_parse(self):
        r = _parse_claude_response(self._sample())
        assert r.success
        assert r.amount_gross == 59.50
        assert r.vat_rate == 19
        assert r.vendor == "REWE"
        assert r.date == date(2025, 1, 15)
        assert r.confidence == 0.92
        assert r.is_business is True

    def test_net_amount_computed(self):
        r = _parse_claude_response(self._sample(amount_gross=119.0, vat_rate=19, amount_net=None))
        assert r.success
        assert abs(r.amount_net - 100.0) < 0.01
        assert abs(r.vat_amount - 19.0) < 0.01

    def test_zero_vat(self):
        r = _parse_claude_response(self._sample(vat_rate=0, amount_gross=50.0))
        assert r.success
        assert r.vat_rate == 0

    def test_german_decimal(self):
        """Германський формат суми 1.234,56 → 1234.56"""
        r = _parse_claude_response(self._sample(amount_gross="1.234,56"))
        assert r.success
        assert r.amount_gross == 1234.56

    def test_invalid_json(self):
        r = _parse_claude_response("not json at all")
        assert not r.success
        assert r.error is not None

    def test_empty_response(self):
        r = _parse_claude_response("{}")
        assert r.success
        assert r.amount_gross is None

    def test_date_formats(self):
        for date_str, expected in [
            ("15.01.2025", date(2025, 1, 15)),
            ("2025-01-15", date(2025, 1, 15)),
            ("15/01/2025", date(2025, 1, 15)),
        ]:
            r = _parse_claude_response(self._sample(date=date_str))
            assert r.date == expected, f"Failed for {date_str}"

    def test_confidence_levels(self):
        for conf in [0.3, 0.6, 0.9]:
            r = _parse_claude_response(self._sample(confidence=conf))
            assert r.confidence == conf

    def test_format_preview_all_langs(self):
        r = _parse_claude_response(self._sample())
        for lang in ["de", "ua", "ru", "en"]:
            preview = format_ocr_preview(r, lang)
            assert "59.50" in preview or "59,50" in preview or "59" in preview
            assert len(preview) > 50


class TestReceiptModel:
    def test_net_amount_with_vat(self):
        r = Receipt()
        r.amount_gross = 119.0
        r.amount_net = None
        r.vat_rate = 19
        r.vat_amount = None
        assert abs(r.net_amount - 100.0) < 0.01

    def test_net_amount_explicit(self):
        r = Receipt()
        r.amount_gross = 119.0
        r.amount_net = 100.0
        r.vat_rate = 19
        r.vat_amount = 19.0
        assert r.net_amount == 100.0

    def test_net_amount_no_vat(self):
        r = Receipt()
        r.amount_gross = 50.0
        r.amount_net = None
        r.vat_rate = 0
        r.vat_amount = None
        assert r.net_amount == 50.0

    def test_amount_display(self):
        r = Receipt()
        r.amount_gross = 12.5
        assert "12.50" in r.amount_display
        assert "€" in r.amount_display


class TestCategoryModel:
    def test_default_categories_count(self):
        from bot.models import DEFAULT_CATEGORIES
        assert len(DEFAULT_CATEGORIES) == 12

    def test_all_tax_codes_valid(self):
        from bot.models import DEFAULT_CATEGORIES
        valid_codes = {tc.value for tc in TaxCode}
        for cat in DEFAULT_CATEGORIES:
            assert cat["tax_code"].value in valid_codes

    def test_privat_category_exists(self):
        from bot.models import DEFAULT_CATEGORIES
        names = [c["name"] for c in DEFAULT_CATEGORIES]
        assert "Privat" in names

    def test_sort_order_unique(self):
        from bot.models import DEFAULT_CATEGORIES
        orders = [c["sort_order"] for c in DEFAULT_CATEGORIES]
        assert len(orders) == len(set(orders))
