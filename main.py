## Think
# - Quality challenges at scale (markdown + extraction)
# - Recos (tf-idf, better keyword n-grams, which keywords to tag?)
# - Other (URL metadata? images?)

## Sample commands
# python main.py --mode 'adhoc_crawl' --directory "/Users/Govind/Desktop/DB/" --adhoc_url "https://edition.cnn.com/2021/12/19/politics/joe-manchin-build-back-better/index.html"
# python main.py --mode 'adhoc_process' --directory "/Users/Govind/Desktop/DB/" --adhoc_url "https://edition.cnn.com/2021/12/19/politics/joe-manchin-build-back-better/index.html"

import argparse
import requests
import hashlib
import os
import validators
import leveldb
import time
import json
import newspaper # https://github.com/codelucas/newspaper
import nltk
import re
import pathlib
import bookmarks_parser
import tqdm
import random
import tldextract
# nltk.download('punkt')

# Arguments
parser = argparse.ArgumentParser(description='Command center')
parser.add_argument('--mode', help='Mode to run the program in', type=str, required=True, choices=['adhoc_crawl', 'adhoc_process', 'crawl_job', 'process_job'])
parser.add_argument('--directory', help='Working directory', type=str, required=True)
parser.add_argument('--adhoc_url', help='Adhoc URL to act on', type=str)
parser.add_argument('--crawl_override', dest='crawl_override', action='store_true')
parser.add_argument('--no-crawl_override', dest='crawl_override', action='store_false')
parser.set_defaults(crawl_override=False)
args = parser.parse_args()

# Crawl and store webpage
def crawl_store_url(url, html_path, crawl_log, crawl_override):

    # Basic checks
    if url is None or type(url) is not str or not validators.url(url):
        return 0, "URL is invalid"

    # Get URL location
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    url_path = os.path.join(html_path, url_hash + ".html")

    # Override check
    if crawl_override is False and os.path.exists(url_path):
        return 0, "URL html already exists for " + url_hash

    # Crawl
    response = requests.get(url)
    with open(url_path, "wb") as f:
        f.write(response.content)

    # Log
    crawl_log.Put(url_hash.encode(encoding='UTF-8'), json.dumps({"s" : response.status_code, "u" : url, "t" : int(time.time())}).encode(encoding='UTF-8'))
    # crawl_log.Get(url_hash.encode(encoding='UTF-8')).decode()

    return 1, "Written to " + url_hash

