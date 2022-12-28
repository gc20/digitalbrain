import bookmarks_parser
import re
import os
import json
import sys
sys.path.append("../")

def __parse_chrome_bookmarks(candidates, bookmarks, path):
    if bookmarks['type'] == 'folder':
        if bookmarks['title'] != 'Bookmarks Bar':
            path += '{}/'.format(bookmarks['title'])
        for child in bookmarks.get('children', []):
            __parse_chrome_bookmarks(candidates, child, path)
    if bookmarks['type'] == 'bookmark':
        if not re.search(r'\.(pdf|jpeg|jpg|png|js)$', bookmarks['url'], flags=re.IGNORECASE) and not re.search(r'(google\.com\/search|\.google\.com\/spreadsheets)', bookmarks['url']):
            candidates.append({
                "type_id" : bookmarks['url'],
                "path" : path,
                "title" : bookmarks["title"],
                "date" : bookmarks["add_date"]
            })

if __name__ == "__main__":
    
    input_folder = '/Users/Govind/Desktop/DB/Data/chrome_bookmarks'
    processed_folder = "/Users/Govind/Desktop/DB/code/v1-digitalbrain/prod_work/input/chrome_bookmarks/" 

    candidates = []
    for seed_filename in os.listdir(input_folder):
        seed_filepath = os.path.join(input_folder, seed_filename)
        bookmarks = bookmarks_parser.parse(seed_filepath)
        __parse_chrome_bookmarks(candidates, bookmarks[0], "chrome_bookmarks/")
        with open(processed_folder + re.sub(r'\.html', '.urls', seed_filename), "w") as f:
            print(json.dumps(candidates), file=f) 
