FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY README.md .
COPY ads_grafana_toolkit/ ./ads_grafana_toolkit/

RUN pip install --no-cache-dir ".[web,nlp]"

# Create data directory for SQLite
RUN mkdir -p /data

# Set environment variables
ENV DATABASE_PATH=/data/dashboards.db
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"

# Run the server
CMD ["python", "-m", "ads_grafana_toolkit.web.app"]
