FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Install package
RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "framework.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
