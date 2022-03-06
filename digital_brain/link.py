import json
from digital_brain import helper as db_helper
from digital_brain import embed as db_embed
import numpy
import tqdm

# Link markdown
def link_markdown(embedded_entry, faiss_index, embedded_entries, logs):

    # Run faiss search & gather links
    distances, neighbors = faiss_index.search(numpy.array([embedded_entry["embedding"]]), k=10)
    auto_links = []
    neighbors_log = []
    for distance, neighbor_fid in zip(distances[0], neighbors[0]):
        if neighbor_fid < 0 or distance < 0.001:
            continue
        neighbor = embedded_entries[neighbor_fid]
        neighbors_log.append("{} @ {}".format(neighbor["id"], distance))
        auto_links.append( "[" + neighbor["file_title"] + "](<" + "obsidian://open?vault=md&file={}".format(neighbor["path_relative"]) + ">) @ D=" + "%.2f" % (distance) )

    # Add links to md
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
def run_link_job(candidates, md_path, index_path, logs):

    # Load index and embedded entries
    target_embedded_entries, faiss_index = db_helper.load_faiss_index(index_path)
    target_embedded_entries_lookup = {}
    for embedded_entry_fid in target_embedded_entries:
        target_embedded_entries_lookup[target_embedded_entries[embedded_entry_fid]['id']] = embedded_entry_fid

    # Get embedded entries (candidates)
    candidate_embedded_entries = {}
    embed_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        embed_stats['total'] += 1
        status, response = 0, ""
        try:
            embedded_entry = None
            if candidate['path'] != "url_adhoc" and candidate['id'] in target_embedded_entries_lookup: # Currently "file" is inferred from stored embeddings, which isn't ideal if same URL has different entry point; ideally retain embedding but do process.get
                embedded_entry = target_embedded_entries[target_embedded_entries_lookup[candidate['id']]]
                status, response = 1, "Found in pre-load index"
            else:
                status, response, embedded_entry = db_embed.get_embedded_entry(candidate, md_path, logs)
            if embedded_entry:
                candidate_embedded_entries[len(candidate_embedded_entries)] = embedded_entry # Although indices could overlap with target, doesn't matter since we aren't indexing
        except Exception as e:
            response = str(e)[0:50]
        embed_stats['status'][status] = 1
        embed_stats['response'][response] = 1 if response not in embed_stats['response'] else embed_stats['response'][response]+1
    print(embed_stats)
    print("Detected {} candidate embedded entries".format(len(candidate_embedded_entries)))
    if len(candidate_embedded_entries) == 0:
        return 0, "No candidate embedded entries"

    # Link markdowns
    link_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for embedded_entry_fid in range(len(candidate_embedded_entries)):
        link_stats['total'] += 1
        status, response = 0, ""
        try:
            embedded_entry = candidate_embedded_entries[embedded_entry_fid]
            status, response = link_markdown(embedded_entry, faiss_index, target_embedded_entries, logs)
        except Exception as e:
            response = str(e)[0:500]
        link_stats['status'][status] += 1
        link_stats['response'][response] = 1 if response not in link_stats['response'] else link_stats['response'][response]+1
    print(link_stats)

    return 1, json.dumps(link_stats)
