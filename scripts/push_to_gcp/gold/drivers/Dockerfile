FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt /app/scripts/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/scripts/requirements.txt

COPY gold_drivers.py /app/scripts/gold/gold_drivers.py

CMD ["python", "/app/scripts/gold/gold_drivers.py"]