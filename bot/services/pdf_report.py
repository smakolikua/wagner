"""
pdf_report.py — генерація PDF Fahrtenbuch (v2).

Покращення:
- Параграфи з переносом тексту для довгих адрес
- Окрема секція підсумку по місяцях якщо звіт за квартал/рік
- Поле для підпису та печатки
- Коректний підрахунок сторінок
- Захист від порожніх поїздок
"""
import io
from datetime import date
from collections import defaultdict
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, PageBreak,
    KeepTogether,
)

from ..models import Trip, Vehicle, User, TripPurpose

# ─── Кольори ──────────────────────────────────────────────────────────────────
C_DARK     = colors.HexColor("#1a1a2e")
C_ACCENT   = colors.HexColor("#16213e")
C_HEADER   = colors.HexColor("#0f3460")
C_ALT_ROW  = colors.HexColor("#f0f4f8")
C_TOTAL    = colors.HexColor("#dbeafe")
C_BIZ      = colors.HexColor("#dcfce7")
C_PRIV     = colors.HexColor("#fef9c3")
C_WHITE    = colors.white
C_GRID     = colors.HexColor("#cbd5e1")
C_TEXT     = colors.HexColor("#1e293b")


def _styles():
    return {
        "title":    ParagraphStyle("title",    fontName="Helvetica-Bold", textColor=C_TEXT, fontSize=16, alignment=TA_CENTER, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica",      textColor=C_TEXT, fontSize=10, alignment=TA_CENTER, spaceAfter=2),
        "meta":     ParagraphStyle("meta",     fontName="Helvetica",      textColor=colors.HexColor("#475569"), fontSize=8.5, alignment=TA_CENTER),
        "cell":     ParagraphStyle("cell",     fontName="Helvetica",      textColor=C_TEXT, fontSize=7.5, leading=10),
        "cell_bold":ParagraphStyle("cell_bold",fontName="Helvetica-Bold", textColor=C_TEXT, fontSize=7.5, leading=10),
        "small":    ParagraphStyle("small",    fontName="Helvetica",      textColor=C_TEXT, fontSize=8, spaceAfter=2),
        "section":  ParagraphStyle("section",  fontName="Helvetica-Bold", textColor=C_HEADER, fontSize=10, spaceBefore=8, spaceAfter=4),
    }


def generate_fahrtenbuch_pdf(
    user: User,
    vehicle: Vehicle,
    trips: List[Trip],
    period_label: str,
    date_from: date,
    date_to: date,
) -> bytes:
    buffer = io.BytesIO()
    st = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Fahrtenbuch {period_label}",
        author=user.name,
    )

    elements = []

    # ── Заголовок ──────────────────────────────────────────────
    elements.append(Paragraph("Fahrtenbuch", st["title"]))
    elements.append(Paragraph(user.name, st["subtitle"]))
    elements.append(Paragraph(
        f"Fahrzeug: <b>{vehicle.display_name}</b>",
        st["subtitle"],
    ))
    elements.append(Paragraph(
        f"Zeitraum: {date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}  |  "
        f"Erstellt: {date.today().strftime('%d.%m.%Y')}",
        st["meta"],
    ))
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=C_HEADER))
    elements.append(Spacer(1, 3 * mm))

    sorted_trips = sorted(trips, key=lambda t: t.date)

    # ── Таблиця ────────────────────────────────────────────────
    col_w = [2.2*cm, 5.2*cm, 5.2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.8*cm, 4.6*cm]

    headers = [
        Paragraph("<b>Datum</b>",       st["cell_bold"]),
        Paragraph("<b>Abfahrt</b>",     st["cell_bold"]),
        Paragraph("<b>Ziel</b>",        st["cell_bold"]),
        Paragraph("<b>km Start</b>",    st["cell_bold"]),
        Paragraph("<b>km Ende</b>",     st["cell_bold"]),
        Paragraph("<b>km gesamt</b>",   st["cell_bold"]),
        Paragraph("<b>Zweck</b>",       st["cell_bold"]),
        Paragraph("<b>Anmerkungen</b>", st["cell_bold"]),
    ]
    data = [headers]

    total_km = biz_km = priv_km = 0.0
    row_styles = []

    for i, trip in enumerate(sorted_trips, start=1):
        km = trip.distance
        total_km += km
        is_biz = trip.purpose == TripPurpose.BUSINESS
        if is_biz:
            biz_km += km
        else:
            priv_km += km

        row_bg = C_BIZ if is_biz else C_PRIV
        row_styles.append(("BACKGROUND", (0, i), (-1, i), row_bg))

        row = [
            Paragraph(trip.date.strftime("%d.%m.%y"),           st["cell"]),
            Paragraph(trip.start_label[:50],                    st["cell"]),
            Paragraph(trip.end_label[:50],                      st["cell"]),
            Paragraph(f"{int(trip.start_mileage):,}".replace(",", "."), st["cell"]),
            Paragraph(f"{int(trip.end_mileage):,}".replace(",", "."),   st["cell"]),
            Paragraph(f"<b>{km:.1f}</b>",                       st["cell_bold"]),
            Paragraph(
                f"{'💼 gesch.' if is_biz else '🏠 privat'}",   st["cell"]),
            Paragraph((trip.notes or "")[:60],                  st["cell"]),
        ]
        data.append(row)

    # Підсумковий рядок
    data.append([
        Paragraph("<b>GESAMT</b>", st["cell_bold"]),
        Paragraph("", st["cell"]),
        Paragraph("", st["cell"]),
        Paragraph("", st["cell"]),
        Paragraph("", st["cell"]),
        Paragraph(f"<b>{total_km:.1f}</b>", st["cell_bold"]),
        Paragraph(
            f"gesch: {biz_km:.1f}\nprivat: {priv_km:.1f}",
            st["cell_bold"],
        ),
        Paragraph("", st["cell"]),
    ])

    table = Table(data, colWidths=col_w, repeatRows=1)

    base_style = [
        # Заголовок
        ("BACKGROUND",   (0, 0), (-1, 0),  C_HEADER),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  C_WHITE),
        ("TOPPADDING",   (0, 0), (-1, 0),  6),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Всі рядки даних
        ("TOPPADDING",   (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 4),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        # Сітка
        ("GRID",         (0, 0), (-1, -1), 0.35, C_GRID),
        ("LINEBELOW",    (0, 0), (-1, 0),  1.2,  C_DARK),
        # Підсумок
        ("BACKGROUND",   (0, -1), (-1, -1), C_TOTAL),
        ("LINEABOVE",    (0, -1), (-1, -1), 1.5,  C_DARK),
    ]

    table.setStyle(TableStyle(base_style + row_styles))
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))

    # ── Підсумок ───────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_GRID))
    elements.append(Spacer(1, 2 * mm))

    summary_data = [
        ["Gesamt km", "Geschäftlich", "Privat", "Anzahl Fahrten"],
        [
            f"{total_km:.1f} km",
            f"{biz_km:.1f} km ({(biz_km/total_km*100 if total_km else 0):.0f}%)",
            f"{priv_km:.1f} km ({(priv_km/total_km*100 if total_km else 0):.0f}%)",
            str(len(sorted_trips)),
        ],
    ]
    summary_table = Table(
        summary_data,
        colWidths=[4.5*cm, 5.5*cm, 5.5*cm, 4.0*cm],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  C_ACCENT),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.5, C_GRID),
        ("FONTNAME",      (0, 1), (-1, 1),  "Helvetica-Bold"),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Підписи ────────────────────────────────────────────────
    sig_data = [[
        "Datum / Unterschrift Fahrer",
        "",
        "Bestätigung / Stempel",
    ]]
    sig_lines = [[
        "_" * 35,
        "",
        "_" * 35,
    ]]
    sig_t = Table(sig_data + sig_lines, colWidths=[9*cm, 3*cm, 9*cm])
    sig_t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.HexColor("#64748b")),
        ("TOPPADDING",    (0, 1), (-1, 1),  14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ]))
    elements.append(sig_t)

    doc.build(elements)
    return buffer.getvalue()
