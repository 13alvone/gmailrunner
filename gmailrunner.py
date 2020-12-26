import summarize
from urllib.request import urlopen
from bs4 import BeautifulSoup
import metadata_parser
import email.header
import requests
import datetime
import argparse
import imaplib
import logging
import email
import math
import time
import nltk
import sys
import os
import re

# Global Variables
gmail_email = os.environ.get('GMAIL_EMAIL')
gmail_passwd = os.environ.get('GMAIL_PASSWD')
gmail_folder = "INBOX"
start_time = time.time()
gmail_tags_path = 'gmailrunner.tags'
master_tags = set()
master_dict = {}
url_blacklist = [                                               # This is a `contains` blacklist, non-explicit
    'https://myaccount.google.com/notifications',
    'https://accounts.google.com/AccountChooser',
]
sender_whitelist = [
    'email_address_@_to_ignore.com',
    'other_address_@_to_ignore.com',
    'etc@you_get_it.com',
]
simple_summarizer = summarize.SimpleSummarizer()


def build_url_obj(_url):
    global master_tags
    meta_strategy = ['og', 'dc', 'meta', 'page']
    tags, page = [], None
    url_obj = {
        'title': '',
        'description': '',
        'image': set(),
        'site_name': '',
        'item_tags': {},
    }

    try:
        url_obj['description'] = summarize_url_content(_url)
    except Exception as e:
        logging.info(f'[!] The following url failed NTLK summarization:\n{_url}\n')

    try:
        page = metadata_parser.MetadataParser(url=_url, search_head_only=False)
        if page and url_obj['title'] != '':
            url_obj['title'] = page.get_metadatas('title', strategy=meta_strategy)
        if page and url_obj['description'] != '':
            url_obj['description'] = page.get_metadatas('description', strategy=meta_strategy)
        if page and url_obj['site_name'] != '':
            url_obj['site_name'] = page.get_metadatas('site_name', strategy=meta_strategy)
        if page and url_obj['image']:
            url_obj['image'].add(page.get_metadata_link('image'))
    except Exception:
        pass

    response = requests.get(_url)
    soup = BeautifulSoup(response.text, 'lxml')
    metas = soup.find_all('meta')

    for meta in metas:
        if 'property' in meta.attrs:
            if 'title' in meta.attrs['property']:
                url_obj['title'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if 'image' in meta.attrs['property']:
                url_obj['image'].add(meta.attrs['content'])
            if 'description' in meta.attrs['property']:
                url_obj['description'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if 'site_name' in meta.attrs['property']:
                url_obj['site_name'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
    for tag_set in tags:
        tag_up = tag_set.lstrip(' ').rstrip(' ').replace(' ', '_')
        for tag in master_tags:
            if tag in tag_up and tag in url_obj['item_tags']:
                url_obj['item_tags'][tag] += 1
            elif tag in tag_up and tag not in url_obj['item_tags']:
                url_obj['item_tags'][tag] = 1
    return url_obj


def populate_master_tags():
    global gmail_tags_path, master_tags
    f_in = open(_path, 'r')
    for line in f_in:
        x = line.replace('\r\n', '').replace('\r', '').replace('\n', '')
        y = x.lstrip(' ').rstrip(' ').replace(' ', '_')
        master_tags.add(y.lower())


def print_elapsed_time(_start_time):
    seconds = round(int(time.time() - _start_time), 2)
    minutes = math.trunc(seconds / 60)
    remaining_seconds = math.trunc(seconds - (minutes * 60))
    if len(f'{remaining_seconds}') != 2:
        remaining_seconds = f'0{remaining_seconds}'
    elapsed_time = f'{minutes}:{remaining_seconds}'
    time_message = f'**** Total_Time Elapsed: {elapsed_time} =======================\n\n'
    logging.info(time_message)


def gmail_authorize(gmail_service):
    try:
        _return_value, _data = gmail_service.login(gmail_email, gmail_passwd)
    except imaplib.IMAP4.error:
        logging.warning('[!] Login Failed\n')
        sys.exit(1)


def process_mailbox(_gmail_service):
    global url_blacklist, sender_whitelist, master_dict
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
                            is_blacklisted = 0
                            sender_approved = 0
                            for ignore_url in url_blacklist:
                                if ignore_url in url:
                                    is_blacklisted = 1
                            for sender in sender_whitelist:
                                if sender in email_from:
                                    sender_approved = 1
                            if url not in master_dict and url not in url_blacklist:
                                if is_blacklisted == 0 and sender_approved == 1:
                                    url_obj = build_url_obj(url)
                                    master_dict[url] = url_obj


def parse_email_list(gmail_service):
    global gmail_folder
    return_value, data = gmail_service.select(gmail_folder)
    if return_value == 'OK':
        logging.info(f'[i] Processing mailbox: {gmail_folder}\n')
        process_mailbox(gmail_service)
        gmail_service.close()
    else:
        logging.warning(f'[!] Error: Unable to open mailbox `{return_value}`')


def summarize_url_content(_url):
    global simple_summarizer
    html = urlopen(_url).read()
    raw = nltk.clean_html(html)
    summary = simple_summarizer.summarize(raw, 4)
    return summary


def main():
    global start_time, gmail_folder, master_dict
    gmail_service = imaplib.IMAP4_SSL('imap.gmail.com')
    gmail_authorize(gmail_service)
    parse_email_list(gmail_service)
    gmail_service.logout()
    for url in master_dict:
        print(f'[+] URL: {url}\n{master_dict[url]}')
    print_elapsed_time(start_time)


if __name__ == "__main__":
    main()
