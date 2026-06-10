"""
stats_chart.py — генерація PNG-діаграм статистики поїздок.
Використовує matplotlib з Agg backend (без дисплею).
"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date, timedelta
from collections import defaultdict
from typing import List
from ..models import Trip, TripPurpose


def _week_label(d: date) -> str:
    """Повертає мітку тижня: 'KW12\n20.03'"""
    iso = d.isocalendar()
    return f"KW{iso[1]}\n{d.strftime('%d.%m')}"


def generate_weekly_chart(trips: List[Trip], lang: str = "de") -> bytes:
    """
    Генерує стовпчасту діаграму пробігу за останні 8 тижнів.
    Ділові — зелений, приватні — жовтий.
    Повертає PNG у байтах.
    """
    today = date.today()
    # Початок поточного тижня (понеділок)
    week_start = today - timedelta(days=today.weekday())

    # 8 тижнів назад
    weeks: list[date] = [week_start - timedelta(weeks=i) for i in range(7, -1, -1)]

    biz_km:  dict[date, float] = defaultdict(float)
    priv_km: dict[date, float] = defaultdict(float)

    for trip in trips:
        # Знаходимо понеділок тижня поїздки
        trip_week = trip.date - timedelta(days=trip.date.weekday())
        if trip_week in [w for w in weeks]:
            if trip.purpose == TripPurpose.BUSINESS:
                biz_km[trip_week]  += trip.distance
            else:
                priv_km[trip_week] += trip.distance

    labels = [_week_label(w) for w in weeks]
    biz_vals  = [round(biz_km[w],  1) for w in weeks]
    priv_vals = [round(priv_km[w], 1) for w in weeks]

    x = range(len(weeks))
    bar_w = 0.38

    titles = {"de": "Kilometerübersicht — letzte 8 Wochen",
               "ua": "Пробіг — останні 8 тижнів",
               "ru": "Пробег — последние 8 недель",
               "en": "Mileage — last 8 weeks"}
    biz_label  = {"de": "Geschäftlich", "ua": "Ділові",   "ru": "Деловые",  "en": "Business"}
    priv_label = {"de": "Privat",       "ua": "Приватні", "ru": "Частные",  "en": "Private"}

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    bars_b = ax.bar([i - bar_w/2 for i in x], biz_vals,  width=bar_w,
                    color="#22c55e", label=biz_label.get(lang, "Business"),  zorder=3)
    bars_p = ax.bar([i + bar_w/2 for i in x], priv_vals, width=bar_w,
                    color="#eab308", label=priv_label.get(lang, "Private"), zorder=3)

    # Підписи значень
    for bar in bars_b:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f"{h:.0f}",
                    ha="center", va="bottom", fontsize=7.5, color="#166534", fontweight="bold")
    for bar in bars_p:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f"{h:.0f}",
                    ha="center", va="bottom", fontsize=7.5, color="#854d0e", fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("km", fontsize=9)
    ax.set_title(titles.get(lang, titles["de"]), fontsize=11, fontweight="bold", pad=10)
    ax.legend(fontsize=9, framealpha=0.7)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.spines[["top","right"]].set_visible(False)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_purpose_pie(trips: List[Trip], lang: str = "de") -> bytes:
    """Кругова діаграма: ділові vs приватні км."""
    biz  = sum(t.distance for t in trips if t.purpose == TripPurpose.BUSINESS)
    priv = sum(t.distance for t in trips if t.purpose == TripPurpose.PRIVATE)

    if biz + priv == 0:
        return b""

    titles = {"de": "Fahrtenverteilung (gesamt)",
               "ua": "Розподіл поїздок (всього)",
               "ru": "Распределение поездок (всего)",
               "en": "Trip breakdown (total)"}
    biz_l  = {"de": f"Geschäftlich\n{biz:.0f} km",
               "ua": f"Ділові\n{biz:.0f} км",
               "ru": f"Деловые\n{biz:.0f} км",
               "en": f"Business\n{biz:.0f} km"}
    priv_l = {"de": f"Privat\n{priv:.0f} km",
               "ua": f"Приватні\n{priv:.0f} км",
               "ru": f"Частные\n{priv:.0f} км",
               "en": f"Private\n{priv:.0f} km"}

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor("#f8fafc")
    wedges, texts, autotexts = ax.pie(
        [biz, priv],
        labels=[biz_l.get(lang, biz_l["de"]), priv_l.get(lang, priv_l["de"])],
        colors=["#22c55e", "#eab308"],
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax.set_title(titles.get(lang, titles["de"]), fontsize=11, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
