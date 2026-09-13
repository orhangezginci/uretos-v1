FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]