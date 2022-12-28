#To Dos
# 1] Add slack/notion/googledocs integrations/data + test run + commit
# 2] Airbyte format
# 3] OpenAI embeddings


## Sample commands
# python main.py --workflow 'url_adhoc' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/" --url "https://80000hours.org/2015/06/whats-the-best-way-to-spend-20000-to-help-the-common-good/"
# python main.py --workflow 'queries_adhoc' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/" --queries "Who is the founder of YCombinator?; What is web3?"
# python main.py --workflow 'crawl_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'process_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'embed_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'retrain_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'tag_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'link_job' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'experimental_similarity' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'experimental_summarization' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"
# python main.py --workflow 'experimental_querygen' --directory "/Users/Govind/Desktop/DB/code/v1-digitalbrain/"

import argparse
import os
import leveldb # consider plyvel
from digital_brain import candidates as db_candidates
from digital_brain import crawl as db_crawl
from digital_brain import process as db_process
from digital_brain import embed as db_embed
from digital_brain import retrain as db_retrain
from digital_brain import tag as db_tag
from digital_brain import link as db_link
from digital_brain import queryann as db_queryann
from experimental.similarity import experimental_similarity
from experimental.summarization import experimental_summarization
from experimental.querygen import experimental_querygen

# Arguments
parser = argparse.ArgumentParser(description='Command center')
parser.add_argument('--workflow', help='Workflow to run', type=str, required=True, choices=['url_adhoc', 'queries_adhoc', 'crawl_job', 'process_job', 'embed_job', 'retrain_job', 'tag_job', 'link_job', 'experimental_similarity', 'experimental_summarization', 'experimental_querygen'])
parser.add_argument('--directory', help='Working directory', type=str, required=True)
parser.add_argument('--mode', help='Mode to apply', type=str, default='prod_work', choices=['dev', 'prod_self', 'prod_work'])
parser.add_argument('--url', help='Adhoc URL to act on', type=str)
parser.add_argument('--queries', help='Adhoc queries to act on', type=str)
parser.add_argument('--crawl_mode', help='Crawling mode -> force (recrawl everything), retry (only failures), new (untried URLs)', type=str, default='new', choices=['force', 'retry', 'new'])
args = parser.parse_args()

if __name__ == "__main__":
    
    # Setup paths
    print("Workflow:", args.workflow)
    print("Mode:", args.mode)
    status, response = 0, "Nothing happened"
    if not os.path.exists(args.directory):
        status, response = 0, "Directory does not exist"
    working_directory = os.path.join(args.directory, args.mode)
    html_path = os.path.join(working_directory, "html")
    input_path = os.path.join(working_directory, "input")
    md_path = os.path.join(working_directory, "md")
    index_path = os.path.join(working_directory, "index")
    experimental_path = os.path.join(working_directory, "experimental")
    adhoc_path = os.path.join(working_directory, "adhoc")

    # Setup logs
    crawl_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'crawl_status.db'), create_if_missing=True)
    process_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'process_status.db'), create_if_missing=True)
    tags_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'tags_status.db'), create_if_missing=True)
    tags_stream = open(os.path.join(working_directory, "log", 'tags_stream.json'), "a")
    links_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'links_status.db'), create_if_missing=True)
    links_stream = open(os.path.join(working_directory, "log", 'links_stream.json'), "a")
    logs = {"crawl" : crawl_status, "process" : process_status, "tags" : tags_status, "tags_stream" : tags_stream, "links" : links_status, "links_stream" : links_stream}

    try:

        if args.workflow == "url_adhoc":
            candidates = [db_candidates.add_candidateid({"type_id" : args.url, "type" : "url", "path" : "url_adhoc"})]
            status, response = db_crawl.run_crawl_job(candidates, html_path, logs, args.crawl_mode)
            status, response = db_process.run_process_job(candidates, html_path, md_path, logs)
            status, response = db_embed.run_embed_job(candidates, md_path, index_path, logs, append=True)
            status, response = db_retrain.run_retrain_job(candidates, md_path, index_path, logs, append=True)
            status, response = db_tag.run_tag_job(candidates, md_path, logs)
            status, response = db_link.run_link_job(candidates, md_path, index_path, logs)

        elif args.workflow == "queries_adhoc":
            status, response = db_queryann.run_queryann_job(args.queries, index_path, adhoc_path)

        else:
            candidates = db_candidates.get_seed_candidates(input_path)

            if args.workflow == 'crawl_job':
                status, response = db_crawl.run_crawl_job(candidates, html_path, logs, args.crawl_mode)

            elif args.workflow == 'process_job':
                status, response = db_process.run_process_job(candidates, html_path, md_path, logs)

            elif args.workflow == 'embed_job':
                status, response = db_embed.run_embed_job(candidates, md_path, index_path, logs)

            elif args.workflow == 'retrain_job':
                status, response = db_retrain.run_retrain_job(candidates, md_path, index_path, logs)

            elif args.workflow == 'tag_job':
                status, response = db_tag.run_tag_job(candidates, md_path, logs)

            elif args.workflow == 'link_job':
                status, response = db_link.run_link_job(candidates, md_path, index_path, logs)

            elif args.workflow == 'experimental_similarity':
                status, response = experimental_similarity(candidates, experimental_path, logs)

            elif args.workflow == 'experimental_summarization':
                status, response = experimental_summarization(candidates, experimental_path, logs)

            elif args.workflow == 'experimental_querygen':
                status, response = experimental_querygen(candidates, experimental_path, logs)

    except Exception as e:
        status, response = 0, str(e)

    print("Status:", status)
    print("Response:", response)
