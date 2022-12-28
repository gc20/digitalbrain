import re
import os
import hashlib
import pathlib
import collections
import json

# Add candidate ID
def add_candidateid(candidate):
    seed = candidate['type'] + candidate['type_id']
    candidate['id'] = hashlib.md5(seed.encode('utf-8')).hexdigest()
    candidate['idb'] = candidate['id'].encode(encoding='UTF-8')
    return candidate


# Get seed candidates
def get_seed_candidates(input_path):
    candidates = []
    fileextension_stats = collections.defaultdict(int)
    for seed_type in os.listdir(input_path):
        seed_folderpath = os.path.join(input_path, seed_type)
        for filename in pathlib.Path(seed_folderpath).rglob('*'):
            filename = filename.as_posix()
            extension = filename.split(".")[-1].lower()
            fileextension_stats[extension] += 1
            if extension in ["html", "txt", "docx", "md", "pdf"]: # "doc"
                candidates.append(add_candidateid({
                    "type" : "file",
                    "type_id" : filename,
                    "path" : os.path.dirname(re.sub(r'^' + re.escape(input_path) + r'[\/]*', '', filename)),
                    "title" : os.path.split(filename)[-1],
                    "extension" : extension
                }))
            elif extension in ["urls"]:
                candidates_urls = json.load(open(filename))
                for candidate in candidates_urls:
                    candidate['type'] = 'url'
                    candidates.append(add_candidateid(candidate))
    fileextension_stats = {k : v for k, v in fileextension_stats.items() if v > 1}
    print("File stats: " + str(sorted(fileextension_stats.items(), key=lambda x: x[1], reverse=True)))
    print("Detected {} candidates".format(len(candidates)))
    return candidates
