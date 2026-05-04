import os
from dotenv import load_dotenv
from urllib.request import urlopen
from urllib.error import HTTPError
import json
import pandas as pd
from google.cloud import storage
from io import BytesIO
import time

load_dotenv()

BASE_URL = os.getenv("BASE_URL").strip().strip("/")
SEASON = int(os.getenv("SEASON"))

URL = f"{BASE_URL}/sessions?year={SEASON}"
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
BLOB_PATH = f"{GCS_MEDAL_PUSH}/season={SEASON}/laps/all_session_laps.parquet"

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()


def fetch_json(url):
    try:
        with urlopen(url) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        if e.code == 404:
            return []
        raise
    return json.loads(raw)


def all_sessions_for_season():
    data = fetch_json(URL)
    dataframe = pd.DataFrame(data)
    if dataframe.empty:
        return dataframe
    dataframe["date_start"] = pd.to_datetime(dataframe["date_start"], utc=True)
    dataframe = dataframe.sort_values(by="date_start", ascending=True)
    return dataframe


def main():
    print(f"[INFO] Fetching sessions for season {SEASON}")
    sessions = all_sessions_for_season()
    sessions = sessions.dropna(subset=["session_key"]).copy()
    sessions["session_key"] = sessions["session_key"].astype(int)
    chunks = []

    for row in sessions.itertuples(index=False):
        laps_url = f"{BASE_URL}/laps?session_key={int(row.session_key)}"
        print(f"[INFO] Fetching laps for session {row.session_key}")
        rows = fetch_json(laps_url)
        if rows:
            chunks.append(pd.DataFrame(rows))
        time.sleep(2)

    if not chunks:
        print(f"[INFO] No laps found for season {SEASON}")
        return

    print(f"[INFO] Concatenating chunks")
    df = pd.concat(chunks, ignore_index=True)
    df["ingested_at"] = pd.Timestamp.now(tz="UTC")

    buf = BytesIO()
    df.to_parquet(buf, index=False)
    # df.to_csv("../../data/bronze/all_session_laps.csv", index=False)
    buf.seek(0)

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(BLOB_PATH)
    blob.upload_from_file(
        buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue())
    )
    print(f"[INFO] Uploaded DataFrame to GCS on {BLOB_PATH}")


if __name__ == "__main__":
    main()
