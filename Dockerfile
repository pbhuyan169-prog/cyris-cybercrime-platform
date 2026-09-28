# Base Image: Lightweight Python
FROM python:3.11-slim

# Prevent Python from buffering standard output / writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Seed initial database for demonstration
RUN python backend/seed_data.py

# Expose port
EXPOSE 8000

# Start command with dynamic PORT support for Cloud / Container platforms
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]