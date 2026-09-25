# 1. Base Image: Use a lightweight Python image
FROM python:3.11-slim

# 2. Prevent Python from buffering standard output / writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Set working directory inside the container
WORKDIR /app

# 4. Copy requirements first to leverage Docker cache
COPY requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code
COPY . .

# 7. Expose application port
EXPOSE 8000

# 8. Start command (e.g., using uvicorn for FastAPI/ASGI, or python main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]