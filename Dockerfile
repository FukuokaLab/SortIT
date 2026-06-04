FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/app

WORKDIR /app

RUN groupadd --system app && \
    useradd --system --gid app --home /app --no-create-home app && \
    apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/data /app/staticfiles \
    && chown -R app:app /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/account/login/')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/FukuokaLab/SortIT"
