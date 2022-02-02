# TBD: Identifying relevant emails, discarding non plain-text emails

import email
from email.policy import default
import readability
import markdownify

class MboxReader:
    def __init__(self, filename):
        self.handle = open(filename, 'rb')
        assert self.handle.readline().startswith(b'From ')
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.handle.close()
    def __iter__(self):
        return iter(self.__next__())
    def __next__(self):
        lines = []
        while True:
            line = self.handle.readline()
            if line == b'' or line.startswith(b'From '):
                # yield(b''.join(lines))
                yield email.message_from_bytes(b''.join(lines), policy=default)
                if line == b'':
                    break
                lines = []
                continue
            lines.append(line)

def __get_charsets(message):
    charsets = set({})
    for c in message.get_charsets():
        if c is not None:
            charsets.update([c])
    return charsets

def get_body(message):
    body = None
    if message.is_multipart():
        body = [part.get_payload(decode=True) for part in message.get_payload()]
    else:
        body = [message.get_payload(decode=True)]
    # while message.is_multipart():
    #     message = message.get_payload()[0]
    # body = message.get_payload(decode=True)
    body_decoded = []
    for charset in __get_charsets(message):
        for b in body:
            if b is not None:
                try:
                    body_decoded.append(b.decode(charset))
                except:
                    body_decoded.append(str(b))
    return ''.join(body_decoded)

def get_html_md(message):
    html = get_body(message)
    if len(html) < 100:
        return "", ""
    readability_article = readability.Document(html)
    html = readability_article.summary()
    md = markdownify.markdownify(html)
    md = "Subject: {}".format(message['Subject']) + "\nFrom: {}".format(message['From']) + "\n" + md
    return html, md


fn = '/Users/Govind/Documents/Backups/Google/Personal/All mail Including Spam and Trash-002.mbox'
i = 0
with MboxReader(fn) as mbox:
    for message in mbox:
        if message and message.get('From') and message.get('To') and message['From'].endswith('@gmail.com>') and message['To'].endswith('@gmail.com>'):
            print(message['From'])
            html, md = get_html_md(message)
            if len(md) > 100:
                with open("/Users/Govind/Desktop/atest/{}.html".format(i), "w") as f:
                    print(html, file=f)
                with open("/Users/Govind/Desktop/atest/{}.md".format(i), "w") as f:
                    print(md, file=f)
                i += 1
                if i == 100:
                    break