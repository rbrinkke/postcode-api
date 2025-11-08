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

# Copy application source code
COPY src/ ./src/

# Expose port
EXPOSE 7777

# Health check - use /health endpoint for reliability
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f --max-time 2 http://localhost:7777/health || exit 1

# Run with production server using new src structure
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7777"]
