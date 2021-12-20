import argparse
import requests
import hashlib
import os
import validators
import leveldb
import time
import json

# Arguments
parser = argparse.ArgumentParser(description='Command center')
parser.add_argument('--mode', help='Mode to run the program in', type=str, required=True, choices=['single_url'])
parser.add_argument('--directory', help='Working directory', type=str, required=True)
parser.add_argument('--inputfile', help='Input file to parse', type=str)
parser.add_argument('--url', help='URL to add', type=str)
args = parser.parse_args()

# Crawl and store webpage
def crawl_store_url(url, html_path, crawl_log, isoverride=False):

    # Basic checks
    if url is None or type(url) is not str or not validators.url(url):
        return 0, "URL is invalid"

    # Get URL location
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    url_path = os.path.join(html_path, url_hash + ".html")

    # Override check
    if isoverride is False and os.path.exists(url_path):
        return 0, "URL html already exists for " + url_hash

    # Crawl
    response = requests.get(url)
    with open(url_path, "wb") as f:
        f.write(response.content)

    # Log
    crawl_log.Put(url_hash.encode(encoding='UTF-8'), json.dumps({"u" : url, "t" : str(int(time.time()))}).encode(encoding='UTF-8'))
    # crawl_log.Get(url_hash.encode(encoding='UTF-8')).decode()

    return 1, "Written to " + url_hash

# Parse to markdown from HTML

# Parse input file

# Run crawling job

# Run parsing job

# Main file
print ("Here")
if __name__ == "__main__":
    
    print("Mode:", args.mode)
    status, response = None, None
    if not os.path.exists(args.directory):
        status, response = 0, "Directory does not exist"
    crawl_log = leveldb.LevelDB(os.path.join(args.directory, "log", 'crawl_log.db'), create_if_missing=True)

    try:

        if args.mode == 'single_url':
            status, response = crawl_store_url(args.url, os.path.join(args.directory, "prod", "html"), crawl_log, isoverride=True)

    except Exception as e:
        status, response = 0, str(e)

    print("Status:", status)
    print("Response:", response)
