from __future__ import print_function

import csv
import os
import glob
import json
import time
import tqdm
import datetime
import hashlib
import re

def __write_to_file(message_cache, output_folder, date_fn, message_writecounter):
    if len(message_cache) > 0:
        message_fn = output_folder + "/" + re.sub(r'\.json$', '_' + str(message_writecounter) + ".json", date_fn)
        with open(message_fn, "w") as f:
            _ = f.write(message_cache)


if __name__ == '__main__':

    # Config
    input_folder = '/Users/Govind/Desktop/DB/Data/slack_ss'
    processed_folder = "/Users/Govind/Desktop/DB/code/v1-digitalbrain/prod_work/input/slack_ss/" 
    slack_users_fn = "/Users/Govind/Desktop/DB/Data/slack_ss_users.json"

    # Process data by channel
    slack_users = json.load(open(slack_users_fn))
    for channel_folder in tqdm.tqdm(sorted(glob.glob(input_folder + "/*"))):
        channel_name = os.path.split(channel_folder)[-1]
    
        # Process by date file in each channel
        for date_fn in sorted(glob.glob(channel_folder + "/*")):

            # Load data
            date_name = os.path.split(date_fn)[-1]
            date_file = open(date_fn, mode='r')
            data = date_file.read()
            data = json.loads(data)
            date_file.close()

            # Prepare output folder
            output_folder = processed_folder + "/" + channel_name
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            
            # Process messages
            message_cache = ""
            message_writecounter = 1
            for message in data:
                if 'user' in message and 'ts' in message and message.get('type', '') == "message":
                    timestamp = datetime.datetime.fromtimestamp(int(float(message['ts']))).strftime("%Y-%m-%d %H:%M:%S")
                    message_text = "[REPLY] " if message.get('subtype', '') == 'thread_broadcast' else ""
                    message_text += "in:#{}; from:@{}; at:{}\n".format(channel_name, slack_users.get(message['user']) or message['user'], timestamp)
                    message_text += "\n".join(["> " + m for m in message.get('text', '').split("\n")])
                    message_cache += message_text + "\n"
                if len(message_cache) > 5000:
                    __write_to_file(message_cache, output_folder, date_name, message_writecounter)
                    message_writecounter += 1
                    message_cache = ""
            __write_to_file(message_cache, output_folder, date_name, message_writecounter)
