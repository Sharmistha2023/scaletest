import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
import numpy as np
from contextlib import redirect_stdout
import aiohttp
import click

headers = {
    # 'X-SLLM-Request-Id': '032adb4b-7837-4a5f-a027-b4820d386b0a',
    # 'x-dkubex-conversation-id': '966036d2-640e-47e3-b1ea-6a0c4380426c',
    # 'X-Auth-Request-Email': 'sharmistha.choudhury@oneconvergence.com'
}

@click.command()
@click.option('--no-of-streams', '-n', default=5, help='Number of parallel streams.')
@click.option('--questions-file', '-q', required=True, type=click.Path(exists=True),
              help='Path to the file containing questions.')
@click.option('--duration', '-d', required=True, type=int, help='Duration to run (in minutes).')
def main(no_of_streams, questions_file, duration):
    securechat_key = os.getenv("SECURECHAT_KEY", "allow")
    f = open(f"file_duration_{no_of_streams}_{duration}min.txt", "w+")
    if not securechat_key:
        print("Export securechat application key as - export SECURECHAT_KEY=<application key>")
        sys.exit(1)

    with open(questions_file, 'r') as file:
        questions = [line.strip() for line in file if line.strip()]
   
    print(f"Streaming for duration (mins): {duration}")
    f.write(f"Streaming for duration (mins): {duration}\n")
    f.write(".....................................................\n")

    json_data = {
    "model": "llama3.2:1b",
    "messages": [
        {"role": "user", "content": "who is krishna"}
      ],
      "files": [
        {"type": "file", "id": "b376c0be-528e-4c2c-86f4-486dd718429e"}
      ]
    }

    #url = "http://3.142.69.119:31932/new/api/chat/"
    # without securellm
    #url = "http://172.26.53.22:30129/app3/api/chat/"
    # with securellm
    url = "<url>/api/chat/completions"
    loop = asyncio.get_event_loop()
    mylist = []

    loop.run_until_complete(run_for_duration(
        duration, no_of_streams, questions, url, headers, json_data, f, mylist
    ))

    # Print first-token latency distribution
    time_taken_less_10 = 0
    time_taken_less_20 = 0
    time_taken_less_30 = 0
    time_taken_greater_60 = 0

    for latency in mylist:
        if latency is None:
            continue
        if latency < 10.0:
            time_taken_less_10 += 1
        elif 10.0 <= latency < 20.0:
            time_taken_less_20 += 1
        elif 20.0 <= latency < 30.0:
            time_taken_less_30 += 1
        elif latency > 60.0:
            time_taken_greater_60 += 1

    print(f"time_taken_less_than_10: {time_taken_less_10}\n ")
    print(f"time_taken_less_than_20: {time_taken_less_20}\n ")
    print(f"time_taken_less_than_30: {time_taken_less_30}\n ")
    print(f"time_taken_greater_than_60: {time_taken_greater_60}\n ")

    f.write(f"time_taken_less_than_10: {time_taken_less_10}\n ")
    f.write(f"time_taken_less_than_20: {time_taken_less_20}\n ")
    f.write(f"time_taken_less_than_30: {time_taken_less_30}\n ")
    f.write(f"time_taken_greater_than_60: {time_taken_greater_60}\n ")

    f.close()
    count = 0
    file_path = f"file_duration_{no_of_streams}_{duration}min.txt"
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip().startswith("Received Response:"):
                count += 1
    print(f"number of response received: {count}\n ")
    f.close()