# Parse to markdown from HTML
def process_url(url, html_path, md_path, md_trail, process_log, url_metadata):

    # Get HTML
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    url_path = os.path.join(html_path, url_hash + ".html")
    if not os.path.exists(url_path):
        return 0, "HTML doesn't exist"
    html = None
    with open(url_path, "rb") as f:
        html = f.read()

    # Parse + process article
    article = newspaper.Article('')
    article.set_html(html)
    article.parse()
    article.nlp()

    # Title
    title = article.title or '<Untitled>'
    title = re.sub(r'[\\\/\:]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()

    # Create content markdown
    md_content = ''
    if article.text:
        md_content += article.text
        if article.keywords and len(article.keywords):
            keyword_select = "|".join([re.escape(str(k).lower()) for k in article.keywords])
            md_content = re.sub(r'\b(' + keyword_select + r')\b', r'[[\1]]', md_content, flags=re.IGNORECASE)

    # Create metadata markdown
    md_metadata = "- URL: " + url + "\n"
    if title:
        md_metadata += "- Article Title: " + title + "\n"
    if url_metadata.get('title'):
        md_metadata += "- Bookmark Title: " + url_metadata.get('title') + "\n"
    if article.authors and len(article.authors):
        md_metadata += "- Authors: " + ", ".join(article.authors) + "\n"
    if article.publish_date:
        md_metadata += "- Publish Date: " + article.publish_date.strftime("%m/%d/%Y") + "\n"
    if url_metadata.get('bdate'):
        md_metadata += "- Bookmarked Date: " + datetime.datetime.fromtimestamp(int(url_metadata.get('bdate'))).strftime("%m/%d/%Y")
    if article.keywords:
        md_metadata += "- Keywords: " + ", ".join(["[[" + k + "]]" for k in article.keywords]) + "\n"
    
    # Create summary markdown
    md_summary = article.summary

    # Final markdown
    md = "**Metadata**\n" + md_metadata + "\n"
    if md_summary:
        md += "**Summary**\n" + md_summary + "\n"
    if md_content:
        md += "**Content**\n" + md_content + "\n"

    # Chosen file
    md_filepath = md_path
    if len(md_trail):
        md_filepath = os.path.join(md_path, *md_trail)
    if not os.path.exists(md_filepath):
        pathlib.Path(md_filepath).mkdir(parents=True, exist_ok=True) 
    md_filename = os.path.join(md_filepath, url_metadata.get('path', ""), title + ".md")

    # Remove old file, write new file and store in process log
    url_hash_encoded = url_hash.encode(encoding='UTF-8')
    try:
        old_filename = json.loads(process_log.Get(url_hash_encoded).decode())['f']
        if os.path.exists(old_filename):
            os.remove(old_filename)
            process_log.Delete(url_hash_encoded)
            print("Removed:", old_filename)
    except Exception as e:
        print(str(e))
        pass

    # Write and store new file
    with open(md_filename, 'w') as f:
        print(md, file=f)
    process_log.Put(url_hash_encoded, json.dumps({"f" : md_filename, "u" : url, "t" : int(time.time())}).encode(encoding='UTF-8'))

    return 1, title + ".md was created"

# [Internal] Parse chrome bookmarks
def __parse_chrome_bookmarks(candidates, bookmarks, path):
    if bookmarks['type'] == 'folder':
        if bookmarks['title'] != 'Bookmarks Bar':
            path += '/{}'.format(bookmarks['title'])
        for child in bookmarks.get('children', []):
            __parse_chrome_bookmarks(candidates, child, path)
    if bookmarks['type'] == 'bookmark':
        candidates.append({"url" : bookmarks['url'], "path" : path, "title" : bookmarks["title"], "bdate" : bookmarks["add_date"]})

# Get seed candidates
def get_seed_candidates(input_path):
    candidates = []
    for seed_type in os.listdir(input_path):
        for seed_filename in os.listdir(os.path.join(input_path, seed_type)):
            seed_filepath = os.path.join(input_path, seed_type, seed_filename)
            if seed_type == "chrome_bookmarks":
                bookmarks = bookmarks_parser.parse(seed_filepath)
                __parse_chrome_bookmarks(candidates, bookmarks[0], "")
    print("Detected {} candidates".format(len(candidates)))
    random.shuffle(candidates)
    return candidates

# Run crawl job
def run_crawl_job(candidates, html_path, crawl_log, crawl_override):
    crawl_stats = {"total" : 0, "status" : {1: 0, 0: 0}}
    domain_stats = {}
    for candidate in tqdm.tqdm(candidates):

        # Stats/logs
        tldextract = tldextract.extract(candidate['url'])
        domain = tldextract.domain + "." + tldextract.suffix
        if domain not in domain_stats:
            domain_stats[domain] = {"total" : 0, "status" : {1: 0, 0: 0}}
        crawl_stats['total'] += 1
        domain_stats[domain]['total'] += 1
        print(candidate)
        if crawl_stats['total'] % 10 == 0:
            print(crawl_stats)
        status = 0

        # Crawl
        try:
            status, _ = crawl_store_url(candidate['url'], os.path.join(args.directory, "prod", "html"), crawl_log, crawl_override)
        except Exception as e:
            pass
        crawl_stats['status'][status] += 1
        domain_stats[domain]['status'][status] += 1
    crawl_stats['success_rate'] = "0%" if crawl_stats['total'] == 0 else "%.2f%" % (crawl_stats['stats'][1] / crawl_stats['total'])
    print(domain_stats)
    return 1, json.dumps(crawl_stats)


# Run process job

# Main file
if __name__ == "__main__":
    
    print("Mode:", args.mode)
    status, response = 0, "Nothing happened"
    if not os.path.exists(args.directory):
        status, response = 0, "Directory does not exist"
    crawl_log = leveldb.LevelDB(os.path.join(args.directory, "log", 'crawl_log.db'), create_if_missing=True)
    process_log = leveldb.LevelDB(os.path.join(args.directory, "log", 'process_log.db'), create_if_missing=True)

    try:

        if args.mode == 'adhoc_crawl':
            status, response = crawl_store_url(args.adhoc_url, os.path.join(args.directory, "prod", "html"), crawl_log, args.crawl_override)

        elif args.mode == 'adhoc_process':
            status, response = process_url(args.adhoc_url, os.path.join(args.directory, "prod", "html"), os.path.join(args.directory, "prod", "md"), [], process_log, {})

        elif args.mode == 'crawl_job':
            candidates = get_seed_candidates(os.path.join(args.directory, "input"))
            status, response = run_crawl_job(candidates, os.path.join(args.directory, "prod", "html"), crawl_log, args.crawl_override)
        elif args.mode == 'process_job':
            candidates = get_seed_candidates(os.path.join(args.directory, "input"))
            # status, response = process_url(args.url, os.path.join(args.directory, "prod", "html"), os.path.join(args.directory, "prod", "md"), [], process_log)

    except Exception as e:
        status, response = 0, str(e)

    print("Status:", status)
    print("Response:", response)
