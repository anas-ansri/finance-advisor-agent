FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create startup script
RUN echo '#!/bin/sh\n\
alembic upgrade head\n\
uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE ${PORT:-5000}

# Command to run the application
CMD ["/app/start.sh"]
