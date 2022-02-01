# conda install -c pytorch faiss-cpu
# Are vectors l2 normalized? Switch to approx similarity later.

import sys
sys.path.append("..")
from experimental import helper
import json
import tqdm
import os
import spacy
import faiss
import numpy

def experimental_similarity(candidates, experimental_path, logs):
 
    entries = helper.get_candidate_entries(candidates, logs)

    nlp = spacy.load("en_core_web_lg")
    embeddings = []
    entry_lookup = {}
    id = 0
    # ids = []
    for entry in tqdm.tqdm(entries):
        embeddings.append(nlp(entry['text']).vector)
        entry_lookup[id] = entry
        # ids.append(id)
        id+=1

    index = faiss.IndexFlatL2(300)
    index.add(numpy.array(embeddings))
    print(index.ntotal, index.is_trained)

    # index_base = faiss.IndexFlatL2(300)
    # index = faiss.IndexIDMap(index_base)
    ## index = faiss.IndexIVFFlat(index_base, 300, 100, faiss.METRIC_L2)
    # index.add_with_ids(numpy.array(embeddings), numpy.array(ids).astype('int64'))
    # print(index.ntotal, index.is_trained)
    # index.search(numpy.array([embeddings[0]]), k=3)

    with open(os.path.join(experimental_path, "similarity.tsv"), "w") as f:
        for id in entry_lookup:
            D, I = index.search(numpy.array([embeddings[id]]), k=3)
            if len(I) == 0 or len(I[0]) == 0:
                continue
            output = [
                entry_lookup[id]['url'],
                entry_lookup[id]['title']
            ]
            for counter, id_match in enumerate(I[0]):
                output.append(str(id_match))
                output.append(str(D[0][counter]))
                output.append(entry_lookup[id_match]['url'])
                output.append(entry_lookup[id_match]['title'])
            print("\t".join(output), file=f)
