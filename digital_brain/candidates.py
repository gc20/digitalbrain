import bookmarks_parser
import re
import os

# [Internal] Parse chrome bookmarks
def __parse_chrome_bookmarks(candidates, bookmarks, path):
    if bookmarks['type'] == 'folder':
        if bookmarks['title'] != 'Bookmarks Bar':
            path += '{}/'.format(bookmarks['title'])
        for child in bookmarks.get('children', []):
            __parse_chrome_bookmarks(candidates, child, path)
    if bookmarks['type'] == 'bookmark':
        if not re.search(r'\.(pdf|jpeg|jpg|png)$', bookmarks['url'], flags=re.IGNORECASE) and not re.search(r'(google\.com\/search|\.google\.com\/spreadsheets)', bookmarks['url']):
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
    return candidates