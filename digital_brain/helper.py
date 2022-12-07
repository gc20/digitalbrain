import bs4
import re
import spacy
import yake
import sentence_transformers
import markdown
import os
import faiss
import pickle

# Convert markdown to text (md -> html -> text since BeautifulSoup can extract text cleanly)
def markdown_to_text(md):

    # Clean out existing auto-*
    md_lines = md.strip("\n").split("\n")
    md_lines = [line for line in md_lines if not re.search(r'^Auto-*:', line)]
    md = "\n".join(md_lines)

    # Convert to HTML
    html = markdown.markdown(md)

    # remove code snippets
    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)

    # Extract text
    soup = bs4.BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))

    return text

spacy_nlp = spacy.load("en_core_web_lg") # python -m spacy download en_core_web_lg
def get_spacy_nlp():
    return spacy_nlp

yake_nlp = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=10, features=None)
def get_yake_nlp():
    return yake_nlp

sentencetransformer_model = sentence_transformers.SentenceTransformer('msmarco-distilbert-base-v4')
def get_sentence_transformer():
    return sentencetransformer_model

# Load FAISS index + embedding entries
def load_faiss_index(index_path):
    embedded_entries = None
    with open(os.path.join(index_path, "faiss_docs_sentencetransformers_embeddedentries.pickle"), 'rb') as handle:
        embedded_entries = pickle.load(handle)
    index = faiss.read_index(os.path.join(index_path, "faiss_docs_sentencetransformers.index"))
    print("Loaded FAISS index & embedded entries")
    return embedded_entries, index