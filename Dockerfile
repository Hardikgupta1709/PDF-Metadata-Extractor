FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY src/ ./src/
ENV PORT=10000
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app
