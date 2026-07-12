FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY importer.py .

ENV FLASK_APP=app
ENV PYTHONPATH=/app

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:create_app()"]
