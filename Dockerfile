# Use official slim Python image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# No COPY! All code and requirements are mounted as volumes.
# Use venv and pip cache volumes for fast local dev.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

CMD ["bash"]

# To run CLI container, override CMD in docker-compose or with --entrypoint
