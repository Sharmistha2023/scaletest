import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
import numpy as np
from contextlib import redirect_stdout
import aiohttp
import click

headers = {
    'X-SLLM-Request-Id': '032adb4b-7837-4a5f-a027-b4820d386b0a',
    'x-dkubex-conversation-id': '966036d2-640e-47e3-b1ea-6a0c4380426c',
    'X-Auth-Request-Email': ''
}

@click.command()
@click.option('--no-of-streams', '-n', default=5, help='Number of parallel streams.')
@click.option('--questions-file', '-q', required=True, type=click.Path(exists=True),
              help='Path to the file containing questions.')
#@click.option('--no-of-question', '-nq', default=1, help='Number of questions.')
@click.option('--no-of-iteration', '-ni', default=1, help='Number of iteratins.')
def main(no_of_streams, questions_file, no_of_iteration):
    securechat_key = os.getenv("SECURECHAT_KEY", "allow")
    f = open(f"file_{no_of_streams}_{no_of_iteration}.txt", "w+")
    if not securechat_key:
        print("Export securechat application key as - export SECURECHAT_KEY=<application key>")
        sys.exit(1)

    with open(questions_file, 'r') as file:
        questions = [line.strip() for line in file if line.strip()]

    # if no_of_question < no_of_streams:
    #   no_of_question= no_of_streams
    total = int(no_of_streams * no_of_iteration)
    questions = questions * total
    questions = questions[:total]
    f.write(f"total questions: {questions} \n")
    f.write(".....................................................\n")
    
    print("total questions", len(questions))

    json_data = {
        'messages': [
            {
                'content': '',
                'role': 'user',
            },
        ],
        'key': securechat_key,
        'prompt': "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown.",
        'temperature': 0,
        'convForm': {

        },
        'user_name': '',
        'request_id': 'bf3557c9-eaaa-4c67-9983-493d0bf8b973',
        'model': {
            'id': 'meta/llama-3.2-3b-instruct',
            'value': 'meta/llama-3.2-3b-instruct',
            'name': 'meta/llama-3.2-3b-instruct',
            'maxLength': 4096,
            'tokenLimit': 4096,
        },
    }

 
    # with securellm
    url = "<url>/api/chat/"
    mylist = []
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_all(no_of_streams, questions, url, headers, json_data, f, mylist))
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
    f.close()
    count = 0
    file_path = f"file_{no_of_streams}_{no_of_iteration}.txt"
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
    
    # log_dir = "logs20"
    # os.makedirs(log_dir, exist_ok=True)
    # log_file_path = os.path.join(log_dir, f"{json_data['request_id']}.log")

    # with open(log_file_path, "w") as log_file, redirect_stdout(log_file):
    #     print(f"Send Q: {question} to url: {url}")
    #     headers['X-SLLM-Request-Id'] = str(uuid.uuid4())
    #     headers.update({"Authorization": f"Bearer {os.getenv('SECURECHAT_KEY')}"})

    #     try:
    #         response = await asyncio.wait_for(session.post(url, headers=headers, json=json_data, ssl=False), timeout=60)
    #         async with response:
    #             async for data in response.content.iter_any():
    #                 if first_token:
    #                     first_token = False
    #                     first_token_arrival = datetime.now()
    #                     diff = first_token_arrival - start_time
    #                     fetch_data.update({
    #                         "first_token_arrival": first_token_arrival.strftime("%Y-%m-%d %H:%M:%S"),
    #                         "first_token_latency": round(diff.total_seconds(), 2)
    #                     })
    #                 answer += data.decode("utf-8")

    #             end_time = datetime.now()
    #             fetch_data.update({
    #                 "answer": answer,
    #                 "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
    #                 "total_time": round((end_time - start_time).total_seconds(), 2)
    #             })

    #     except asyncio.TimeoutError:
    #         print(f"Request for question: {question} timed out after 120 seconds")
    #         fetch_data["timeout"] = True
    #         return fetch_data

    #     print(f"Received Response: {question} in {'{:.2f}'.format(fetch_data['total_time'])} sec")
    #     print(f"⏱️ Request Sent At      : {fetch_data['start_time']}")
    #     print(f"🕒 First Token At       : {fetch_data.get('first_token_arrival', 'N/A')}")
    #     print(f"⚡ First Token Latency  : {fetch_data.get('first_token_latency', 'N/A')} sec")
    #     print(f"⏳ Total Response Time  : {fetch_data['total_time']} sec")

    # return fetch_data


   

    
    

    print(f"Send Q: {question} to url: {url}")
    f.write(f"Send Q: {question} to url: {url} \n")
    headers['X-SLLM-Request-Id'] = str(uuid.uuid4())
    headers.update({"Authorization" : f"Bearer {os.getenv('SECURECHAT_KEY')}"})
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

    # 🆕 Additional prints
    
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


