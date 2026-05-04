FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt /app/scripts/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/scripts/requirements.txt

COPY gold_sessions.py /app/scripts/gold/gold_sessions.py

CMD ["python", "/app/scripts/gold/gold_sessions.py"]