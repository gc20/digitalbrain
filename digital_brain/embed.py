import json
import faiss
from digital_brain import helper as db_helper
import numpy
import tqdm
import os
import pathlib
import re
import pickle

# Get embedded entry from markdowns
def get_embedded_entry(candidate, md_path, logs):

    # Get md
    md_filename, md = None, None
    try:
        md_filename = json.loads(logs["process"].Get(candidate['idb']).decode())["file"]
        md = pathlib.Path(md_filename).read_text()
    except Exception as e:
        return 0, "Could not extract md", None
    if len(md) < 5:
        return 0, "md not meaningful enough", None

    # Clean out existing auto-*
    md_lines = md.strip("\n").split("\n")
    md_lines = [line for line in md_lines if not re.search(r'^Auto-[\w+]:', line)]
    md = "\n".join(md_lines)

    # Convert to text and embed
    text_content = db_helper.markdown_to_text(md)
    sentencetransformer_model = db_helper.get_sentence_transformer()
    sentence_embedding = sentencetransformer_model.encode(text_content)

    # Prepare embedded entry
    embedded_entry = {k : candidate[k] for k in ["idb", "id", "type", "type_id"]}
    embedded_entry["file"] = md_filename
    embedded_entry["file_title"] = os.path.split(md_filename)[-1]
    embedded_entry["path_relative"] = md_filename.replace(md_path, "")
    embedded_entry["embedding"] = sentence_embedding
    embedded_entry["md"] = md

    return 1, "Embedded", embedded_entry


# Build & store FAISS index + embedding entries 
def build_faiss_index(embedded_entries, index_path):
    with open(os.path.join(index_path, "faiss_docs_sentencetransformers_embeddedentries.pickle"), 'wb') as handle:
        pickle.dump(embedded_entries, handle, protocol=pickle.HIGHEST_PROTOCOL)
    embeddings = [embedded_entries[i]["embedding"] for i in range(len(embedded_entries))]
    index = faiss.IndexFlatL2(768) # hardcoded based on sentence_transformer
    # index = faiss.IndexFlatIP(300) # hardcoded based on Spacy vector default
    # embeddings_np = numpy.array(embeddings)
    # faiss.normalize_L2(embeddings_np) # Cosine similarity hack for FAISS (https://www.lftechnology.com/blog/ai/faiss-basics/); Spacy expects cosine (https://spacy.io/api/token#similarity)
    index.add(numpy.array(embeddings))
    print("FAISS index built with {} entries. Training status: {}".format(index.ntotal, index.is_trained))
    faiss.write_index(index, os.path.join(index_path, "faiss_docs_sentencetransformers.index"))
    return index

# Run embed job
def run_embed_job(candidates, md_path, index_path, logs, append=False):

    # Load if needed
    embedded_entries = {}
    if append is True:
        embedded_entries, _ = db_helper.load_faiss_index(index_path)

    # Get embedded entries (candidates)
    embed_stats = {"total" : 0, "status" : {1: 0, 0: 0}, "response" : {}}
    for candidate in tqdm.tqdm(candidates):
        embed_stats['total'] += 1
        status, response = 0, ""
        try:
            status, response, embedded_entry = get_embedded_entry(candidate, md_path, logs)
            if embedded_entry:
                embedded_entries[len(embedded_entries)] = embedded_entry
        except Exception as e:
            response = str(e)[0:50]
        embed_stats['status'][status] = 1
        embed_stats['response'][response] = 1 if response not in embed_stats['response'] else embed_stats['response'][response]+1
    print("Detected {} candidate embedded entries".format(len(embedded_entries)))
    if len(embedded_entries) == 0:
        return 0, "No candidate embedded entries"

    # Build index
    _ = build_faiss_index(embedded_entries, index_path)
    
    return 1, json.dumps(embed_stats)