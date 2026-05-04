from google.cloud import storage
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_MEDAL_FETCH = os.getenv("GCS_MEDAL_FETCH", "").strip()
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
SEASON = int(os.getenv("SEASON"))
BLOB_PATH = f"{GCS_MEDAL_FETCH}/season={SEASON}/laps/all_session_laps.parquet"

BLOB_PATH_PUSH = f"{GCS_MEDAL_PUSH}/season={SEASON}/laps/all_session_laps.parquet"

BLOB_PATH_SESSIONS = f"gold/season={SEASON}/session.parquet"

def main():
    print(f"[INFO] Fetching laps for season {SEASON} from {BLOB_PATH}")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(BLOB_PATH)
    df = pd.read_parquet(BytesIO(blob.download_as_bytes()))

    print(f"[INFO] Fetching sessions for season {SEASON} from {BLOB_PATH_SESSIONS}")
    blob_sessions = bucket.blob(BLOB_PATH_SESSIONS)
    df_sessions = pd.read_parquet(BytesIO(blob_sessions.download_as_bytes()))

    print(f"[INFO] Filling empty date start with session start") 
    session_start = (
        df_sessions.drop_duplicates("session_key").set_index("session_key")["date_start"]
    )

    df["date_start"] = df["date_start"].fillna(df["session_key"].map(session_start))
    df["date_start"] = pd.to_datetime(df["date_start"], errors="coerce")
    
    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    blob_push = bucket.blob(BLOB_PATH_PUSH)
    blob_push.upload_from_file(buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue()))
    print(f"[INFO] Uploaded DataFrame to GCS on {BLOB_PATH_PUSH}")

if __name__ == "__main__":
    main()