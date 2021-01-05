from func_timeout import func_timeout, FunctionTimedOut
from bs4 import BeautifulSoup
import metadata_parser
import email.header
import mimetypes
import summarize
import datetime
import requests
import imaplib
import logging
import email
import math
import time
import nltk
import wget
import uuid
import json
import sys
import re
import os

# Global Variables
root_db_dir = '/tmp/piggylinks/'
gmail_email = os.environ.get('GMAIL_EMAIL')
gmail_passwd = os.environ.get('GMAIL_PASSWD')
gmail_folder = "INBOX"
start_time = time.time()
gmail_tags_path = 'cybersecurity.tags'
global_tags = set()
output_dict = {}
meta_strategy = ['meta', 'dc', 'og']
simple_summarizer = summarize.SimpleSummarizer()
url_block_list = [                                  # This is a `contains` block-list, non-explicit
    'https://myaccount.google.com/notifications',
    'https://accounts.google.com/AccountChooser',
]
sender_allow_list = [
    'email0@domain0',
    'email1@domain1'
]


def save_obj(_obj):
    global root_db_dir
    file_name = _obj['uuid']
    file_extension = _obj['extension'].replace('.', '')
    file_type_dir = f'{root_db_dir}/{file_extension}'
    if not os.path.isdir(file_type_dir):
        os.makedirs(file_type_dir)
    file_path = f'{file_type_dir}/{file_name}.{file_extension}'
    try:
        wget.download(_obj['url'], file_path)
    except Exception as e:
        with open(file_path, 'w') as f_out:
            f_out.write(f'{_obj}\n\n')
            f_out.write(f'{e}\n')
    _obj['file_path'] = f'{file_path}'
    return _obj


def parse_initial(_url_obj):
    global meta_strategy
    try:
        page = metadata_parser.MetadataParser(url=_url_obj['url'], search_head_only=True)
        if page and _url_obj['title'] != '':
            _url_obj['title'] = page.get_metadatas('title', strategy=meta_strategy)
        if page and _url_obj['description'] != '':
            _url_obj['description'] = page.get_metadatas('description', strategy=meta_strategy)
        if page and _url_obj['site_name'] != '':
            _url_obj['site_name'] = page.get_metadatas('site_name', strategy=meta_strategy)
        if page and _url_obj['image']:
            _url_obj['image'].add(page.get_metadata_link('image'))
        return _url_obj
    except Exception as e:
        logging.info(e)
        return _url_obj


def build_url_obj(_url, print_progress=True):
    global global_tags
    tags, page = [], None
    url_obj = {
        'uuid': uuid.uuid4().hex,
        'url': f'{_url}',
        'title': '',
        'description': '',
        'image': set(),
        'site_name': '',
        'tags': {},
        'type': None,
        'extension': None,
        'file_path': None
    }

    header_update = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1) AppleWebKit/605.1.15 '
                                   '(KHTML, like Gecko) Version/14.0.2 Safari/605.1.15',
                     'Connection': 'close',
                     'Cache-Control': 'no-cache',
                     'Pragma': 'no-cache'
                     }

    try:
        _url_obj = func_timeout(30, parse_initial, args=(url_obj,))
    except FunctionTimedOut:
        logging.warning(f'[!] Initial Parse Timed Out!\n[-] URL: {_url}\n')
    except Exception as e:
        logging.warning(f'[!] Initial Parse Failed\n[-] URL: {_url}\n[-] Error: {e}\n')

    try:
        response = requests.get(_url, verify=True, timeout=20, headers=header_update)
    except Exception as e:
        logging.info(e)
        return url_obj
    content_type = response.headers.get('content-type').split(';')[0]
    extension = mimetypes.guess_extension(content_type)
    soup = BeautifulSoup(response.text, features="lxml", parser="lxml")
    url_obj['description'] = summarize_url_content(_url, soup)
    url_obj['extension'] = extension
    url_obj['type'] = content_type
    try:
        metas = soup.find_all('meta')
        for meta in metas:
            if 'property' in meta.attrs:
                if 'title' in meta.attrs['property']:
                    url_obj['title'] = meta.attrs['content']
                    tags.append(meta.attrs['content'])
                if 'image' in meta.attrs['property']:
                    url_obj['image'].add(meta.attrs['content'])
                if 'description' in meta.attrs['property']:
                    if len(meta.attrs['content']) > 600:
                        url_obj['description'] = meta.attrs['content'][:599]
                        tags.append(meta.attrs['content'][:599])
                    else:
                        url_obj['description'] = meta.attrs['content']
                        tags.append(meta.attrs['content'])
                if 'site_name' in meta.attrs['property']:
                    url_obj['site_name'] = meta.attrs['content']
                    tags.append(meta.attrs['content'])
            if ' votes and ' in url_obj['description'] and ' comments so far on ' in url_obj['description']:
                new_description_str = ''
                content = list(filter(None, soup.text.split('\n')))[:-1]
                for entry in content:
                    if 'Press J to jump to the feed' not in entry:
                        if 'Posted by' not in entry and 'Days Ago' not in entry:
                            for item in content:
                                new_description_str += f' {item}'
                            if len(new_description_str) > 1500:
                                url_obj['description'] = new_description_str[:1499]
                                tags.append(new_description_str[:1499])
                            else:
                                url_obj['description'] = new_description_str
                                tags.append(new_description_str)
            if url_obj['title'] == '':
                url_obj['title'] = re.split(r'; |, |: |- |\*|\n|\r\n', url_obj['description'])[0]
    except Exception as e:
        logging.info(e)
        pass
    for tag_set in tags:
        tag_up = tag_set.strip().replace('"', '').replace('"', '')
        for tag in global_tags:
            if tag in tag_up and tag in url_obj['tags']:
                url_obj['tags'][tag] += 1
            elif tag in tag_up and tag not in url_obj['tags']:
                url_obj['tags'][tag] = 1
    if 'text/html' not in content_type:
        url_obj = save_obj(url_obj)
    if print_progress:
        msg = f'[+] URL Built\t{_url}\n[^]\tURl Obj {url_obj}\n'
        logging.info(msg)
        print(msg)
    return url_obj


