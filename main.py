## Sample commands
# python main.py --workflow 'crawl_url_adhoc' --directory "/Users/Govind/Desktop/DB/" --mode="dev" --url_adhoc "https://huggingface.co/tasks/question-answering"
# python main.py --workflow 'process_html_adhoc' --directory "/Users/Govind/Desktop/DB/" --mode="dev" --url_adhoc "https://huggingface.co/tasks/question-answering"
# python main.py --workflow 'crawl_job' --directory "/Users/Govind/Desktop/DB/"
# python main.py --workflow 'process_job' --directory "/Users/Govind/Desktop/DB/"
# python main.py --workflow 'tag_job' --directory "/Users/Govind/Desktop/DB/"
# python main.py --workflow 'link_job' --directory "/Users/Govind/Desktop/DB/"
# python main.py --workflow 'experimental_similarity' --directory "/Users/Govind/Desktop/DB/"

import argparse
import os
import leveldb # consider plyvel
from digital_brain import candidates as db_candidates
from digital_brain import crawl as db_crawl
from digital_brain import process as db_process
from digital_brain import tag as db_tag
from digital_brain import link as db_link
from experimental.similarity import experimental_similarity
from experimental.summarization import experimental_summarization

# Arguments
parser = argparse.ArgumentParser(description='Command center')
parser.add_argument('--workflow', help='Workflow to run', type=str, required=True, choices=['crawl_url_adhoc', 'process_html_adhoc', 'crawl_job', 'process_job', 'tag_job', 'link_job', 'experimental_similarity', 'experimental_summarization'])
parser.add_argument('--directory', help='Working directory', type=str, required=True)
parser.add_argument('--mode', help='Mode to apply', type=str, default='prod', choices=['dev', 'prod'])
parser.add_argument('--url_adhoc', help='Adhoc URL to act on', type=str)
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
    experimental_path = os.path.join(working_directory, "experimental")

    # Setup logs
    crawl_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'crawl_status.db'), create_if_missing=True)
    process_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'process_status.db'), create_if_missing=True)
    tags_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'tags_status.db'), create_if_missing=True)
    tags_stream = open(os.path.join(working_directory, "log", 'tags_stream.json'), "a")
    links_status = leveldb.LevelDB(os.path.join(working_directory, "log", 'links_status.db'), create_if_missing=True)
    links_stream = open(os.path.join(working_directory, "log", 'links_stream.json'), "a")
    logs = {"crawl" : crawl_status, "process" : process_status, "tags" : tags_status, "tags_stream" : tags_stream, "links" : links_status, "links_stream" : links_stream}

    try:

        candidates = None
        if args.workflow.endswith("_adhoc"):
            candidates = db_candidates.add_candidateid({"type_id" : args.url_adhoc, "type" : "url"})
        else:
            candidates = db_candidates.get_seed_candidates(input_path)

        if args.workflow == "crawl_url_adhoc":
            status, response = db_crawl.crawl_url(candidates, html_path, logs, args.crawl_mode)

        elif args.workflow == 'process_html_adhoc':
            status, response = db_process.process_html(candidates, html_path, md_path, logs)

        elif args.workflow == 'crawl_job':
            status, response = db_crawl.run_crawl_job(candidates, html_path, logs, args.crawl_mode)

        elif args.workflow == 'process_job':
            status, response = db_process.run_process_job(candidates, html_path, md_path, logs)

        elif args.workflow == 'tag_job':
            status, response = db_tag.run_tag_job(candidates, md_path, logs)

        elif args.workflow == 'link_job':
            status, response = db_link.run_link_job(candidates, md_path, logs)

        elif args.workflow == 'experimental_similarity':
            status, response = experimental_similarity(candidates, experimental_path, logs)

        elif args.workflow == 'experimental_summarization':
            status, response = experimental_summarization(candidates, experimental_path, logs)

    except Exception as e:
        status, response = 0, str(e)

    print("Status:", status)
    print("Response:", response)
