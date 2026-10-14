FROM python:3.12-slim
WORKDIR /app
COPY services/shopfloor-bff-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ ./contracts/
COPY services/shopfloor-bff-api/src/ ./src/
WORKDIR /app/src
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]