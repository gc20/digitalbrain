## PLAN
# 1] Summarization
#   - Summarize (abstract + executive?)
#   - Deep tagging turn-on, only across summary?
#   - GPT-3 API?
# 2] Keywords
#   - Split by keyword group (cycles?)
#   - Cross-document (only keep top?)
#   - Dedup tags (within doc maps?)
#   - Precision/recall (Yake?)
# 3] Linking
#   - Semantic similarity between notes
#   - Semantic similarity between paragraphs
#   - Chronological linking between pages
# 4] More Data
#   - Chrome history (parse)
#   - Kindle highlights
#   - Twitter history (by hashtag?, pull related actions)
# 5] Chrome Extension
#   - Show recommendations while browsing ("link to my vault" -> similarity + keywords)
# 6] Later
#   - Misc (images/PDF, language, summarization, failures, domain removal)

## Sample commands
# python main.py --workflow 'adhoc_crawl' --directory "/Users/Govind/Desktop/DB/" --mode="dev" --adhoc_url "https://edition.cnn.com/2021/12/19/politics/joe-manchin-build-back-better/index.html"
# python main.py --workflow 'adhoc_process' --directory "/Users/Govind/Desktop/DB/" --mode="dev" --adhoc_url "https://edition.cnn.com/2021/12/19/politics/joe-manchin-build-back-better/index.html"
# python main.py --workflow 'crawl_job' --directory "/Users/Govind/Desktop/DB/"
# python main.py --workflow 'process_job' --directory "/Users/Govind/Desktop/DB/"

import argparse
import requests
import hashlib
import os
import validators
import leveldb # consider plyvel
import time
import json
import collections
import re
import pathlib
import bookmarks_parser
import tqdm
import random
import tldextract
import datetime
import spacy
import readability
import newspaper # https://github.com/codelucas/newspaper
import bs4
import urllib
import markdownify
# import nltk
import yake

# NLP
# python -m spacy download en_core_web_sm
spacy_nlp = spacy.load("en_core_web_lg")
# nltk.download('punkt')
yake_nlp = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=10, features=None)

# Arguments
parser = argparse.ArgumentParser(description='Command center')
parser.add_argument('--workflow', help='Workflow to run', type=str, required=True, choices=['adhoc_crawl', 'adhoc_process', 'crawl_job', 'process_job'])
parser.add_argument('--directory', help='Working directory', type=str, required=True)
parser.add_argument('--mode', help='Mode to apply', type=str, default='prod', choices=['dev', 'prod'])
parser.add_argument('--adhoc_url', help='Adhoc URL to act on', type=str)
parser.add_argument('--crawl_override', dest='crawl_override', action='store_true')
parser.add_argument('--no-crawl_override', dest='crawl_override', action='store_false')
parser.set_defaults(crawl_override=False)
args = parser.parse_args()

# Crawl and store webpage
def crawl_store_url(url, html_path, logs, crawl_override):

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

# Process keywords
def __process_keyword(keyword):
    keyword = re.sub(r'[\s\,\&\\\/\[\]\(\)\.\+\'\"\’]', '-', keyword)
    keyword = re.sub(r'[\-]+', '-', keyword)
    keyword = "#" + keyword.strip("-")
    status = True if len(keyword) >= 3 else False
    return keyword, status

