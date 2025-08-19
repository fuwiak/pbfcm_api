# Playwright Python base with browsers preinstalled (v1.54)
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_MODULE=pbfcm_api:app  # change to api:app if you want the other scraper

WORKDIR /app

# Install only your app deps (includes playwright==1.54.0)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build-time smoke check (no reliance on __version__ attribute)
RUN python - <<'PY'
import sys, platform
from importlib.metadata import version, PackageNotFoundError
print("python:", sys.version)
try:
    print("playwright:", version("playwright"))
except PackageNotFoundError:
    print("playwright: MISSING")
    raise SystemExit(1)
PY

# Copy app code
COPY . .

# Make sure the start script is executable
RUN chmod +x start.sh

EXPOSE 8000

# Single worker so one Chromium instance is reused per process
CMD ["bash", "-lc", "./start.sh"]
