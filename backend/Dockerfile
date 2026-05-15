# ── Stage 1 : installation des dépendances ────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2 : image finale allégée ────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Utilisateur non-root (uid 1001)
RUN groupadd -g 1001 appgroup \
    && useradd -r -u 1001 -g appgroup -m appuser

# Dépendances copiées depuis le builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Code source
COPY --chown=appuser:appgroup . .

ENV PATH=/home/appuser/.local/bin:$PATH \
    HOME=/home/appuser \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
