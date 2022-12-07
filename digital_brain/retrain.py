import json
from digital_brain import helper as db_helper
import tqdm
import os
import pathlib
import re

# Get candidate text from markdowns
def get_candidate_text(candidate, md_path, logs):

    # Get md
    md_filename, md = None, None
    try:
        md_filename = json.loads(logs["process"].Get(candidate['idb']).decode())["file"]
        md = pathlib.Path(md_filename).read_text()
    except Exception as e:
        return 0, "Could not extract md"
    if len(md) < 5:
        return 0, "md not meaningful enough"

    # Clean out existing auto-*
    md_lines = md.strip("\n").split("\n")
    md_lines = [line for line in md_lines if not re.search(r'^Auto-(\w+):', line)]
    md = "\n".join(md_lines)

    # Convert to text and embed
    text_content = db_helper.markdown_to_text(md)
    text_content = " ".join(text_content.split(" ")[0:2000])
    lines = [line.replace("\n", " ") for line in text_content.split("\n\n")]
    
    return 1, lines

# Run retrain job
def run_retrain_job(candidates, md_path, index_path, logs):

    # Get candidate text
    candidate_text_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    text_data = []
    for candidate in tqdm.tqdm(candidates):
        candidate_text_stats['total'] += 1
        status, response = 0, ""
        try:
            status, candidate_text = get_candidate_text(candidate, md_path, logs)
            if status:
                text_data.append(candidate_text)
        except Exception as e:
            response = str(e)[0:50]
        candidate_text_stats['status'][status] = 1
        candidate_text_stats['response'][response] = 1 if response not in candidate_text_stats['response'] else candidate_text_stats['response'][response]+1
    print("Detected {} candidate text entries".format(len(text_data)))
    if len(text_data) == 0:
        return 0, "No candidate text entries"

    ### TBD -> replace with retrain code
    with open("/tmp/text_data_raw.json", "w") as f:
        print(json.dumps(text_data), file=f)
    
    return 1, json.dumps(candidate_text_stats)