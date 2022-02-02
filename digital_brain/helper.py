import bs4
import re
import spacy
import yake
import markdown

# Convert markdown to text
def markdown_to_text(md):
    # md -> html -> text since BeautifulSoup can extract text cleanly
    html = markdown.markdown(md)
    # remove code snippets
    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)
    # extract text
    soup = bs4.BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))
    return text

spacy_nlp = spacy.load("en_core_web_lg") # python -m spacy download en_core_web_lg
def get_spacy_nlp():
    return spacy_nlp

# NLP
yake_nlp = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=10, features=None)
def get_yake_nlp():
    return yake_nlp
