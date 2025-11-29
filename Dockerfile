FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Expose API port
EXPOSE 8000

# Run server
CMD ["python", "scripts/run_server.py"]
