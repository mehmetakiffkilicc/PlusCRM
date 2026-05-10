# Sync Worker Dockerfile - Build Version V4-FORCE-REFRESH
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    unixodbc-dev \
    gcc \
    g++ \
    curl \
    gnupg \
    socat \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && mkdir -p /usr/share/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 tdsodbc freetds-dev \
    && rm -rf /var/lib/apt/lists/*
    
# Configure FreeTDS to use protocol version 7.3 or 8.0
RUN echo "[global]\n\ttds version = 7.3\n\tclient charset = UTF-8\n" > /etc/freetds/freetds.conf

# Fix OpenSSL configuration to allow legacy TLS connections (resolves 10054 TCP Provider error)
RUN sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g' /etc/ssl/openssl.cnf || true \
    && sed -i 's/MinProtocol = TLSv1.2/MinProtocol = TLSv1/g' /etc/ssl/openssl.cnf || true

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project and startup script
COPY . .
RUN chmod +x start-tailscale.sh

# Run with Tailscale
CMD ["./start-tailscale.sh", "python", "scheduler_service.py"]
