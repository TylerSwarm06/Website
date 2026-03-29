FROM python:3.12-slim

WORKDIR /app

# Install docker CLI for container stats
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]