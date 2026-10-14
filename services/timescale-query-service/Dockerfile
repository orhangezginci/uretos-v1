FROM python:3.12-slim
WORKDIR /app
COPY services/timescale-query-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ ./contracts/
COPY services/timescale-query-service/src/ ./src/
WORKDIR /app/src
CMD ["python", "main.py"]