async def fetch_all(no_of_streams, questions, url, headers, json_data, f, mylist):
    semaphore = asyncio.Semaphore(no_of_streams)

    times_token = []
    times_resp = []
    timeout_count = 0
    async with aiohttp.ClientSession(trust_env=True) as session:
        tasks = [fetch_with_semaphore(semaphore, session, url, headers, json_data, question, f, mylist) for question in questions]
        start_time = datetime.now()
        responses = await asyncio.gather(*tasks)
        end_time = datetime.now()
        total_time = end_time - start_time
        print(f"Total time taken = {'{:.2f}'.format(total_time.total_seconds())} sec")

        for fetch_data in responses:
            if 'timeout' in fetch_data:
                timeout_count += 1
            elif 'total_time' in fetch_data:
                times_token.append(fetch_data.get('first_token_latency'))
                times_resp.append(fetch_data.get('total_time'))

        print(f"Total timeouts: {timeout_count}")

        if times_token:
            avg_time_token = np.mean(times_token)
            median_time = np.median(times_token)
            min_time_token = min(times_token)
            max_time_token = max(times_token)
            print(f"Median time for the first token received: {'{:.2f}'.format(median_time)} sec")
            print(f"Minimum time for the first token received: {'{:.2f}'.format(min_time_token)} sec")
            print(f"Maximum time for the first token received: {'{:.2f}'.format(max_time_token)} sec")
            print(f"Average time for the first token received: {'{:.2f}'.format(avg_time_token)} sec")
            
            f.write(f"Median time for the first token received: {'{:.2f}'.format(median_time)} sec \n")
            f.write(f"Minimum time for the first token received: {'{:.2f}'.format(min_time_token)} sec \n")
            f.write(f"Maximum time for the first token received: {'{:.2f}'.format(max_time_token)} sec \n")
            f.write(f"Average time for the first token received: {'{:.2f}'.format(avg_time_token)} sec \n")

        if times_resp:
            avg_time_resp = np.mean(times_resp)
            median_time = np.median(times_resp)
            min_time_resp = min(times_resp)
            max_time_resp = max(times_resp)
            print(f"Median time for the response received: {'{:.2f}'.format(median_time)} sec")
            print(f"Minimum time for the response received: {'{:.2f}'.format(min_time_resp)} sec")
            print(f"Maximum time for the response received: {'{:.2f}'.format(max_time_resp)} sec")
            print(f"Average time for the response received: {'{:.2f}'.format(avg_time_resp)} sec")

            f.write(f"Median time for the response received: {'{:.2f}'.format(median_time)} sec \n")
            f.write(f"Minimum time for the response received: {'{:.2f}'.format(min_time_resp)} sec \n")
            f.write(f"Maximum time for the response received: {'{:.2f}'.format(max_time_resp)} sec \n")
            f.write(f"Average time for the response received: {'{:.2f}'.format(avg_time_resp)} sec \n")

async def fetch_with_semaphore(semaphore, session, url, headers, json_data, question, f, mylist):
    async with semaphore:
        return await fetch(session, url, headers, json_data, question, f, mylist)


if __name__ == "__main__":
    main()
