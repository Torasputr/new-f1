from google.cloud import storage
import os
from dotenv import load_dotenv
from urllib.request import urlopen
import json
import pandas as pd
from io import BytesIO

load_dotenv()

LINK = "https://api.openf1.org/v1/drivers?session_key=latest"
GCS_BUCKET = os.getenv("GCS_BUCKET", "").strip()
GCS_BLOB_PATH = os.getenv("GCS_BLOB_PATH", "").strip()
SEASON = int(os.getenv("SEASON", ""))
GCS_MEDAL_PUSH = os.getenv("GCS_MEDAL_PUSH", "").strip()
GCS_BLOB_PATH = f"{GCS_MEDAL_PUSH}/season={SEASON}/driver.parquet"


def upload_parquet(df, bucket, blob_path):
    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(blob_path)
    blob.upload_from_file(
        buf, content_type="application/vnd.apache.parquet", size=len(buf.getvalue())
    )
    # df.to_csv("../../data/bronze/drivers.csv", index=False)


def main():
    print(f"[INFO] Fetching drivers for season {SEASON} from openf1 API")
    with urlopen(LINK) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)

    print(f"[INFO] Converting data to pandas DataFrame")
    df = pd.DataFrame(data)

    print(f"[INFO] Uploading DataFrame to GCS")
    upload_parquet(df, GCS_BUCKET, GCS_BLOB_PATH)
    print(f"[INFO] Uploaded DataFrame to GCS on {GCS_BLOB_PATH}")


if __name__ == "__main__":
    main()