def populate_global_tags():
    global gmail_tags_path, global_tags
    f_in = open(gmail_tags_path, 'r')
    for line in f_in:
        _tag = line.replace('\r\n', '').replace('\r', '').replace('\n', '').strip().lower()
        global_tags.add(_tag)


def print_elapsed_time(_start_time):
    seconds = round(int(time.time() - _start_time), 2)
    minutes = math.trunc(seconds / 60)
    remaining_seconds = math.trunc(seconds - (minutes * 60))
    if len(f'{remaining_seconds}') != 2:
        remaining_seconds = f'0{remaining_seconds}'
    elapsed_time = f'{minutes}:{remaining_seconds}'
    time_message = f'[i] Total_Time Elapsed: {elapsed_time}\n'
    logging.info(time_message)


def gmail_authorize(gmail_service):
    try:
        _return_value, _data = gmail_service.login(gmail_email, gmail_passwd)
    except imaplib.IMAP4.error as e:
        logging.warning(f'[!] Login Failed\n[!] {e}\n')
        sys.exit(1)


def process_mailbox(_gmail_service):
    global url_block_list, sender_allow_list, output_dict
    _return_value, _data = _gmail_service.search(None, "ALL")
    if _return_value != 'OK':
        logging.warning('[!] No messages found!\n')
        return
    for num in _data[0].split():
        _return_value, _data = _gmail_service.fetch(num, '(RFC822)')
        if _return_value != 'OK':
            logging.warning(f'[!] Error getting message {num}\n')
            return
        for response_part in _data:
            if isinstance(response_part, tuple):
                _message = email.message_from_string(response_part[1].decode('utf-8'))
                email_from = _message['from']
                for part in _message.walk():
                    if part.get_content_type() == 'text/plain':
                        message_payload = part.get_payload(decode=True).decode('utf-8')
                        url_list = re.findall(r'(https?://\S+)', message_payload)
                        for url in url_list:
                            url = url.lstrip("'").rstrip("'")
                            is_blacklisted = 0
                            sender_approved = 0
                            for ignore_url in url_block_list:
                                if ignore_url in url:
                                    is_blacklisted = 1
                            for sender in sender_allow_list:
                                if sender in email_from:
                                    sender_approved = 1
                            if url not in output_dict and url not in url_block_list:
                                if is_blacklisted == 0 and sender_approved == 1:
                                    url_obj = build_url_obj(url)
                                    output_dict[url] = url_obj


def parse_email_list(gmail_service):
    global gmail_folder
    return_value, data = gmail_service.select(gmail_folder)
    if return_value == 'OK':
        print(f'[i] Processing mailbox: {gmail_folder}\n')
        process_mailbox(gmail_service)
        gmail_service.close()
    else:
        logging.info(f'[!] Error: Unable to open mailbox `{return_value}`')


def summarize_url_content(_url, _soup):
    global simple_summarizer
    raw = _soup.get_text()
    raw_sentences = ' '.join(nltk.word_tokenize(raw)).replace(' .', '.')
    summary = simple_summarizer.summarize(raw_sentences, 4)
    return summary


def write_db_flat_file(_output_dict):
    file_name = f'{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}'
    with open(f'{file_name}.json', 'w') as f_out:
        json.dump(_output_dict, f_out)
    f_out.close()


def main():
    global start_time, gmail_folder, output_dict
    gmail_service = imaplib.IMAP4_SSL('imap.gmail.com')
    gmail_authorize(gmail_service)
    populate_global_tags()
    parse_email_list(gmail_service)
    gmail_service.logout()
    write_db_flat_file(output_dict)
    print_elapsed_time(start_time)


if __name__ == "__main__":
    main()
