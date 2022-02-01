import hashlib
import json
import os
import pathlib
import re

def __prep_text(article):
    title = ""
    lines_old = article.split("\n")
    lines_new = []
    detected_break = False
    for line in lines_old:
        if re.search(r'^- Article Title: ', line):
            title = line.replace("- Article Title: ", "")
        if re.search(r'^-------', line):
            detected_break = True
        elif detected_break is True and line != "" and not re.search(r'^Auto-tags: ', line):
            lines_new.append(line)
    if title:
        lines_new.insert(0, title)
    article = " ".join(lines_new)
    article = ' '.join(article.split())
    return article[:9500], title

def get_candidate_entries(candidates, logs):
    entries = []
    for candidate in candidates:
        url_hash = hashlib.md5(candidate['url'].encode('utf-8')).hexdigest()
        filename = None
        try:
            filename = json.loads(logs["process"].Get(url_hash.encode(encoding='UTF-8')).decode())["file"]
        except Exception as e:
            pass
        if not filename or not os.path.exists(filename):
            continue
        article, title = __prep_text(pathlib.Path(filename).read_text())
        entries.append({
            "id" : url_hash,
            "url" : candidate['url'],
            "title" : title,
            "text" : article
        })
    print("Detected {} entries".format(len(entries)))
    return entries