async def fetch(session, url, headers, json_data, question, f, mylist):
    json_data["messages"][0]["content"] = question
    json_data["request_id"] = str(uuid.uuid4())
    start_time = datetime.now()

    fetch_data = {
        "question": question,
        "request_id": json_data["request_id"],
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    answer = ""
    first_token = True

    print(f"Send Q: {question} to url: {url}")
    f.write(f"Send Q: {question} to url: {url} \n")
    #headers['X-SLLM-Request-Id'] = str(uuid.uuid4())
    headers.update({"Authorization": f"Bearer {os.getenv('SECURECHAT_KEY')}"})

    try:
        response = await asyncio.wait_for(session.post(url, headers=headers, json=json_data, ssl=False), timeout=120)
        async with response:
            async for data in response.content.iter_any():
                if first_token:
                    first_token = False
                    first_token_arrival = datetime.now()
                    diff = first_token_arrival - start_time
                    fetch_data.update({
                        "first_token_arrival": first_token_arrival.strftime("%Y-%m-%d %H:%M:%S"),
                        "first_token_latency": round(diff.total_seconds(), 2)
                    })
                answer += data.decode("utf-8")

            end_time = datetime.now()
            fetch_data.update({
                "answer": answer,
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_time": round((end_time - start_time).total_seconds(), 2)
            })

    except asyncio.TimeoutError:
        f.write(f"Request for question: {question} timed out after 120 seconds \n")
        print(f"Request for question: {question} timed out after 120 seconds")
        fetch_data["timeout"] = True
        return fetch_data

    print(f"Received Response: {question} in {'{:.2f}'.format(fetch_data['total_time'])} sec")
    f.write("...............\n")
    f.write(f"Received Response: {question} in {'{:.2f}'.format(fetch_data['total_time'])} sec\n")

    print(f"⏱️ Request Sent At      : {fetch_data['start_time']}")
    print(f"🕒 First Token At       : {fetch_data.get('first_token_arrival', 'N/A')}")
    print(f"⚡ First Token Latency  : {fetch_data.get('first_token_latency', 'N/A')} sec")
    print(f"⏳ Total Response Time  : {fetch_data['total_time']} sec")

    mylist.append(fetch_data.get("first_token_latency"))

    f.write(f"⏱️ Request Sent At      : {fetch_data['start_time']} \n")
    f.write(f"🕒 First Token At       : {fetch_data.get('first_token_arrival', 'N/A')} \n")
    f.write(f"⚡ First Token Latency  : {fetch_data.get('first_token_latency', 'N/A')} sec \n")
    f.write(f" Total Response Time  : {fetch_data['total_time']} sec \n")
    f.write("..........................\n\n")

    return fetch_data

async def fetch_with_semaphore(semaphore, session, url, headers, json_data, question, f, mylist):
    async with semaphore:
        return await fetch(session, url, headers, json_data, question, f, mylist)

async def run_for_duration(duration_minutes, no_of_streams, questions, url, headers, json_data, f, mylist):
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    semaphore = asyncio.Semaphore(no_of_streams)
    times_token = []
    times_resp = []
    timeout_count = 0
    index = 0
    total_tasks = 0

    async with aiohttp.ClientSession(trust_env=True) as session:
        while datetime.now() < end_time:
            batch_questions = [questions[index % len(questions)] for _ in range(no_of_streams)]
            index += 1
            tasks = [
                fetch_with_semaphore(semaphore, session, url, headers, json_data, question, f, mylist)
                for question in batch_questions
            ]
            responses = await asyncio.gather(*tasks)
            total_tasks += len(responses)

            for fetch_data in responses:
                if 'timeout' in fetch_data:
                    timeout_count += 1
                elif 'total_time' in fetch_data:
                    times_token.append(fetch_data.get('first_token_latency'))
                    times_resp.append(fetch_data.get('total_time'))

        print(f"\nFinished {total_tasks} requests in {duration_minutes} minutes.")
        f.write(f"\nFinished {total_tasks} requests in {duration_minutes} minutes.\n")
        print(f"Total timeouts: {timeout_count}")
        f.write(f"Total timeouts: {timeout_count}\n")
       
        if times_token:
            avg_time_token = np.mean(times_token)
            median_time = np.median(times_token)
            min_time_token = min(times_token)
            max_time_token = max(times_token)
            print(f"Median time for the first token received: {median_time:.2f} sec")
            print(f"Minimum time for the first token received: {min_time_token:.2f} sec")
            print(f"Maximum time for the first token received: {max_time_token:.2f} sec")
            print(f"Average time for the first token received: {avg_time_token:.2f} sec")

            f.write(f"Median time for the first token received: {median_time:.2f} sec\n")
            f.write(f"Minimum time for the first token received: {min_time_token:.2f} sec\n")
            f.write(f"Maximum time for the first token received: {max_time_token:.2f} sec\n")
            f.write(f"Average time for the first token received: {avg_time_token:.2f} sec\n")

        if times_resp:
            avg_time_resp = np.mean(times_resp)
            median_time = np.median(times_resp)
            min_time_resp = min(times_resp)
            max_time_resp = max(times_resp)
            print(f"Median time for the response received: {median_time:.2f} sec")
            print(f"Minimum time for the response received: {min_time_resp:.2f} sec")
            print(f"Maximum time for the response received: {max_time_resp:.2f} sec")
            print(f"Average time for the response received: {avg_time_resp:.2f} sec")

            f.write(f"Median time for the response received: {median_time:.2f} sec\n")
            f.write(f"Minimum time for the response received: {min_time_resp:.2f} sec\n")
            f.write(f"Maximum time for the response received: {max_time_resp:.2f} sec\n")
            f.write(f"Average time for the response received: {avg_time_resp:.2f} sec\n")

if __name__ == "__main__":
    main()
