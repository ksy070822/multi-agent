# Railway Deployment Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the petcare_advisor package
COPY petcare_advisor/ ./petcare_advisor/

# Install the package in editable mode
WORKDIR /app/petcare_advisor
RUN pip install -e .

# Set PYTHONPATH
ENV PYTHONPATH=/app/petcare_advisor/src

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Start command
CMD ["sh", "-c", "python -m uvicorn petcare_advisor.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
