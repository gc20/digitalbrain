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
def process_html(candidate, html_path, md_path, logs):

    # Get HTML
    html_filename = os.path.join(html_path, candidate['id'] + ".html")
    if not os.path.exists(html_filename): # swap with DB check?
        return 0, "HTML doesn't exist"
    html = None
    with open(html_filename, "rb") as f:
        html = f.read()

    # Populate relative links
    soup = bs4.BeautifulSoup(html, features="lxml")
    if candidate['type'] == 'url':
        for a in soup.findAll('a'):
            if a.get('href'):
                a['href'] = urllib.parse.urljoin(candidate['type_id'], a['href'])
        for img_tag in ['img', 'image']:
            for i in soup.findAll(img_tag):
                if i.get('src'):
                    i['src'] = urllib.parse.urljoin(candidate['type_id'], i['src'])
    html = str(soup)

    # Get HTML
    readability_article = readability.Document(html)
    html_content = readability_article.summary()

    # Prepare title
    title = candidate.get('title')
    if not title or len(title) < 5:
        title = readability_article.title()
        title = re.sub(r'[\\\/\:]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        title = title.strip()
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
    if candidate['type'] == "url":
        md_content = '[' + title + ']' + '(' + candidate['type_id'] + ')' + "\n\n" + md_content
    else:
        md_content = title + "\n\n" + md_content

    # Chosen file
    md_filepath = md_path
    if candidate.get('path', ""):
        md_filepath = os.path.join(md_path, candidate.get('path', ""))
    if not os.path.exists(md_filepath):
        pathlib.Path(md_filepath).mkdir(parents=True, exist_ok=True) 
    md_filename = os.path.join(md_filepath, title + ".md")

    # Remove old file, write new file and store in process log
    try:
        old_filename = json.loads(logs["process"].Get(candidate['idb']).decode())['file']
        if os.path.exists(old_filename):
            os.remove(old_filename)
            logs["process"].Delete(candidate['idb'])
            print("Removed:", old_filename)
    except Exception as e:
        print(str(e))
        pass

    # Write and store new file
    with open(md_filename, 'w') as f:
        print(md_content, file=f)
    log_entry = {k : candidate[k] for k in ["id", "type", "type_id"]}
    log_entry["file"] = md_filename
    log_entry["time"] = int(time.time()) 
    logs["process"].Put(candidate['idb'], json.dumps(log_entry).encode(encoding='UTF-8'))

    return 1, ".md was created"


# Run process job
def run_process_job(candidates, html_path, md_path, logs):
    process_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        status, response = 0, ""
        try:
            process_stats['total'] += 1
            status, response = process_html(candidate, html_path, md_path, logs)
        except Exception as e:
            response = str(e)[0:50]
        process_stats['status'][status] += 1
        process_stats['response'][response] = 1 if response not in process_stats['response'] else process_stats['response'][response]+1
        if process_stats['total'] % 100 == 0:
            print(process_stats)
    return 1, json.dumps(process_stats)
