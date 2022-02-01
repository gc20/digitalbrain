import hashlib
import os
import bs4
import urllib
import markdownify
# import nltk
import yake
import spacy
import readability
import newspaper # https://github.com/codelucas/newspaper
import re
import tqdm
import collections
import json
import pathlib
import datetime
import time

# NLP
# python -m spacy download en_core_web_lg
spacy_nlp = spacy.load("en_core_web_lg")
# nltk.download('punkt')
yake_nlp = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=10, features=None)

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

    # Title
    title = re.sub(r'[\\\/\:]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()

    # Get text
    newspaper_article = newspaper.Article('')
    newspaper_article.set_html(html_content)
    newspaper_article.parse()
    text_content = newspaper_article.text
    # soup = bs4.BeautifulSoup(html_content, features="lxml")
    # text_content = soup.get_text('\n')
    if len(text_content) < 280:
        return 0, "Text <280 chars"

    # Get keywords (links)
    links_keywords_raw = collections.Counter(re.findall(r'\[(.*?)\]', md_content))
    links_keywords_raw += collections.Counter(re.findall(r'\*\*(.*?)\*\*', md_content))

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
    keywords = {"s" : spacy_keywords_raw, "y" : yake_keywords_raw, "l" : links_keywords_raw}
    logs["tags"].Put(url_hash_encoded, json.dumps(keywords).encode(encoding='UTF-8'))
    print(json.dumps(keywords), file=logs["tags_stream"])

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
