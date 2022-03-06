from digital_brain import helper as db_helper
import os
import numpy
import json
import collections

# Run Q&A job
def run_qna_job(queries, index_path, adhoc_path):

    # Load index, embedded entries and model
    target_embedded_entries, faiss_index = db_helper.load_faiss_index(index_path)
    sentencetransformer_model = db_helper.get_sentence_transformer()

    # Process queries
    query_status = collections.defaultdict(int)
    with open(os.path.join(adhoc_path, "qna.json"), "a") as f:
        for query in queries.split("; "):
            query_embedding = sentencetransformer_model.encode(query)
            distances, neighbors = faiss_index.search(numpy.array([query_embedding]), k=5)
            for i in range(len(distances)):
                entry = {"query" : query, "results" : []}
                for distance, neighbor_fid in zip(distances[i], neighbors[i]):
                    if neighbor_fid < 0 or distance < 0.001:
                        continue
                    entry['results'].append({
                        "file" : target_embedded_entries[neighbor_fid]['file'],
                        "file_title" : target_embedded_entries[neighbor_fid]['file_title'],
                        "md" : target_embedded_entries[neighbor_fid]['md'],
                        "distance" : str(distance)
                    })
                print(json.dumps(entry), file=f)
                query_status[len(distances[i])] += 1
    
    return 1, json.dumps(query_status)
