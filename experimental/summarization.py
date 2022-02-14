# pip install transformers[tf-cpu]
# python -c "from transformers import pipeline; print(pipeline('sentiment-analysis')('we love you'))"

import sys
sys.path.append("../")
from experimental import helper
import json
import tqdm
import os
import transformers
import datetime

def experimental_summarization(candidates, experimental_path, logs):
 
    entries = helper.get_candidate_entries(candidates, logs)
    generated_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    model = transformers.BartForConditionalGeneration.from_pretrained("sshleifer/distilbart-xsum-12-1")
    tokenizer = transformers.BartTokenizer.from_pretrained("sshleifer/distilbart-xsum-12-1")

    with open(os.path.join(experimental_path, "summarization.json"), "a") as f:
        max_chunk_size = 8
        for i in range(0, len(entries), max_chunk_size):
            print("Iteration {}".format(i), flush=True)
            chunk = entries[i:i+max_chunk_size]
            batch = tokenizer([entry['text'] for entry in chunk], truncation=True, padding=True, return_tensors="pt")
            summary_ids = model.generate(batch.input_ids,
                        num_beams=4,
                        num_return_sequences=1,
                        no_repeat_ngram_size = 2,
                        length_penalty = 1,
                        min_length = 30,
                        max_length = 512,
                        early_stopping = True)
            output = [tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)]
            for j, entry in enumerate(chunk):
                entry['summary'] = output[0][j]
                entry['generated_at'] = generated_at
                print(json.dumps(entry), file=f, flush=True)
            # summary = tokenizer.decode(summary_ids[0])
