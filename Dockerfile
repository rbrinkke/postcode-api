FROM python:3.11-slim

# Install system dependencies including curl for healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port
EXPOSE 7777

# Health check - test postcode endpoint with 1 second timeout
HEALTHCHECK --interval=30s --timeout=1s --start-period=10s --retries=3 \
    CMD curl -f --max-time 1 http://localhost:7777/postcode/1012AB || exit 1

# Run with production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7777"]
