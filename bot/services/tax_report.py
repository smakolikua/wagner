"""
tax_report.py — генерація EÜR (Einnahmenüberschussrechnung) PDF.

Взято від WISO Steuer:
- Belegübersicht по категоріях
- EÜR таблиця: доходи − витрати = прибуток
- ПДВ підсумок (Umsatzsteuer-Voranmeldung)
- Підпис і дата

Структура PDF:
  1. Заголовок + реквізити
  2. Fahrtkosten (з Fahrtenbuch)
  3. Betriebsausgaben по категоріях (з чеків)
  4. EÜR підсумок
  5. ПДВ підсумок
"""
import io
from datetime import date
from collections import defaultdict
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable,
)

from ..models import User, Receipt, Trip, TripPurpose, Category

C_DARK   = colors.HexColor("#1a1a2e")
C_HEAD   = colors.HexColor("#0f3460")
C_ALT    = colors.HexColor("#f0f4f8")
C_TOTAL  = colors.HexColor("#dbeafe")
C_PLUS   = colors.HexColor("#dcfce7")
C_MINUS  = colors.HexColor("#fef9c3")
C_GRID   = colors.HexColor("#cbd5e1")
C_WHITE  = colors.white
C_TEXT   = colors.HexColor("#1e293b")

_EURO = "\u20AC"


def _s(name, **kw):
    base = dict(fontName="Helvetica", textColor=C_TEXT, fontSize=9)
    base.update(kw)
    return ParagraphStyle(name, **base)


