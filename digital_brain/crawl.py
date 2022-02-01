import validators
import hashlib
import os
import json
import requests
import random
import tqdm
import tldextract
import time

# Crawl and store webpage
def crawl_url(candidate, html_path, logs, crawl_override):

    # Basic checks
    url = candidate['type_id']
    if url is None or type(url) is not str or not validators.url(url):
        return 0, "URL is invalid"

    # Get HTML location
    html_filename = os.path.join(html_path, candidate['id'] + ".html")

    # Pre-existing crawl check
    if crawl_override is False and os.path.exists(html_filename):
        try:
            previous_crawl = json.loads(logs["crawl"].Get(candidate['idb']).decode())
            if previous_crawl['status'] == 200:
                return 0, "HTML pre-exists"
        except Exception as e:
            pass

    # Crawl and log
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        with open(html_filename, "wb") as f:
            f.write(response.content)
    # else:
    #     if os.path.exists(html_filename):
    #         os.remove(html_filename)
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
def run_crawl_job(candidates, html_path, logs, crawl_override):

    crawl_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    random.shuffle(candidates)
    for candidate in tqdm.tqdm(candidates):

        # Stats 1
        crawl_stats['total'] += 1
        if crawl_stats['total'] % 10 == 0:
            print(crawl_stats)
        status, response = 0, ""

        # Crawl
        try:
            status, response = crawl_url(candidate, html_path, logs, crawl_override)
        except Exception as e:
            response = str(e)[0:50]

        # Stats 2
        crawl_stats['status'][status] += 1
        crawl_stats['response'][response] = 1 if response not in crawl_stats['response'] else crawl_stats['response'][response]+1
    
    crawl_stats['success_rate'] = "0%" if crawl_stats['total'] == 0 else "%.2f" % (crawl_stats['status'][1] / crawl_stats['total'])
    return 1, json.dumps(crawl_stats)
