import collections
import tqdm
import json
import pathlib
import re
import markdown
import bs4
import yake
import spacy


# NLP
spacy_nlp = spacy.load("en_core_web_lg") # python -m spacy download en_core_web_lg
yake_nlp = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=10, features=None)

# Process tags
def __process_tag(tag):
    tag = re.sub(r'[\s\,\&\\\/\[\]\(\)\.\+\'\"\’]', '-', tag)
    tag = re.sub(r'[\-]+', '-', tag)
    tag = "#" + tag.strip("-")
    status = True if len(tag) >= 3 else False
    return tag, status

# Convert markdown to text
def __markdown_to_text(md):
    # md -> html -> text since BeautifulSoup can extract text cleanly
    html = markdown.markdown(md)
    # remove code snippets
    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)
    # extract text
    soup = bs4.BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))
    return text

# Extract tags from markdown
def tag_markdown(candidate, md_path, permitted_tags, logs):

    # Get md
    md_filename, md = None, None
    try:
        md_filename = json.loads(logs["process"].Get(candidate['idb']).decode())["file"]
        md = pathlib.Path(md_filename).read_text()
    except Exception as e:
        return 0, "Could not extract md"
    if len(md) < 5:
        return 0, "md not meaningful enough"

    # Clean out existing tags
    md_lines = md.strip("\n").split("\n")
    # md_lines = [line for line in md_lines if not re.search(r'^Auto-tags:', line)]
    if re.search(r'^Auto-tags:', md_lines[-1]):
        _ = md_lines.pop()
    md = "\n".join(md_lines)

    # Get tags (spacy)
    text_content = __markdown_to_text(md)
    spacy_doc = spacy_nlp(text_content)
    spacy_tags_raw = collections.defaultdict(int)
    for e in spacy_doc.ents:
        if e.label_ not in set(['DATE', 'PERCENT', 'CARDINAL', 'MONEY', 'TIME', 'ORDINAL']):
            if not re.search(r'\s\s', e.text):
                tag, tag_status = __process_tag(e.text)
                if tag_status:
                    spacy_tags_raw[tag] += 1
    spacy_tags = [tag for tag, _ in sorted(spacy_tags_raw.items(), key=lambda x: x[1], reverse=True) if permitted_tags is None or tag in permitted_tags]

    # Get tags (yake)
    yake_tags_result = yake_nlp.extract_keywords(text_content)
    yake_tags_raw = {}
    for entry in yake_tags_result:
        if entry[1] < 0.2:
            tag, tag_status = __process_tag(entry[0])
            if tag_status:
                yake_tags_raw[tag] = entry[1]
    yake_tags = [tag for tag, tag_score in sorted(yake_tags_raw.items(), key=lambda x: x[1], reverse=True) if tag_score < 0.2 and tag not in spacy_tags_raw and (permitted_tags is None or tag in permitted_tags)]

    # # Get tags (links)
    # links_tags_raw = collections.Counter(re.findall(r'\[(.*?)\]', md))
    # links_tags_raw += collections.Counter(re.findall(r'\*\*(.*?)\*\*', md))

    # Add tags
    auto_tags = spacy_tags + yake_tags
    if len(auto_tags):
        if md_lines[-1] != "":
            md_lines.append("")
        md_lines.append("Auto-tags: " + ", ".join(list(auto_tags)))
    md_new = "\n".join(md_lines)
    response = "Auto-tags are the same"
    if md != md_new:
        with open(md_filename, 'w') as f:
            print(md_new, file=f)
        response = "Auto-tags have changed"

    # Log tags
    log_entry = {k : candidate[k] for k in ["id", "type", "type_id"]}
    log_entry["spacy_tags"] = spacy_tags_raw
    log_entry["yake_tags"] = yake_tags_raw
    logs["tags"].Put(candidate['idb'], json.dumps(log_entry).encode(encoding='UTF-8'))
    print(json.dumps(log_entry), file=logs["tags_stream"])

    return 1, response


# Run tag job
def run_tag_job(candidates, md_path, logs):
    tag_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        status, response = 0, ""
        try:
            tag_stats['total'] += 1
            status, response = tag_markdown(candidate, md_path, None, logs)
        except Exception as e:
            response = str(e)[0:50]
        tag_stats['status'][status] += 1
        tag_stats['response'][response] = 1 if response not in tag_stats['response'] else tag_stats['response'][response]+1
        if tag_stats['total'] % 100 == 0:
            print(tag_stats)
    return 1, json.dumps(tag_stats)
