# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Системні бібліотеки потрібні для matplotlib і psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо залежності зі Stage 1
COPY --from=builder /install /usr/local

# Копіюємо код
COPY . .

# Не-root користувач для безпеки
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import asyncio; from bot.config import settings; print('OK')" || exit 1

CMD ["python", "-m", "bot.main"]
