## Sample commands

### Setup
```cd prod_work && mkdir adhoc experimental html index input log md```
- input: contains data that needs to be processedl; can include symlinks, actual data or .urls files. My current input/ folder has the following entries: "chrome_bookmarks evernote gmail local notion slack"
- html: Data is ingested and stored in html format
- md: Data is further processed and stored in md format (I happen to have followed a lot of the steps as page 15 of WebGPT - https://arxiv.org/pdf/2112.09332.pdf; except this one where I picked md instead of simple HTML)
- index: Pickled embeddings and embeddings are stored here
- log: Log lookups in leveldb, including of metadata and actions carried out are stored here
- adhoc: stores results of adhoc queries
- experimental: stores results of experimental work

### Crawl and store an adhoc URL
```python main.py --workflow 'url_adhoc' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/" --url "https://80000hours.org/2015/06/whats-the-best-way-to-spend-20000-to-help-the-common-good/"

### Run adhoc searches
python main.py --workflow 'queries_adhoc' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/" --queries "Who is the founder of YCombinator?; What is web3?"

### Run a crawler for any URLs in .urls files
python main.py --workflow 'crawl_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### Ingest and process files of all formats
python main.py --workflow 'process_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### Embed and create a vectorized form of each document
python main.py --workflow 'embed_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Deprecated] Fine-tune the model (pre-GPT)
python main.py --workflow 'retrain_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Deprecated] Tag documents with useful keywords for search
python main.py --workflow 'tag_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Deprecated] Link documents to each other
python main.py --workflow 'link_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Experimental] Document similarity 
python main.py --workflow 'experimental_similarity' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Experimental] Summarization (pre-GPT)
python main.py --workflow 'experimental_summarization' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

### [Experimental] Document to query generation (for generating fine-tuning samples)
python main.py --workflow 'experimental_querygen' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
```
