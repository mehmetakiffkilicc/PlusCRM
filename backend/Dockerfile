# Backend Dockerfile - Build Version V3
FROM python:3.12-slim

# Set environment variables (using recommended key=value format)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p staticfiles logs

# Collect static files at build time (avoids ~15s runtime delay on every deploy)
RUN SECRET_KEY=build-time-static-key DATABASE_URL=sqlite:///tmp/build.db \
    python manage.py collectstatic --noinput

# Copy and prepare startup script
COPY start.sh .
RUN chmod +x start.sh

# Railway sets the PORT environment variable automatically
CMD ["./start.sh"]
