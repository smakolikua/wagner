"""
ocr_service.py — розпізнавання чеків через Claude Vision API.

Workflow:
1. Отримуємо Telegram photo → завантажуємо байти
2. Відправляємо в Claude claude-sonnet-4-20250514 з base64 зображенням
3. Парсимо структурований JSON відповідь
4. Повертаємо OCRResult з усіма полями чека

Fallback: якщо API недоступний або впевненість < 0.5 — просимо ввести вручну.
"""
import base64
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import httpx
from loguru import logger


@dataclass
class OCRResult:
    """Результат розпізнавання чека."""
    success: bool
    confidence: float = 0.0

    # Основні поля
    amount_gross: Optional[float] = None   # загальна сума з ПДВ
    amount_net: Optional[float] = None     # без ПДВ
    vat_amount: Optional[float] = None     # сума ПДВ
    vat_rate: int = 0                      # 0 / 7 / 19

    date: Optional[date] = None
    vendor: Optional[str] = None
    description: Optional[str] = None

    # Пропонована категорія (назва)
    suggested_category: Optional[str] = None
    # Чи ділова витрата
    is_business: bool = True

    raw_text: str = ""
    error: Optional[str] = None


_SYSTEM_PROMPT = """Du bist ein Buchhalter-Assistent. Analysiere das Bild eines Kassenbons oder einer Rechnung.
Antworte NUR mit einem JSON-Objekt, ohne Markdown, ohne Erklärungen.

JSON-Schema:
{
  "amount_gross": <float|null>,
  "amount_net": <float|null>,
  "vat_amount": <float|null>,
  "vat_rate": <0|7|19>,
  "date": "<DD.MM.YYYY>"|null,
  "vendor": "<string>"|null,
  "description": "<kurze Beschreibung>"|null,
  "suggested_category": "<Bürobedarf|Kfz-Kosten|Reisekosten|Bewirtungskosten|Telefon/Internet|Miete/Pacht|Sonstige BA|Privat>",
  "is_business": <true|false>,
  "confidence": <0.0-1.0>
}

Regeln:
- amount_gross = Gesamtbetrag inkl. MwSt
- Wenn MwSt nicht erkennbar: vat_rate=0, amount_net=amount_gross
- date im Format DD.MM.YYYY
- confidence: 1.0 = alle Felder klar lesbar, 0.5 = mehrere Felder unklar"""


async def extract_receipt_data(image_bytes: bytes, lang: str = "de") -> OCRResult:
    """
    Основна функція: байти зображення → OCRResult.
    Використовує Claude Vision через Anthropic API.
    """
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 512,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analysiere diesen Kassenbon/Rechnung und gib das JSON zurück."
                    }
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data["content"][0]["text"].strip()
        return _parse_claude_response(raw_text)

    except httpx.TimeoutException:
        logger.warning("Claude Vision API timeout")
        return OCRResult(success=False, error="⏱ API timeout. Введіть дані вручну.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Claude Vision API error: {e.response.status_code}")
        return OCRResult(success=False, error=f"❌ API помилка {e.response.status_code}. Введіть вручну.")
    except Exception as e:
        logger.error(f"OCR unexpected error: {e}")
        return OCRResult(success=False, error="❌ Помилка розпізнавання. Введіть дані вручну.")


def _parse_claude_response(raw: str) -> OCRResult:
    """Парсить JSON відповідь від Claude."""
    # Витягуємо JSON якщо є зайвий текст
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        return OCRResult(success=False, raw_text=raw,
                        error="Не вдалося розпізнати структуру відповіді.")
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        return OCRResult(success=False, raw_text=raw, error=f"JSON parse error: {e}")

    # Парсимо дату
    receipt_date = None
    if data.get("date"):
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                receipt_date = datetime.strptime(data["date"], fmt).date()
                break
            except ValueError:
                continue

    # Обчислюємо net якщо є gross і vat_rate
    amount_gross = _safe_float(data.get("amount_gross"))
    amount_net   = _safe_float(data.get("amount_net"))
    vat_amount   = _safe_float(data.get("vat_amount"))
    vat_rate     = int(data.get("vat_rate") or 0)

    if amount_gross and vat_rate and not amount_net:
        amount_net = round(amount_gross / (1 + vat_rate / 100), 2)
        vat_amount = round(amount_gross - amount_net, 2)

    confidence = float(data.get("confidence") or 0.5)

    return OCRResult(
        success=True,
        confidence=confidence,
        amount_gross=amount_gross,
        amount_net=amount_net,
        vat_amount=vat_amount,
        vat_rate=vat_rate,
        date=receipt_date,
        vendor=data.get("vendor"),
        description=data.get("description"),
        suggested_category=data.get("suggested_category"),
        is_business=bool(data.get("is_business", True)),
        raw_text=raw,
    )


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        # Нормалізуємо "1.234,56" → "1234.56"
        s = str(val).replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return round(float(s), 2)
    except (ValueError, TypeError):
        return None


def format_ocr_preview(result: OCRResult, lang: str = "de") -> str:
    """Форматує результат OCR для показу користувачу перед підтвердженням."""
    lines = []

    conf_bar = "🟢" if result.confidence >= 0.8 else "🟡" if result.confidence >= 0.5 else "🔴"
    lines.append(f"{conf_bar} <b>Розпізнано</b> (впевненість: {result.confidence:.0%})\n")

    if result.amount_gross:
        lines.append(f"💶 Сума: <b>{result.amount_gross:.2f} €</b>")
        if result.vat_rate:
            lines.append(f"   з них ПДВ {result.vat_rate}%: {result.vat_amount:.2f} €")
    else:
        lines.append("💶 Сума: <i>не розпізнано</i>")

    if result.date:
        lines.append(f"📅 Дата: <b>{result.date.strftime('%d.%m.%Y')}</b>")
    else:
        lines.append("📅 Дата: <i>не розпізнано</i>")

    if result.vendor:
        lines.append(f"🏪 Постачальник: <b>{result.vendor}</b>")

    if result.description:
        lines.append(f"📝 Опис: {result.description}")

    if result.suggested_category:
        lines.append(f"🏷 Категорія: <b>{result.suggested_category}</b>")

    type_label = "💼 Ділова" if result.is_business else "🏠 Приватна"
    lines.append(f"📌 Тип: {type_label}")

    return "\n".join(lines)
