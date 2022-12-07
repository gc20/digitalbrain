# Retrain

import transformers
import datasets
import json

def preprocess_function(examples):
    return tokenizer([" ".join(x) for x in examples["text"]], truncation=True, padding=True)

def group_texts(examples):
    block_size = 128
    concatenated_examples = {k: sum(examples[k], []) for k in examples.keys()}
    total_length = len(concatenated_examples[list(examples.keys())[0]])
    result = {
        k: [t[i : i + block_size] for i in range(0, total_length, block_size)]
        for k, t in concatenated_examples.items()
    }
    result["labels"] = result["input_ids"].copy()
    return result

# Initialize tokenizer
tokenizer = transformers.AutoTokenizer.from_pretrained("distilgpt2")

# Load data
text_data = json.load(open("/tmp/text_data_raw.json"))

# Load and prep data
data = datasets.Dataset.from_dict({"text" : text_data})
data = data.shuffle()
data = data.train_test_split(test_size=0.2)

# Tokenize data
tokenizer.pad_token = tokenizer.eos_token
tokenized_data = data.map(
    preprocess_function,
    batched=True,
    num_proc=4,
    remove_columns=data["train"].column_names,
)

# Split into smaller chunks by block_size
lm_dataset = tokenized_data.map(group_texts, batched=True, num_proc=4)

# Create batch and pad
data_collator = transformers.DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Setup model
model = transformers.AutoModelForCausalLM.from_pretrained("distilgpt2")

# Define hyperparameters
training_args = transformers.TrainingArguments(
    output_dir="/Users/Govind/Desktop/db/prod/log/lm_retrain_results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    weight_decay=0.01,
)

# Pass arguments to trainer
trainer = transformers.Trainer(
    model=model,
    args=training_args,
    train_dataset=lm_dataset["train"],
    eval_dataset=lm_dataset["test"],
    data_collator=data_collator,
)

# Train
trainer.train()