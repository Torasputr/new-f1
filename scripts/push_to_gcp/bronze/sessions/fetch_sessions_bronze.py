from urllib.request import urlopen
import os
from dotenv import load_dotenv
import json
import pandas as pd
from io import BytesIO
from google.cloud import storage

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()

BASE_URL = os.getenv("BASE_URL").strip().strip("/")
SEASON = int(os.getenv("SEASON"))
URL = f"{BASE_URL}/sessions?year={SEASON}"
GCS_MEDAL = os.getenv("GCS_MEDAL", "").strip()

GCS_BLOB_PATH=f"{GCS_MEDAL}/season={SEASON}/session.parquet"

def upload_parquet(df, bucket, blob_path):
    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(blob_path)

    blob.upload_from_file(buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue()))

def main():
    print(f"[INFO] Fetching sessions for season {SEASON} from openf1 API")
    with urlopen(URL) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)

    print(f"[INFO] Converting data to pandas DataFrame")
    df = pd.DataFrame(data)
    
    ingested_at = pd.Timestamp.now(tz="UTC")
    df["ingested_at"] = ingested_at

    print(f"[INFO] Uploading DataFrame to GCS")
    upload_parquet(df, GCS_BUCKET, GCS_BLOB_PATH)
    print(f"[INFO] Uploaded DataFrame to GCS on {GCS_BLOB_PATH}")

if __name__ == "__main__":
    main()
