"""test_csv.py — тести CSV-імпорту адрес."""
import pytest
import asyncio
from bot.services.csv_import import parse_addresses_csv
from bot.models import AddressType


@pytest.mark.asyncio
async def test_valid_csv():
    csv = b"name,address,type\nKunde GmbH,Hauptstr 1 Munich,Kunde\nBuero,Leopoldstr 5 Munich,Buero\n"
    items, errors = await parse_addresses_csv(csv)
    assert len(items) == 2
    assert not errors
    assert items[0]["label"] == "Kunde GmbH"
    assert items[0]["type"] == AddressType.CLIENT
    assert items[1]["type"] == AddressType.OFFICE


@pytest.mark.asyncio
async def test_missing_name_column():
    csv = b"label,address\nTest,Hauptstr 1\n"
    items, errors = await parse_addresses_csv(csv)
    assert len(errors) > 0
    assert "name" in errors[0].lower()


@pytest.mark.asyncio
async def test_unknown_type_defaults_to_other():
    csv = b"name,address,type\nTest,Irgendwo 1,UnknownType\n"
    items, errors = await parse_addresses_csv(csv)
    assert len(items) == 1
    assert items[0]["type"] == AddressType.OTHER


@pytest.mark.asyncio
async def test_empty_rows_skipped():
    csv = b"name,address,type\n,Hauptstr 1,Kunde\nGood Name,Leopoldstr 5,Kunde\n"
    items, errors = await parse_addresses_csv(csv)
    assert len(items) == 1
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_bom_utf8():
    csv = "\ufeffname,address,type\nTest BOM,Hauptstr 1 Munich,Sonstiges\n".encode("utf-8-sig")
    items, errors = await parse_addresses_csv(csv)
    assert len(items) == 1
    assert items[0]["label"] == "Test BOM"


@pytest.mark.asyncio
async def test_all_types_mapping():
    csv = (
        b"name,address,type\n"
        b"Home,Heimstr 1,Heimatadresse\n"
        b"Client,Hauptstr 1,Kunde\n"
        b"Office,Buerostr 1,Buero\n"
        b"Other,Irgendwo 1,Sonstiges\n"
    )
    items, _ = await parse_addresses_csv(csv)
    types = [i["type"] for i in items]
    assert AddressType.HOME   in types
    assert AddressType.CLIENT in types
    assert AddressType.OFFICE in types
    assert AddressType.OTHER  in types
