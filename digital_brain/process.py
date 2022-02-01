import hashlib
import os
import bs4
import urllib
import markdownify
import readability
import re
import tqdm
import collections
import json
import pathlib
import time

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

    # Prepare title
    title = re.sub(r'[\\\/\:]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()
    if not title or len(title) < 5:
        title = candidate.get('title')
        if not title or len(title) < 5:
            return 0, "Could not extract meaningful title"

    # Get markdown
    md_content = markdownify.markdownify(html_content)
    if not title or not html_content or not md_content:
        return 0, "Could not extract meaningful content"
    md_content = re.sub(r'[\#]+', ' ', md_content)
    md_content = re.sub(r'[\[]+', r'[', md_content)
    md_content = re.sub(r'[\]]+', r']', md_content)
    if len(md_content) < 280:
        return 0, "Text <280 chars"
    md_content = re.sub(r'\n\n[\n]+', r'\n\n', md_content)
    md_content = '[' + title + ']' + '(' + url + ')' + "\n\n" + md_content

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
        print(md_content, file=f)
    logs["process"].Put(url_hash_encoded, json.dumps({"f" : md_filename, "u" : url, "t" : int(time.time())}).encode(encoding='UTF-8'))

    return 1, ".md was created"


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
