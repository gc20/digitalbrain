import bookmarks_parser
import re
import os
import hashlib
import pathlib
import collections

# Add candidate ID
def add_candidateid(candidate):
    seed = candidate['type'] + candidate['type_id']
    candidate['id'] = hashlib.md5(seed.encode('utf-8')).hexdigest()
    candidate['idb'] = candidate['id'].encode(encoding='UTF-8')
    return candidate

# Parse Chrome bookmarks
def __parse_chrome_bookmarks(candidates, bookmarks, path):
    if bookmarks['type'] == 'folder':
        if bookmarks['title'] != 'Bookmarks Bar':
            path += '{}/'.format(bookmarks['title'])
        for child in bookmarks.get('children', []):
            __parse_chrome_bookmarks(candidates, child, path)
    if bookmarks['type'] == 'bookmark':
        if not re.search(r'\.(pdf|jpeg|jpg|png|js)$', bookmarks['url'], flags=re.IGNORECASE) and not re.search(r'(google\.com\/search|\.google\.com\/spreadsheets)', bookmarks['url']):
            candidates.append(add_candidateid({
                "type" : "url",
                "type_id" : bookmarks['url'],
                "path" : path,
                "title" : bookmarks["title"],
                "bdate" : bookmarks["add_date"]
            }))

# Parse local files
def __parse_local_files(candidates, folder_path, file_path):
    fileextension_stats = collections.defaultdict(int)
    for filename in pathlib.Path(file_path).rglob('*'):
        filename = filename.as_posix()
        extension = filename.split(".")[-1].lower()
        if extension in ["html", "txt", "docx", "md"]: # and "googledrive_backup" in file_path: # "pdf", "doc"
            candidates.append(add_candidateid({
                "type" : "file",
                "type_id" : filename,
                "extension" : extension,
                "path" : os.path.dirname(re.sub(r'^' + re.escape(folder_path) + r'[\/]*', '', filename)),
                "title" : os.path.split(filename)[-1]
            }))
        else:
            fileextension_stats[extension] += 1
    fileextension_stats = {k : v for k, v in fileextension_stats.items() if v > 1}
    print("Discarded: " + str(sorted(fileextension_stats.items(), key=lambda x: x[1], reverse=True)))

# Get seed candidates
def get_seed_candidates(input_path):
    candidates = []
    for seed_type in os.listdir(input_path):
        seed_folderpath = os.path.join(input_path, seed_type)
        for seed_filename in os.listdir(seed_folderpath):
            seed_filepath = os.path.join(seed_folderpath, seed_filename)
            if seed_type == "chrome_bookmarks":
                bookmarks = bookmarks_parser.parse(seed_filepath)
                __parse_chrome_bookmarks(candidates, bookmarks[0], "chrome_bookmarks/")
            elif seed_type == "local_files":
                __parse_local_files(candidates, seed_folderpath, seed_filepath)
    print("Detected {} candidates".format(len(candidates)))
    return candidates
