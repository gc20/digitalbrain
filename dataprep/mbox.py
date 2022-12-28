# source /Users/Govind/miniconda/etc/profile.d/conda.sh

import sys
sys.path.append("..")
import mailbox
import bs4
import json
import re
import os
import hashlib
import quopri

def get_html_text(html):
    try:
        return bs4.BeautifulSoup(html, 'lxml').body.get_text(' ', strip=True)
    except AttributeError: # message contents empty
        return None

class GmailMboxMessage():
    def __init__(self, email_data):
        if not isinstance(email_data, mailbox.mboxMessage):
            raise TypeError('Variable must be type mailbox.mboxMessage')
        self.email_data = email_data
    def parse_email(self):
        return {
            "email_labels" : self.email_data['X-Gmail-Labels'],
            "email_date" : self.email_data['Date'],
            "email_from" : self.email_data['From'],
            "email_to" : self.email_data['To'],
            "email_subject" : self.email_data['Subject'],
            "email_text" : self.read_email_payload()         
        }
    def read_email_payload(self):
        email_payload = self.email_data.get_payload()
        if self.email_data.is_multipart():
            email_messages = list(self._get_email_messages(email_payload))
        else:
            email_messages = [email_payload]
        return [self._read_email_text(msg) for msg in email_messages]
    def _get_email_messages(self, email_payload):
        for msg in email_payload:
            if isinstance(msg, (list,tuple)):
                for submsg in self._get_email_messages(msg):
                    yield submsg
            elif msg.is_multipart():
                for submsg in self._get_email_messages(msg.get_payload()):
                    yield submsg
            else:
                yield msg
    def _read_email_text(self, msg):
        content_type = 'NA' if isinstance(msg, str) else msg.get_content_type()
        encoding = 'NA' if isinstance(msg, str) else msg.get('Content-Transfer-Encoding', 'NA')
        if 'text/plain' in content_type and 'base64' not in encoding:
            msg_text = msg.get_payload()
        elif 'text/html' in content_type and 'base64' not in encoding:
            msg_text = get_html_text(msg.get_payload())
        elif content_type == 'NA':
            msg_text = get_html_text(msg)
        else:
            msg_text = None
        return (content_type, encoding, msg_text)


# Store data in desired parseable format
def store_entry(entry, processed_folder, log_file, stats):
    if 'Trash' in entry['email_labels']:
        stats["trash"] += 1
        return
    body_text = [t[2] for t in entry['email_text'] if t[0] in ['text/plain'] and len(t) == 3 and t[2] is not None]
    if len(body_text) == 0:
        stats["no_body"] += 1
        return
    from_email = re.search(r'^.*?<([^\>]*)>$', entry['email_from'] or "-")
    if not from_email:
        stats["no_from"] += 1
        return
    from_email = from_email.group(1)
    to_email = re.search(r'^.*?<([^\>]*)>$', entry['email_to'] or "-")
    if not to_email:
        stats["no_to"] += 1
        return
    to_email = to_email.group(1)
    folder_name = processed_folder + from_email + "/" + to_email + "/" 
    file_name = (re.sub(r'[\s\/\\\"\']+', '-', entry['email_subject'].strip()) or "-")
    body_meta = "\n".join([
        "From: " + (entry['email_from'] or "-"),
        "To: " + (entry['email_to'] or "-"),
        "Date: " + (entry['email_date'] or "-"),
        "Subject: " + (entry['email_subject'] or "-"),
        "Labels: " + (entry['email_labels'] or "-"),
        "Body: " + "\n"
    ])
    body_text = "\n".join(body_text)
    body_text = re.sub(r'\n\n+', '\n', re.sub(r'[> ]+\n', '\n', body_text))
    # body_text = quopri.decodestring(body_text)
    body = body_meta + body_text
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    if os.path.exists(folder_name + file_name + ".txt"):
        md5 = hashlib.md5(body.encode('utf-8')).hexdigest()
        file_name += "-" + md5
        stats["clash"] += 1
    with open(folder_name + file_name + ".txt", "w") as f:
        # print(json.dumps(entry),file=f)
        print(body, file=f)
    stats["done"] += 1
    print(json.dumps({
        "from" : from_email,
        "to" : to_email,
        "date" : entry['email_date'], # import dateutil; epoch = dateutil.parser.parse(entry['email_date']).timestamp()
        "fn" : file_name
    }), file=log_file)


if __name__ == "__main__":
    
    input_fn = '/Users/Govind/Desktop/DB/Data/ss-email.mbox'
    processed_folder = "/Users/Govind/Desktop/DB/code/v1-digitalbrain/prod_work/input/ssemail_mbox/" 
    log_fn = "/tmp/ssemail_mbox.log"

    # Extract intermediate_fn
    mbox_obj = mailbox.mbox(input_fn)
    #num_entries = len(mbox_obj)
    stats = {"total" : 0, "done" : 0, "clash" : 0, "trash" : 0, "no_body" : 0, "no_to" : 0, "no_from" : 0, "error" : 0}
    with open(log_fn, "w") as log_file:
        for idx, email_obj in enumerate(mbox_obj):
            try:
                if idx % 1000 == 0:
                    print(stats)
                stats["total"] += 1
                email_data = GmailMboxMessage(email_obj)
                entry = email_data.parse_email()
                store_entry(entry, processed_folder, log_file, stats)
            except Exception as e:
                print("Error: ", str(e))
                stats["error"] += 1
