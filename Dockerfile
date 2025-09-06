# Use Python base image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend code
COPY . .

# Expose port (optional for Cloud Run, but good for local)
EXPOSE 8080

# Set environment variables for Flask
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=flask_server.py \
    FLASK_ENV=production

# Start Flask
CMD ["python", "flask_server.py"]
