# pip install transformers[tf-cpu]
# python -c "from transformers import pipeline; print(pipeline('sentiment-analysis')('we love you'))"

import sys
sys.path.append("..")
from digital_brain import candidates
from experimental import helper
import leveldb # consider plyvel
import json
import tqdm
import os
import transformers

input_path = "/Users/Govind/Desktop/DB/prod/input"
working_directory = "/Users/Govind/Desktop/DB/prod/"
process_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'process_status.db'), create_if_missing=True)
logs = {"process" : process_status}

candidates = candidates.get_seed_candidates(input_path)
entries = helper.get_candidate_entries(candidates, logs)

model = transformers.PegasusForConditionalGeneration.from_pretrained("google/pegasus-multi_news")
tokenizer = transformers.PegasusTokenizer.from_pretrained("google/pegasus-multi_news")

with open("/tmp/experiment_summarization.json", "w") as f:
    for entry in tqdm.tqdm(entries):
        batch = tokenizer(entry['text'], truncation=True, padding='longest', return_tensors="pt")
        summary_ids = model.generate(batch.input_ids,
                    num_beams=6,
                    num_return_sequences=1,
                    no_repeat_ngram_size = 2,
                    length_penalty = 1,
                    min_length = 30,
                    max_length = 512,
                    early_stopping = True)
        output = [tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)]
        entry['summary'] = output[0]
        print(json.dumps(entry), file=f)
        # summary = tokenizer.decode(summary_ids[0])
