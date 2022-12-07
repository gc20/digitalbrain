import validators
import hashlib
import os
import json
import requests
import random
import tqdm
import time
import pathlib
import mammoth
import markdown

# Crawl and store webpage
def crawl_url(candidate, html_path, logs, crawl_mode):

    # Basic checks
    url = candidate['type_id']
    if url is None or type(url) is not str or not validators.url(url):
        return 0, "URL is invalid"

    # Get HTML location
    html_filename = os.path.join(html_path, candidate['id'] + ".html")

    # Crawl mode compliance check
    if crawl_mode != "force":
        if os.path.exists(html_filename): # This line is redundant since we're checking logs, but it's there to take care of file/log mismatch
            try:
                previous_crawl = json.loads(logs["crawl"].Get(candidate['idb']).decode())
                if previous_crawl.get('status'):
                    if crawl_mode == "new":
                        return 1, "crawl_mode=new & crawl previously attempted"
                    elif crawl_mode == "retry" and previous_crawl['status'] == 200:
                        return 1, "crawl_mode=retry & successful crawl previously done"
            except Exception as e:
                pass

    # Crawl
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        with open(html_filename, "wb") as f:
            f.write(response.content)
    # else:
    #     if os.path.exists(html_filename):
    #         os.remove(html_filename)
 
    # Log
    log_entry = {k : candidate[k] for k in ["id", "type", "type_id"]}
    log_entry["status"] = response.status_code
    log_entry["time"] = int(time.time()) 
    logs["crawl"].Put(candidate['idb'], json.dumps(log_entry).encode(encoding='UTF-8'))
    # logs["crawl"].Get(candidate['idb']).decode()

    # Status & response
    if response.status_code != 200:
        return 0, "HTTP status {}".format(response.status_code)
    return 1, "Crawled!"


# Run crawl job
def run_crawl_job(candidates, html_path, logs, crawl_mode):

    crawl_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    random.shuffle(candidates)
    for candidate in tqdm.tqdm(candidates):

        if candidate['type'] != "url":
            continue

        # Crawl
        status, response = 0, ""
        try:
            status, response = crawl_url(candidate, html_path, logs, crawl_mode)
        except Exception as e:
            response = str(e)[0:200]

        # File
        elif candidate['type'] == "file":
            try:
                status, response = store_as_html(candidate, html_path, logs)
            except Exception as e:
                response = str(e)[0:200]

        # Stats
        crawl_stats['total'] += 1
        crawl_stats['status'][status] += 1
        crawl_stats['response'][response] = 1 if response not in crawl_stats['response'] else crawl_stats['response'][response]+1
        if crawl_stats['total'] % 10 == 0:
            print(crawl_stats)
    
    crawl_stats['success_rate'] = "0%" if crawl_stats['total'] == 0 else "%.2f" % (crawl_stats['status'][1] / crawl_stats['total'])
    print(crawl_stats)
    return 1, json.dumps(crawl_stats)
