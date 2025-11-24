import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
import numpy as np

# ---------------- CONFIG ----------------
URL = "https://172.26.53.73:32443"
API_URL = f"{URL}/api/ds/knowledge/"
GET_DATASETS_URL = f"{URL}/api/owui/api/v1/knowledge/"
DKUBEX_API_KEY = ""
total_doc = 100
#PDF_PATH = ""  # absolute path of the dataset folder
PDF_PATH = "/home/data/con100"
owui_token = ""
user_name = "new"
CONCURRENT_USERS = 25
COMMON_COOKIE = ""
USERS = [f"{user_name}{i}" for i in range(1, CONCURRENT_USERS+1)]
POLL_INTERVAL = 15  # seconds
TIMEOUT = 2100      # seconds (35mins)
# ----------------------------------------

BASE_JSON = {
    "file_path": PDF_PATH,
    "knowledge_name": "",
    "knowledge_description": "",
    "concurrency_limit": 2,
}


async def create_dataset(session, username):
    """Send ingestion create request"""
    headers = {
        "content-type": "application/json",
        "Authorization": DKUBEX_API_KEY,
    }

    dataset_name = f"{username}dataset{uuid.uuid4().hex[:6]}"
    payload = json.loads(json.dumps(BASE_JSON))
    payload["knowledge_name"] = dataset_name
    payload["knowledge_description"] = dataset_name
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
        "authorization": DKUBEX_API_KEY,
        "owui-token": owui_token,
        "cookie": COMMON_COOKIE,
    }

    while (datetime.now() - start_time).total_seconds() < TIMEOUT:
        try:
            async with session.get(GET_DATASETS_URL, headers=headers, ssl=False) as resp:
                data = await resp.json()
                file_count = 0
                for ds in data:
                    if ds["name"] == dataset_name:
                        #print("i am at if block")
                        file_count = len(ds.get("data", {}).get("file_ids", []))
                        if file_count == total_doc:
                            total_time = (datetime.now() - start_time).total_seconds()
                            total_minutes = (datetime.now() - start_time).total_seconds() / 60
                            print(f"{username}: {dataset_name} completed in {total_minutes:.1f}min")
                            return {"user": username, "dataset": dataset_name, "time": total_minutes, "status": "completed"}
                       
        except Exception as e:
            #print(f"{username}: polling error: {e}")
            pass

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

    #Step 3: summarize
    print("\n Summary:")
    completed = [r for r in poll_results if r["status"] == "completed"]
    failed = [r for r in poll_results if r["status"] != "completed"]
    for r in poll_results:
        if r["status"] == "completed":
            print(f"dataset name : {r['dataset']} total_time: {r['time']}")

    if completed:
        times = [r["time"] for r in completed]
        print(f"   Completed: {len(completed)}")
        print(f"   Avg: {np.mean(times):.1f}min | Min: {min(times):.1f}min | Max: {max(times):.1f}min")
    print(f"   Failed/Timeout: {len(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
