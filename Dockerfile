FROM python:3.13-slim

# Install build dependencies, install Python packages, then remove build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential python3-dev libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy app
COPY app.py /app/

# Create data directory
RUN mkdir -p /data

# Healthcheck: fail if no log update in 10 minutes
HEALTHCHECK --interval=5m --timeout=10s --retries=3 CMD \
    [ -f /data/app.log ] && \
    find /data/app.log -mmin -10 | grep -q app.log || exit 1

# Run app
CMD ["python", "app.py"]
