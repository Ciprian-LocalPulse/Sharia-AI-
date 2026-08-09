FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN addgroup --system sharia && adduser --system --ingroup sharia sharia
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install .
# دليل لسجلّ التدقيق الدائم (SQLite) — يُفترض ربطه بوحدة تخزين خارجية
# (docker volume / K8s PersistentVolume) عبر SHARIA_AI_AUDIT_DB_PATH=/data/...
RUN mkdir -p /data && chown sharia:sharia /data
USER sharia
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"
CMD ["uvicorn", "sharia_ai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]