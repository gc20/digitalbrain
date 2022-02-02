import json
import spacy
from digital_brain import helper as db_helper
import faiss
import numpy
import os
import tqdm
import pathlib
import re

# Get embedded entries from markdowns
def get_embedded_entries(candidate, md_path, embedded_entries, logs):

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
    md_lines = [line for line in md_lines if not re.search(r'^Auto-links:', line)]
    md = "\n".join(md_lines)

    # Convert to text and embed
    text_content = db_helper.markdown_to_text(md)
    spacy_nlp = db_helper.get_spacy_nlp()
    spacy_doc = spacy_nlp(text_content)

    # Prepare embedded entry
    embedded_entry = {k : candidate[k] for k in ["idb", "id", "type", "type_id"]}
    embedded_entry["file"] = md_filename
    embedded_entry["file_title"] = os.path.split(md_filename)[-1]
    embedded_entry["path_relative"] = md_filename.replace(md_path, "")
    embedded_entry["embedding"] = spacy_doc.vector
    embedded_entry["md"] = md
    embedded_entries[len(embedded_entries)] = embedded_entry

    return 1, "Embedded"


# Build FAISS index
def build_faiss_index(embedded_entries, logs):
    embeddings = [embedded_entries[i]["embedding"] for i in range(len(embedded_entries))]
    index = faiss.IndexFlatL2(300) # hardcoded based on Spacy vector default
    index.add(numpy.array(embeddings))
    print("FAISS index built with {} entries. Training status: {}".format(index.ntotal, index.is_trained))
    ## save index to disk
    return index


# Link markdown
def link_markdown(embedded_entry_fid, embedded_entries, faiss_index, logs):

    # Run faiss search & gather links
    embedded_entry = embedded_entries[embedded_entry_fid]
    distances, neighbors = faiss_index.search(numpy.array([embedded_entry["embedding"]]), k=5)
    auto_links = []
    neighbors_log = []
    for distance, neighbor_fid in zip(distances[0], neighbors[0]):
        if neighbor_fid < 0 or embedded_entry_fid == neighbor_fid:
            continue
        neighbor = embedded_entries[neighbor_fid]
        neighbors_log.append("{} @ {}".format(neighbor["id"], distance))
        auto_links.append( "[" + neighbor["file_title"] + "](<" + "obsidian://open?vault=md&file={}".format(neighbor["path_relative"]) + ">) @ D=" + "%.2f" % (distance) )

    # Add links
    md_lines = embedded_entry["md"].split("\n")
    if len(auto_links) > 0:
        if md_lines[-1] != "":
            md_lines.append("")
        md_lines.append("Auto-links: " + ", ".join(auto_links))
    md_new = "\n".join(md_lines)
    with open(embedded_entry["file"], 'w') as f:
        print(md_new, file=f)

    # Log links
    log_entry = {k : embedded_entry[k] for k in ["id", "type", "type_id"]}
    log_entry["links"] = neighbors_log
    logs["links"].Put(embedded_entry['idb'], json.dumps(log_entry).encode(encoding='UTF-8'))
    print(json.dumps(log_entry), file=logs["links_stream"])

    return 1, "Added {} auto-links".format(len(auto_links))


# Run link job
def run_link_job(candidates, md_path, logs):

    # Get embedded entries
    embedded_entries = {}
    embed_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        embed_stats['total'] += 1
        status, response = 0, ""
        try:
            status, response = get_embedded_entries(candidate, md_path, embedded_entries, logs)
        except Exception as e:
            response = str(e)[0:50]
        embed_stats['status'][status] = 1
        embed_stats['response'][response] = 1 if response not in embed_stats['response'] else embed_stats['response'][response]+1
    print(embed_stats)
    print("Generated {} embedded entries".format(len(embedded_entries)))
    if len(embedded_entries) == 0:
        return 0, "No embedded entries generated"

    # Build index
    faiss_index = build_faiss_index(embedded_entries, logs)

    # Link markdowns
    link_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for embedded_entry_fid in range(len(embedded_entries)):
        link_stats['total'] += 1
        status, response = 0, ""
        try:
            status, response = link_markdown(embedded_entry_fid, embedded_entries, faiss_index, logs)
        except Exception as e:
            response = str(e)[0:500]
        link_stats['status'][status] += 1
        link_stats['response'][response] = 1 if response not in link_stats['response'] else link_stats['response'][response]+1
    print(link_stats)

    return 1, json.dumps(link_stats)
