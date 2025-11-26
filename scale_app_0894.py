import asyncio
import aiohttp
import json
import time
import random
url = ""
API_URL = f"{url}/api/ds/apps/"
CONCURRENT_USERS = 25  # number of concurrent app creations

# Same cookie for all users
COMMON_COOKIE = ""
llm_url = ""
llm_key = ""
emb_url = ""
emb_key = ""
dataset_name = "user3_dataset_fac24d"

# Define each user's details
USERS = [{"username": f"user{i}", "namespace": f"user{i}-ns"} for i in range(1, 26)]



def build_app_payload(user, app_name, dataset_name):
    """Build the JSON payload for app creation."""
    return {
        "userapp": {
            "name": app_name,
            "url": f"/{app_name}",
            "image": "dkubex123/llmapp:general-securechat",
            "cpu_count": 1,
            "gpu_count": 0,
            "memory": 4,
            "docker_registry_server": "DOCKER_SERVER",
            "docker_registry_username": "DOCKER_USER",
            "docker_registry_password": "DOCKER_PASSWORD",
            "publish": True,
            "mount_home": "all",
            "hostname": "",
            "route_type": "ingress",
            "env": json.dumps({
                "APP_CONFIG_PATH": f"/home/{user['username']}/appData/{app_name}-publish/config.yaml",
                "FMQUERY_ARGS": f"llm --dataset {dataset_name} --config /home/{user['username']}/appData/{app_name}-publish/config.yaml"
            }),
            "ingress": json.dumps({
                "name": [
                    {"port": 3000, "rewrite-target": False, "ingress-prefix": f"/{app_name}"}
                ]
            })
        },
        "config_str": json.dumps({
            "dataset": dataset_name,
            "vectorstore": "weaviate_vectorstore",
            "embedding": "dkubex",
            "synthesizer": {
                "llm": "dkubex",
                "llm_url": {llm_url},
                "llmkey": {llm_key},
            },
            "embedding_url": {emb_url},
            "embedding_key": {emb_key},
        }),
    }


async def create_app(session, semaphore, user, app_index):
    """Send concurrent app creation request."""
    async with semaphore:
        app_name = f"app-{user['username']}-{int(time.time())}-{random.randint(100,999)}"
        
        payload = build_app_payload(user, app_name, dataset_name)

        headers = {
            "content-type": "application/json",
            "namespace": "sharmistha-choudhury",
            "username": "sharmistha-choudhury",
            "Cookie": COMMON_COOKIE,
        }

        try:
            async with session.post(API_URL, headers=headers, json=payload, ssl=False) as resp:
                text = await resp.text()
                print(f"[{user['username']}] App {app_name} -> Status {resp.status}")
                print(text[:500])  # print first 500 chars of response
        except Exception as e:
            print(f"[{user['username']}] Error creating {app_name}: {e}")


async def main():
    semaphore = asyncio.Semaphore(CONCURRENT_USERS)
    async with aiohttp.ClientSession() as session:
        tasks = [create_app(session, semaphore, user, i + 1) for i, user in enumerate(USERS)]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

