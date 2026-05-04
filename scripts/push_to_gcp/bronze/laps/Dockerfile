FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt /app/scripts/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/scripts/requirements.txt

COPY fetch_laps_bronze.py /app/scripts/bronze/fetch_laps_bronze.py

CMD ["python", "/app/scripts/bronze/fetch_laps_bronze.py"]