# Parse to markdown from HTML
def process_url(candidate, html_path, md_path, logs):

    # Get HTML
    url = candidate['url']
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    url_path = os.path.join(html_path, url_hash + ".html")
    if not os.path.exists(url_path): # swap with DB check?
        return 0, "HTML doesn't exist"
    html = None
    with open(url_path, "rb") as f:
        html = f.read()

    # Populate relative links
    soup = bs4.BeautifulSoup(html, features="lxml")
    for a in soup.findAll('a'):
        if a.get('href'):
            a['href'] = urllib.parse.urljoin(url, a['href'])
    for img_tag in ['img', 'image']:
        for i in soup.findAll(img_tag):
            if i.get('src'):
                i['src'] = urllib.parse.urljoin(url, i['src'])
    html = str(soup)

    # Get HTML
    readability_article = readability.Document(html)
    title = readability_article.title()
    html_content = readability_article.summary()

    # Get markdown
    md_content = markdownify.markdownify(html_content)
    if not title or not html_content or not md_content:
        return 0, "Could not extract meaningful content"
    md_content = re.sub(r'[\#]+', ' ', md_content)
    md_content = re.sub(r'[\[]+', r'[', md_content)
    md_content = re.sub(r'[\]]+', r']', md_content)

    # Get text
    newspaper_article = newspaper.Article('')
    newspaper_article.set_html(html_content)
    newspaper_article.parse()
    text_content = newspaper_article.text
    # soup = bs4.BeautifulSoup(html_content, features="lxml")
    # text_content = soup.get_text('\n')
    if len(text_content) < 280:
        return 0, "Text <280 chars"

    # Get keywords (spacy)
    spacy_doc = spacy_nlp(text_content)
    spacy_keywords_raw = collections.defaultdict(int)
    # entity_marks = []
    for e in spacy_doc.ents:
        if e.label_ not in set(['DATE', 'PERCENT', 'CARDINAL', 'MONEY', 'TIME', 'ORDINAL']):
            if not re.search(r'\s\s', e.text):
                keyword, keyword_status = __process_keyword(e.text)
                if keyword_status:
                    spacy_keywords_raw[keyword] += 1
                    # entity_marks.append((e.start_char, e.end_char))
    # spacy_keywords = [keyword for keyword, _ in sorted(spacy_keywords_raw.items(), key=lambda x: x[1], reverse=True)]

    # Get keywords (yake)
    yake_keywords_result = yake_nlp.extract_keywords(text_content)
    yake_keywords_raw = {}
    for entry in yake_keywords_result:
        if entry[1] < 0.2:
            keyword, keyword_status = __process_keyword(entry[0])
            if keyword_status:
                yake_keywords_raw[keyword] = entry[1]
    # yake_keywords = [keyword for keyword, keyword_score in sorted(yake_keywords_raw.items(), key=lambda x: x[1], reverse=True) if keyword_score < 0.2]

    # Title
    title = re.sub(r'[\\\/\:]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()

    # Tag content
    # for entity_mark in reversed(entity_marks):
    #     md_content = md_content[:entity_mark[0]] + "[[" + md_content[entity_mark[0]:entity_mark[1]] + "]]" + md_content[entity_mark[1]:]
    # if keywords and len(keywords):
    #     keyword_select = "|".join([re.escape(str(k).lower()) for k in keywords])
    #     md_content = re.sub(r'\b(' + keyword_select + r')\b', r'[[\1]]', md_content, flags=re.IGNORECASE)

    # Create metadata markdown
    md_metadata = "- URL: " + url + "\n"
    if title:
        md_metadata += "- Article Title: " + title + "\n"
    if candidate.get('title') and candidate.get('title') != title:
        md_metadata += "- Bookmark Title: " + candidate.get('title') + "\n"
    if newspaper_article.authors and len(newspaper_article.authors):
        md_metadata += "- Authors: " + ", ".join(newspaper_article.authors) + "\n"
    if newspaper_article.publish_date:
        md_metadata += "- Publish Date: " + newspaper_article.publish_date.strftime("%m/%d/%Y") + "\n"
    if candidate.get('bdate'):
        md_metadata += "- Bookmarked Date: " + datetime.datetime.fromtimestamp(int(candidate.get('bdate'))).strftime("%m/%d/%Y") + "\n"

    # Final markdown
    md = "**About**\n" + md_metadata + "\n"
    md += "-----------------------------\n" + md_content + "\n\n"

    # Chosen file
    md_filepath = md_path
    if candidate.get('path', ""):
        md_filepath = os.path.join(md_path, candidate.get('path', ""))
    if not os.path.exists(md_filepath):
        pathlib.Path(md_filepath).mkdir(parents=True, exist_ok=True) 
    md_filename = os.path.join(md_filepath, title + ".md")

    # Remove old file, write new file and store in process log
    url_hash_encoded = url_hash.encode(encoding='UTF-8')
    try:
        old_filename = json.loads(logs["process"].Get(url_hash_encoded).decode())['f']
        if os.path.exists(old_filename):
            os.remove(old_filename)
            logs["process"].Delete(url_hash_encoded)
            print("Removed:", old_filename)
    except Exception as e:
        print(str(e))
        pass

    # Write and store new file
    with open(md_filename, 'w') as f:
        print(md, file=f)
    logs["process"].Put(url_hash_encoded, json.dumps({"f" : md_filename, "u" : url, "t" : int(time.time())}).encode(encoding='UTF-8'))

    # Store tags
    keywords = {"s" : spacy_keywords_raw, "y" : yake_keywords_raw}
    logs["tags"].Put(url_hash_encoded, json.dumps(keywords).encode(encoding='UTF-8'))
    print(json.dumps(keywords), file=logs["tags_stream"])

    return 1, ".md was created"

# [Internal] Parse chrome bookmarks
def __parse_chrome_bookmarks(candidates, bookmarks, path):
    if bookmarks['type'] == 'folder':
        if bookmarks['title'] != 'Bookmarks Bar':
            path += '{}/'.format(bookmarks['title'])
        for child in bookmarks.get('children', []):
            __parse_chrome_bookmarks(candidates, child, path)
    if bookmarks['type'] == 'bookmark':
        if not re.search(r'\.(pdf|jpeg|jpg|png)$', bookmarks['url'], flags=re.IGNORECASE) and not re.search(r'(google\.com\/search|docs\.google\.com\/spreadsheets)', bookmarks['url']):
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
def run_crawl_job(candidates, html_path, logs, crawl_override):
    crawl_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    domain_stats = {}
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
            status, response = crawl_store_url(candidate['url'], html_path, logs, crawl_override)
        except Exception as e:
            response = str(e)[0:50]

        # Stats 2
        crawl_stats['status'][status] += 1
        domain_stats[domain]['status'][status] += 1
        crawl_stats['response'][response] = 1 if response not in crawl_stats['response'] else crawl_stats['response'][response]+1
        domain_stats[domain]['response'][response] = 1 if response not in domain_stats[domain]['response'] else domain_stats[domain]['response'][response]+1
    
    crawl_stats['success_rate'] = "0%" if crawl_stats['total'] == 0 else "%.2f%" % (crawl_stats['stats'][1] / crawl_stats['total'])
    print(domain_stats)
    return 1, json.dumps(crawl_stats)


# Run process job
def run_process_job(candidates, html_path, md_path, logs):
    process_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        status, response = 0, ""
        try:
            process_stats['total'] += 1
            status, response = process_url(candidate, html_path, md_path, logs)
        except Exception as e:
            response = str(e)[0:50]
        process_stats['status'][status] += 1
        process_stats['response'][response] = 1 if response not in process_stats['response'] else process_stats['response'][response]+1
        if process_stats['total'] % 100 == 0:
            print(process_stats)
    return 1, json.dumps(process_stats)


# Main file
if __name__ == "__main__":
    
    print("Workflow:", args.workflow)
    print("Mode:", args.mode)
    status, response = 0, "Nothing happened"
    if not os.path.exists(args.directory):
        status, response = 0, "Directory does not exist"
    working_directory = os.path.join(args.directory, args.mode)

    # Setup logs
    crawl_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'crawl_status.db'), create_if_missing=True)
    process_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'process_status.db'), create_if_missing=True)
    tags_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'tags_status.db'), create_if_missing=True)
    tags_stream = open(os.path.join(working_directory, "log", 'tags_stream.json'), "w")
    logs = {"crawl" : crawl_status, "process" : process_status, "tags" : tags_status, "tags_stream" : tags_stream}

    try:

        if args.workflow == 'adhoc_crawl':
            status, response = crawl_store_url(args.adhoc_url, os.path.join(working_directory, "html"), logs, args.crawl_override)

        elif args.workflow == 'adhoc_process':
            status, response = process_url({"url" : args.adhoc_url}, os.path.join(working_directory, "html"), os.path.join(working_directory, "md"), logs)

        elif args.workflow == 'crawl_job':
            candidates = get_seed_candidates(os.path.join(working_directory, "input"))
            status, response = run_crawl_job(candidates, os.path.join(working_directory, "html"), logs, args.crawl_override)
        elif args.workflow == 'process_job':
            candidates = get_seed_candidates(os.path.join(working_directory, "input"))
            status, response = run_process_job(candidates, os.path.join(working_directory, "html"), os.path.join(working_directory, "md"), logs)

    except Exception as e:
        status, response = 0, str(e)

    print("Status:", status)
    print("Response:", response)
