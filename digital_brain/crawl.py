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
def crawl_url(url, html_path, logs, crawl_override):

    # Basic checks
    if url is None or type(url) is not str or not validators.url(url):
        return 0, "URL is invalid"

    # Get URL location
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    url_path = os.path.join(html_path, url_hash + ".html")

    # Pre-existing crawl check
    if crawl_override is False and os.path.exists(url_path):
        try:
            previous_crawl = json.loads(logs["crawl"].Get(url_hash.encode(encoding='UTF-8')).decode())
            if previous_crawl['s'] == 200:
                return 0, "HTML pre-exists"
        except Exception as e:
            pass

    # Crawl and log
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        with open(url_path, "wb") as f:
            f.write(response.content)
    # else:
    #     if os.path.exists(url_path):
    #         os.remove(url_path)
    logs["crawl"].Put(url_hash.encode(encoding='UTF-8'), json.dumps({"s" : response.status_code, "u" : url, "t" : int(time.time())}).encode(encoding='UTF-8'))
    # logs["crawl"].Get(url_hash.encode(encoding='UTF-8')).decode()

    # Status & response
    if response.status_code != 200:
        return 0, "HTTP status {}".format(response.status_code)
    return 1, "Crawled!"



# Run crawl job
def run_crawl_job(candidates, html_path, logs, crawl_override):

    crawl_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    domain_stats = {}
    random.shuffle(candidates)
    for candidate in tqdm.tqdm(candidates):

        # Stats 1
        tld_extract = tldextract.extract(candidate['url'])
        domain = tld_extract.domain + "." + tld_extract.suffix
        if domain not in domain_stats:
            domain_stats[domain] = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
        crawl_stats['total'] += 1
        domain_stats[domain]['total'] += 1
        print(candidate)
        if crawl_stats['total'] % 10 == 0:
            print(crawl_stats)
        if crawl_stats['total'] % 100 == 0:
            print(domain_stats, flush=True)
        status, response = 0, ""

        # Crawl
        try:
            status, response = crawl_url(candidate['url'], html_path, logs, crawl_override)
        except Exception as e:
            response = str(e)[0:50]

        # Stats 2
        crawl_stats['status'][status] += 1
        domain_stats[domain]['status'][status] += 1
        crawl_stats['response'][response] = 1 if response not in crawl_stats['response'] else crawl_stats['response'][response]+1
        domain_stats[domain]['response'][response] = 1 if response not in domain_stats[domain]['response'] else domain_stats[domain]['response'][response]+1
    
    crawl_stats['success_rate'] = "0%" if crawl_stats['total'] == 0 else "%.2f%" % (crawl_stats['status'][1] / crawl_stats['total'])
    print(domain_stats)
    return 1, json.dumps(crawl_stats)
