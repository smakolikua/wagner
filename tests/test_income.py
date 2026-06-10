"""test_income.py — тести моделі Income."""
import pytest
from unittest.mock import MagicMock
from datetime import date
from bot.models import Income


class TestIncomeModel:
    def test_gross_amount_with_vat(self):
        inc = Income()
        inc.amount = 1000.0
        inc.vat_amount = 190.0
        inc.vat_rate = 19
        assert abs(inc.gross_amount - 1190.0) < 0.01

    def test_gross_amount_no_vat(self):
        inc = Income()
        inc.amount = 500.0
        inc.vat_amount = 0.0
        inc.vat_rate = 0
        assert inc.gross_amount == 500.0

    def test_display_net(self):
        inc = Income()
        inc.amount = 1500.0
        assert "1500" in inc.display
        assert "€" in inc.display

    def test_display_with_vat(self):
        inc = Income()
        inc.amount = 1000.0
        inc.vat_amount = 190.0
        inc.vat_rate = 19
        display = inc.display
        assert "1000" in display
        assert "190" in display

    def test_repr(self):
        inc = Income()
        inc.id = 1
        inc.date = date(2025, 1, 15)
        inc.amount = 1500.0
        r = repr(inc)
        assert "1" in r
        assert "1500" in r


class TestIncomeCalculations:
    def test_vat_7_percent(self):
        inc = Income()
        inc.amount = 100.0
        inc.vat_amount = 7.0
        inc.vat_rate = 7
        assert abs(inc.gross_amount - 107.0) < 0.01

    def test_kleinunternehmer_zero_vat(self):
        """Kleinunternehmer не нараховує ПДВ."""
        inc = Income()
        inc.amount = 1000.0
        inc.vat_amount = 0.0
        inc.vat_rate = 0
        inc.is_kleinunternehmer = True
        assert inc.gross_amount == 1000.0

    def test_multiple_incomes_sum(self):
        incomes = []
        for amt in [1000.0, 2000.0, 1500.0]:
            inc = Income()
            inc.amount = amt
            inc.vat_amount = round(amt * 0.19, 2)
            inc.vat_rate = 19
            incomes.append(inc)
        total_net = sum(i.amount for i in incomes)
        total_vat = sum(i.vat_amount for i in incomes)
        assert abs(total_net - 4500.0) < 0.01
        assert abs(total_vat - 855.0) < 0.01