def generate_eur_pdf(
    user: User,
    receipts: List[Receipt],
    trips: List[Trip],
    date_from: date,
    date_to: date,
    period_label: str,
    total_income: float = 0.0,      # доходи (якщо користувач ввів вручну)
) -> bytes:
    """Генерує EÜR PDF і повертає байти."""
    buffer = io.BytesIO()
    st = {
        "title":    _s("t",   fontSize=15, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=2),
        "subtitle": _s("sub", fontSize=10, alignment=TA_CENTER, spaceAfter=2),
        "meta":     _s("m",   fontSize=8,  textColor=colors.HexColor("#475569"), alignment=TA_CENTER),
        "section":  _s("sec", fontSize=10, fontName="Helvetica-Bold", textColor=C_HEAD, spaceBefore=6, spaceAfter=3),
        "cell":     _s("c",   fontSize=8),
        "cellb":    _s("cb",  fontSize=8,  fontName="Helvetica-Bold"),
        "small":    _s("sm",  fontSize=7.5, textColor=colors.HexColor("#64748b")),
    }

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"EÜR {period_label}", author=user.name,
    )
    el = []

    # ── Заголовок ──
    el.append(Paragraph("Einnahmenüberschussrechnung (EÜR)", st["title"]))
    el.append(Paragraph(f"§ 4 Abs. 3 EStG  ·  {user.name}", st["subtitle"]))
    el.append(Paragraph(
        f"Zeitraum: {date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}  "
        f"|  Erstellt: {date.today().strftime('%d.%m.%Y')}",
        st["meta"],
    ))
    el.append(Spacer(1, 3*mm))
    el.append(HRFlowable(width="100%", thickness=1.5, color=C_HEAD))
    el.append(Spacer(1, 3*mm))

    # ── РОЗДІЛ 1: Einnahmen (доходи) ──
    el.append(Paragraph("A. Betriebseinnahmen", st["section"]))
    income_data = [
        [Paragraph("<b>Position</b>", st["cellb"]),
         Paragraph("<b>Betrag (netto)</b>", st["cellb"]),
         Paragraph("<b>USt</b>", st["cellb"]),
         Paragraph("<b>Brutto</b>", st["cellb"])],
        [Paragraph("Umsatzerlöse laut Buchhaltung", st["cell"]),
         Paragraph(f"{total_income:,.2f} {_EURO}", st["cell"]),
         Paragraph("—", st["cell"]),
         Paragraph(f"{total_income:,.2f} {_EURO}", st["cell"])],
        [Paragraph("<b>Summe Betriebseinnahmen</b>", st["cellb"]),
         Paragraph(f"<b>{total_income:,.2f} {_EURO}</b>", st["cellb"]),
         Paragraph("", st["cell"]),
         Paragraph(f"<b>{total_income:,.2f} {_EURO}</b>", st["cellb"])],
    ]
    _add_table(el, income_data, [8*cm, 3.5*cm, 2*cm, 3*cm], C_PLUS)

    # ── РОЗДІЛ 2: Fahrtkosten (поїздки) ──
    biz_trips = [t for t in trips if t.purpose == TripPurpose.BUSINESS]
    total_km   = sum(t.distance for t in biz_trips)
    fahrt_cost = round(total_km * 0.30, 2)  # 0,30 €/km pauschal (§ 9 EStG)

    el.append(Paragraph("B. Fahrtkosten (aus Fahrtenbuch)", st["section"]))
    fahrt_data = [
        [Paragraph("<b>Beschreibung</b>", st["cellb"]),
         Paragraph("<b>Km</b>", st["cellb"]),
         Paragraph("<b>Pauschale</b>", st["cellb"]),
         Paragraph("<b>Betrag</b>", st["cellb"])],
        [Paragraph(f"Geschäftliche Fahrten ({len(biz_trips)} Fahrten)", st["cell"]),
         Paragraph(f"{total_km:.1f} km", st["cell"]),
         Paragraph(f"0,30 {_EURO}/km", st["cell"]),
         Paragraph(f"{fahrt_cost:,.2f} {_EURO}", st["cell"])],
        [Paragraph("<b>Summe Fahrtkosten</b>", st["cellb"]),
         Paragraph("", st["cell"]),
         Paragraph("", st["cell"]),
         Paragraph(f"<b>{fahrt_cost:,.2f} {_EURO}</b>", st["cellb"])],
    ]
    _add_table(el, fahrt_data, [8*cm, 2.5*cm, 3*cm, 3*cm], C_MINUS)

    # ── РОЗДІЛ 3: Betriebsausgaben по категоріях ──
    biz_receipts = [r for r in receipts if r.is_business]
    by_cat: dict[str, list] = defaultdict(list)
    for r in biz_receipts:
        cat_name = r.category.name if r.category else "Sonstige BA"
        by_cat[cat_name].append(r)

    total_expenses_receipts = sum(r.net_amount for r in biz_receipts)
    total_vat_paid = sum((r.vat_amount or 0) for r in biz_receipts)

    el.append(Paragraph("C. Betriebsausgaben (Belege)", st["section"]))
    exp_rows = [
        [Paragraph("<b>Kategorie</b>", st["cellb"]),
         Paragraph("<b>Belege</b>", st["cellb"]),
         Paragraph("<b>Netto</b>", st["cellb"]),
         Paragraph("<b>VSt</b>", st["cellb"]),
         Paragraph("<b>Brutto</b>", st["cellb"])],
    ]
    for cat_name, cat_receipts in sorted(by_cat.items()):
        net    = sum(r.net_amount for r in cat_receipts)
        vat    = sum((r.vat_amount or 0) for r in cat_receipts)
        gross  = sum(r.amount_gross for r in cat_receipts)
        exp_rows.append([
            Paragraph(cat_name, st["cell"]),
            Paragraph(str(len(cat_receipts)), st["cell"]),
            Paragraph(f"{net:,.2f} {_EURO}", st["cell"]),
            Paragraph(f"{vat:,.2f} {_EURO}", st["cell"]),
            Paragraph(f"{gross:,.2f} {_EURO}", st["cell"]),
        ])
    exp_rows.append([
        Paragraph("<b>Summe Betriebsausgaben</b>", st["cellb"]),
        Paragraph(f"<b>{len(biz_receipts)}</b>", st["cellb"]),
        Paragraph(f"<b>{total_expenses_receipts:,.2f} {_EURO}</b>", st["cellb"]),
        Paragraph(f"<b>{total_vat_paid:,.2f} {_EURO}</b>", st["cellb"]),
        Paragraph("", st["cell"]),
    ])
    _add_table(el, exp_rows, [6*cm, 1.8*cm, 3*cm, 2.5*cm, 3*cm], C_MINUS)

    # ── РОЗДІЛ 4: EÜR Підсумок ──
    total_expenses = fahrt_cost + total_expenses_receipts
    profit = total_income - total_expenses

    el.append(Paragraph("D. Ergebnis (EÜR)", st["section"]))
    summary_data = [
        [Paragraph("<b>Position</b>", st["cellb"]), Paragraph("<b>Betrag</b>", st["cellb"])],
        [Paragraph("A. Betriebseinnahmen", st["cell"]),         Paragraph(f"{total_income:,.2f} {_EURO}", st["cell"])],
        [Paragraph("B. Fahrtkosten",       st["cell"]),         Paragraph(f"- {fahrt_cost:,.2f} {_EURO}", st["cell"])],
        [Paragraph("C. Betriebsausgaben (Belege)", st["cell"]), Paragraph(f"- {total_expenses_receipts:,.2f} {_EURO}", st["cell"])],
        [Paragraph("<b>Gewinn / Verlust</b>", st["cellb"]),
         Paragraph(f"<b>{'+ ' if profit >= 0 else ''}{profit:,.2f} {_EURO}</b>", st["cellb"])],
    ]
    profit_color = C_PLUS if profit >= 0 else colors.HexColor("#fecaca")
    summary_tbl = Table(summary_data, colWidths=[12*cm, 4.5*cm])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  C_HEAD),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, C_GRID),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [C_WHITE, C_ALT]),
        ("BACKGROUND",    (0, -1),(-1, -1), profit_color),
        ("LINEABOVE",     (0, -1),(-1, -1), 1.2, C_DARK),
        ("FONTNAME",      (0, -1),(-1, -1), "Helvetica-Bold"),
    ]))
    el.append(summary_tbl)
    el.append(Spacer(1, 5*mm))

    # ── РОЗДІЛ 5: Umsatzsteuer ──
    el.append(Paragraph("E. Umsatzsteuer-Zusammenfassung", st["section"]))
    vst_data = [
        [Paragraph("<b>Position</b>", st["cellb"]), Paragraph("<b>Betrag</b>", st["cellb"])],
        [Paragraph("Vorsteuer (bezahlt)", st["cell"]),     Paragraph(f"{total_vat_paid:,.2f} {_EURO}", st["cell"])],
        [Paragraph("Umsatzsteuer (eingenommen)", st["cell"]), Paragraph(f"0,00 {_EURO} *", st["cell"])],
        [Paragraph("Zahllast / Erstattung", st["cellb"]),  Paragraph(f"<b>{-total_vat_paid:,.2f} {_EURO}</b>", st["cellb"])],
    ]
    _add_table(el, vst_data, [12*cm, 4.5*cm], colors.HexColor("#f0fdf4"))
    el.append(Paragraph("* Umsatzsteuer aus Einnahmen bitte manuell ergänzen.", st["small"]))
    el.append(Spacer(1, 8*mm))

    # ── Підпис ──
    sig_data = [["Datum / Unterschrift", "", "Steuerberater / Stempel"]]
    sig_lines = [["_" * 30, "", "_" * 30]]
    sig_tbl = Table(sig_data + sig_lines, colWidths=[7*cm, 2.5*cm, 7*cm])
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.HexColor("#64748b")),
        ("TOPPADDING",    (0, 1), (-1, 1),  14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    el.append(sig_tbl)

    doc.build(el)
    return buffer.getvalue()


def _add_table(el, data, col_widths, row_color):
    tbl = Table(data, colWidths=col_widths)
    n = len(data)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),   C_HEAD),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),   C_WHITE),
        ("TOPPADDING",    (0, 0),  (-1, -1),  4),
        ("BOTTOMPADDING", (0, 0),  (-1, -1),  4),
        ("LEFTPADDING",   (0, 0),  (-1, -1),  5),
        ("GRID",          (0, 0),  (-1, -1),  0.3, C_GRID),
        ("ROWBACKGROUNDS",(0, 1),  (-1, n-2), [C_WHITE, C_ALT]),
        ("BACKGROUND",    (0, -1), (-1, -1),  row_color),
        ("LINEABOVE",     (0, -1), (-1, -1),  1.0, C_DARK),
    ]))
    el.append(tbl)
    el.append(Spacer(1, 3*mm))
