import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
import numpy as np

# ---------------- CONFIG ----------------
URL = ""
API_URL = f"{URL}/api/fm/dataset/create"
GET_DATASETS_URL = f"{URL}/api/fm/dataset"
DKUBEX_API_KEY = ""
PDF_PATH = "/home/data/con100"
NAMESPACE = "sharmistha-choudhury"
users_name = "new"
CONCURRENT_USERS = 30
embedding_url = ""
embedding_key = ""
USERS = [f"{users_name}{i}" for i in range(1, CONCURRENT_USERS+1)]
POLL_INTERVAL = 15  # seconds
TIMEOUT = 2100      # seconds (35 mins)


# ----------------------------------------

COMMON_COOKIE = ""

BASE_JSON = {
    "name": "testmaha",
    "publish": True,
    "username": "",
    "splitter": {"type": "token_text_splitter", "config": {"chunk_size": 256, "chunk_overlap": 0}},
    "embedding": {"type": "dkubex", "config": {"embedding_url": embedding_url, "embedding_key": embedding_key}},
    "pipeline": "default",
    "dkubex_api_key": DKUBEX_API_KEY,
    "num_workers": 1,
    "cache_enabled": False,
    "metadata": "default",
    "adjacent_chunks": False,
    "mlflow": {"experiment": "Default"},
    "mode": "sync",
    "reader": [{
        "type": "filereader",
        "config": {
            "loader": {"input_dir": PDF_PATH, "recursive": True, "use_unstructure": False},
            "delete": False,
        },
    }],
}


async def create_dataset(session, username):
    """Send ingestion create request"""
    headers = {
        "content-type": "application/json",
        "namespace": NAMESPACE,
        "username": NAMESPACE,
        "cookie": COMMON_COOKIE,
    }

    dataset_name = f"{username}_dataset_{uuid.uuid4().hex[:6]}"
    payload = json.loads(json.dumps(BASE_JSON))
    payload["name"] = dataset_name
    payload["username"] = NAMESPACE
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = datetime.now()
    try:
        async with session.post(API_URL, headers=headers, json=payload, ssl=False) as resp:
            text = await resp.text()
            print(f"Sent ingestion for : {dataset_name} ({resp.status}) start_time : {start_time_str}")
            return {"user": username, "dataset": dataset_name, "status": resp.status, "start": start_time}
    except Exception as e:
        print(f"Failed to send ingestion for {username}: {e}")
        return {"user": username, "dataset": None, "status": "error", "error": str(e)}


async def poll_until_completed(session, username, dataset_name, start_time):
    """Poll the GET /dataset API to see when this dataset becomes completed"""
    headers = {
        "namespace": NAMESPACE,
        "username": NAMESPACE,
        "cookie": COMMON_COOKIE,
    }

    while (datetime.now() - start_time).total_seconds() < TIMEOUT:
        try:
            async with session.get(GET_DATASETS_URL, headers=headers, ssl=False) as resp:
                data = await resp.json()
                for ds in data:
                    if ds["dataset_name"] == dataset_name:
                        status = ds["status"].lower()
                        if status == "completed":
                            total_time = (datetime.now() - start_time).total_seconds() / 60
                            print(f"{username}: {dataset_name} completed in {total_time:.1f}min")
                            return {"user": username, "dataset": dataset_name, "time": total_time, "status": "completed"}
                        elif status in ("failed", "error"):
                            print(f" {username}: {dataset_name} failed")
                            return {"user": username, "dataset": dataset_name, "status": status}
        except Exception as e:
            print(f"{username}: polling error: {e}")

        await asyncio.sleep(POLL_INTERVAL)

    print(f"{username}: {dataset_name} timed out")
    return {"user": username, "dataset": dataset_name, "status": "timeout"}


async def main():
    async with aiohttp.ClientSession() as session:
        # Step 1: send all ingestion requests concurrently
        ingestion_results = await asyncio.gather(*[create_dataset(session, u) for u in USERS])
        valid_datasets = [r for r in ingestion_results if r.get("dataset")]
        print(f"valid dataset : {valid_datasets}")

        # Step 2: poll all concurrently
        poll_results = await asyncio.gather(
            *[poll_until_completed(session, ds["user"], ds["dataset"], ds["start"]) for ds in valid_datasets]
        )

    # Step 3: summarize
    print("\n Summary:")
    completed = [r for r in poll_results if r["status"] == "completed"]
    failed = [r for r in poll_results if r["status"] != "completed"]

    if completed:
        times = [r["time"] for r in completed]
        print(f"   Completed: {len(completed)}")
        print(f"   Avg: {np.mean(times):.1f}min | Min: {min(times):.1f}min | Max: {max(times):.1f}min")
    print(f"   Failed/Timeout: {len(failed)}")


if __name__ == "__main__":
    asyncio.run(main())

