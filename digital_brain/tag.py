import collections
import tqdm
import hashlib
import json
import pathlib
import re

# Run tag job
def run_tag_job(candidates, html_path, md_path, logs):

    # Get top tags
    tags_all = collections.defaultdict(int)
    for candidate in tqdm.tqdm(candidates):
        try:
            url_hash = hashlib.md5(candidate['url'].encode('utf-8')).hexdigest()
            tag_entry = json.loads(logs["tags"].Get(url_hash.encode(encoding='UTF-8')).decode())
            tags_local = set()
            for tag_type in ["s", "y"]:
                for tag in tag_entry[tag_type]:
                    tags_local.add(tag)
            for tag in tags_local:
                tags_all[tag] += 1
        except Exception as e:
            pass
    tags_permitted = set()
    for tag, _ in sorted(tags_all.items(), key=lambda x: x[1], reverse=True)[:100]:
        tags_permitted.add(tag)
    print(sorted(tags_permitted))
    
    # Tag candidates
    tag_stats = {"total" : 0, "tagged" : 0, "status" : {1: 0, 0: 0}}
    for candidate in tqdm.tqdm(candidates):
        status = 0
        try:

            # Get chosen tags
            tag_stats['total'] += 1
            url_hash = hashlib.md5(candidate['url'].encode('utf-8')).hexdigest()
            tag_entry = json.loads(logs["tags"].Get(url_hash.encode(encoding='UTF-8')).decode())
            tags_chosen = set()
            for tag_type in ["s", "y"]:
                for tag in tag_entry[tag_type]:
                    if tag in tags_permitted:
                        tags_chosen.add(tag)

            # Edit markdown
            md_filename = json.loads(logs["process"].Get(url_hash.encode(encoding='UTF-8')).decode())["f"]
            md = pathlib.Path(md_filename).read_text()
            md_lines = md.split("\n")
            md_lines = [line for line in md_lines if not re.search(r'^Auto-tags:', line)]
            while len(md_lines) and md_lines[-1] == "":
                _ = md_lines.pop()
            if re.search(r'^Auto-tags:', md_lines[-1]):
                _ = md_lines.pop()
            if len(tags_chosen):
                md_lines.append("")
                md_lines.append("Auto-tags: " + ", ".join(list(tags_chosen)))
                tag_stats["tagged"] += 1
            md_new = "\n".join(md_lines)
            if md != md_new:
                with open(md_filename, 'w') as f:
                    print(md_new, file=f)
            status = 1

        except Exception as e:
            pass
        
        tag_stats["status"][status] += 1

    return 1, json.dumps(tag_stats)
