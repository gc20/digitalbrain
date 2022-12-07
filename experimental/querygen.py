import sys
sys.path.append("..")
from experimental import helper
import json
import tqdm
import transformers
import os
import numpy
import torch
import pathlib
import re

def experimental_querygen(candidates, experimental_path, logs):
 
    # Settings
    model_name = 'doc2query/all-t5-base-v1'
    device = torch.device("mps")
    tokenizer = transformers.T5Tokenizer.from_pretrained(model_name)
    model = transformers.T5ForConditionalGeneration.from_pretrained(model_name)
    batch_size = 16  # larger batch size == faster processing
    num_queries = 3  # number of queries to generate for each entry
    # os.environ["CUDA_VISIBLE_DEVICES"]= "0"

    # Load entries
    # entries = helper.get_candidate_entries(candidates, logs)
    entries = []
    for candidate in candidates:
        text = pathlib.Path(candidate['type_id']).read_text()
        text = "\n".join([t for t in text.split("\n") if not re.search(r'^(From|To|Date|Labels):', t)])
        entries.append({
            "file" : candidate['type_id'],
            "text" : text
            })
    print(len(entries))

    # Process batches
    batch = []
    with open(os.path.join(experimental_path, "querygen.json"), "w") as f:
        for entry in tqdm.tqdm(entries):

            batch.append(entry)
            if len(batch) != batch_size:
                continue

            inputs = tokenizer(
                [entry['text'] for entry in batch],
                truncation=True,
                padding=True,
                max_length=384,
                return_tensors='pt'
            )

            # generate three queries per entry
            outputs = model.generate(
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=64,
                do_sample=True,
                top_p=0.95,
                num_return_sequences=num_queries
            )

            # decode query to human readable text
            decoded_output = tokenizer.batch_decode(
                outputs,
                skip_special_tokens=True
            )

            # loop through to pair query and entry
            queries = []
            for i, query in enumerate(decoded_output):
                query = query.replace('\t', ' ').replace('\n', ' ')  # remove newline + tabs
                queries.append(query)
                if i % num_queries == num_queries-1:
                    batch_idx = int(i/num_queries)
                    print(json.dumps({
                        "text" : batch[batch_idx]['text'],
                        "file" : batch[batch_idx]['file'],
                        "queries" : queries
                        }), file=f)
                    queries = []
            
            batch = []
            batch_details = []
