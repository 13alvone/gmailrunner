#!/bin/python3

# Standard Python3 Library Items
import datetime
import email
import email.header
import imaplib
import json
import logging
import math
import mimetypes
import os
import re
import sys
import time
import uuid

# Non-Standard PyPi Imports
import metadata_parser
import nltk
import requests
import wget
from tld import get_tld
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from func_timeout import func_timeout, FunctionTimedOut

# Custom Imports
import summarize

# Global Variables
root_db_dir = '~/piggylinks'
global_timeout = 60
content_length = 2000
gmail_email = os.environ.get('GMAIL_EMAIL')
gmail_passwd = os.environ.get('GMAIL_PASSWD')
gmail_folder = "INBOX"
start_time = time.time()
gmail_tags_path = 'cybersecurity.tags'
global_tags = set()
output_dict = {}
meta_strategy = ['meta', 'dc', 'og', 'page']
simple_summarizer = summarize.SimpleSummarizer()
url_block_list = [  # This is a `contains` block-list, non-explicit
    'https://myaccount.google.com/notifications',
    'https://accounts.google.com/AccountChooser',
]

sender_allow_list = [
    'allow_email_0@domain.com',
    'allow_email_1@domain.com'
]

generic_headers = {'Connection': 'close',
                   'Cache-Control': 'no-cache',
                   'Pragma': 'no-cache',
                   'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
                   }


def is_valid_url(_url):
    try:
        URLValidator()(_url)
        return True
    except ValidationError as e:
        logging.info(e)
        return False


# Save a given `_url_obj` to file by downloading it from its given, full url.
def save_obj(_url_obj):
    global root_db_dir
    if not is_valid_url(_url_obj['url']):
        return _url_obj
    file_name = _url_obj['uuid']
    file_extension = _url_obj['extension'].replace('.', '')
    file_type_dir = f'{root_db_dir}/{file_extension}'
    if not os.path.isdir(file_type_dir):
        os.makedirs(file_type_dir)
    file_path = f'{file_type_dir}/{file_name}.{file_extension}'
    try:
        wget.download(_url_obj['url'], file_path)
    except Exception as e:
        with open(file_path, 'w') as f_out:
            f_out.write(f'{_url_obj}\n\n')
            f_out.write(f'{e}\n')
    _url_obj['file_path'] = f'{file_path}'
    return _url_obj


# Function to perform initial url processing with the `metadata_parser` component
def parse_initial(_url_obj,):
    global meta_strategy, global_timeout, generic_headers
    try:
        page = metadata_parser.MetadataParser(url=_url_obj['url'], search_head_only=True)
    except Exception as e:
        logging.info(f'{e}')
        _args = {'args': (_url_obj['url'],), 'kwargs': {'headers': generic_headers}}
        response = func_timeout_wrapper(_timeout_sec=global_timeout, _func_obj=requests.get, _args_obj=_args)['output']
        if not response.text:
            return _url_obj
        page = metadata_parser.MetadataParser(html=response.text, search_head_only=True)
    if page and _url_obj['title'] != '':
        if isinstance(page.get_metadatas('title', strategy=meta_strategy), list):
            _url_obj['title'] = page.get_metadatas('title', strategy=meta_strategy)[0]
        elif isinstance(page.get_metadatas('title', strategy=meta_strategy), str):
            _url_obj['title'] = page.get_metadatas('title', strategy=meta_strategy)
    if page and _url_obj['description'] != '':
        if isinstance(page.get_metadatas('description', strategy=meta_strategy), list):
            _url_obj['description'] = page.get_metadatas('description', strategy=meta_strategy)[0]
        elif isinstance(page.get_metadatas('description', strategy=meta_strategy), str):
            _url_obj['description'] = page.get_metadatas('description', strategy=meta_strategy)
    if page and _url_obj['site_name'] != '':
        if isinstance(page.get_metadatas('site_name', strategy=meta_strategy), list):
            _url_obj['site_name'] = page.get_metadatas('site_name', strategy=meta_strategy)[0]
        elif isinstance(page.get_metadatas('site-name', strategy=meta_strategy), str):
            _url_obj['site_name'] = page.get_metadatas('site_name', strategy=meta_strategy)
    if page and _url_obj['image']:
        if isinstance(page.get_metadata_link('image', strategy=meta_strategy), list):
            for item in page.get_metadata_link('image'):
                _url_obj['image'].add(item)
        elif isinstance(page.get_metadata_link('image', strategy=meta_strategy), str):
            _url_obj['image'].add(page.get_metadata_link('image'))
    return _url_obj


def func_timeout_wrapper(_timeout_sec, _func_obj, _args_obj):
    '''
    [PURPOSE] --> `Add timeout to ANY func`         # cspeakes - "13alvone" custom wrapper
    @ _timeout_sec --> int                          # Variable Type
    @ _func_obj --> `function_do`                   # Example string of `function_do()
    @ _args_obj --> `Option 0` || `Option 1`        # Two options of input available
        : Option 0
            [t] tuple                               # Type tuple input, **kwargs is optional
        : Option 1
            [t] dict                                # Type dictionary input containing:
            [^] {'args': arg_tuple(),               # --> tuple containing positional args, `None` for none.
                'kwargs': kwarg_dict()              # --> dictionary containing named args
                }
    '''

    function_obj = {
        'name': _func_obj.__name__,
        'args': _args_obj,
        'timeout': _timeout_sec,
        'error': None,
        'output': None
    }

    # If tuple, process function with only positional args, kwargs and positional if dictionary.
    try:
        if isinstance(_args_obj, tuple):
            function_obj['output'] = func_timeout(timeout=_timeout_sec, func=_func_obj, args=_args_obj)
        elif isinstance(_args_obj, dict):
            _args = _args_obj['args']
            _kwargs = _args_obj['kwargs']
            function_obj['output'] = func_timeout(timeout=_timeout_sec, func=_func_obj, args=_args, kwargs=_kwargs)
        return function_obj

    # Return explicit alert if function failed due to timeout.
    except FunctionTimedOut:
        function_obj['error'] = f'Timeout for function `{_func_obj}` exceeded {_timeout_sec} seconds.'
        msg = f'[!] {function_obj["error"]}\n' \
              f'\tFunction:\t{function_obj["name"]}\n' \
              f'\tArguments:\t{function_obj["args"]}\n' \
              f'\tTimeout:\t{function_obj["timeout"]}\n' \
              f'\tFunction Output:\t{function_obj["output"]}\n'
        logging.warning(msg)
        return function_obj

    # Return explicit alert if function failed due to issue with the passed function itself.
    except Exception as e:
        function_obj['error'] = f'{e}'.replace('\n', '. ')
        msg = f'[!] General function error in function `{function_obj["name"]}`.\n' \
              f'\tFunction:\t{function_obj["name"]}\n' \
              f'\tArguments:\t{function_obj["args"]}\n' \
              f'\tTimeout:\t{function_obj["timeout"]}\n' \
              f'\tError Details:\t{function_obj["error"]}\n' \
              f'\tFunction Output:\t{function_obj["output"]}\n'
        logging.warning(msg)
        return function_obj


def build_url_obj(_url, print_progress=True):
    global global_tags, global_timeout, content_length, generic_headers
    tags, page = [], None

    # Define `url_obj` which will be returned for each `url` passed to this function.
    url_obj = {
        'uuid': uuid.uuid4().hex,
        'url': f'{_url}',
        'title': '',
        'description': None,
        'image': set(),
        'site_name': None,
        'tags': {},
        'type': None,
        'extension': None,
        'file_path': None
    }

    # Exit the following unnecessary cpu cost if url is found to be invalid.
    if not is_valid_url(_url):
        return url_obj

    # Attempt initial build of url metadata with the `metadata_parser` class as a first attempt.
    results = func_timeout_wrapper(global_timeout, parse_initial, (url_obj,))
    url_obj = results['output'] if results['output'] else results['args'][0]

    # Try-Except to generate and augment any existing data with a separate content parsing mechanism
    try:
        request_args = {'args': (_url,),
                        'kwargs': {
                            'verify': True,
                            'timeout': 30,
                            'headers': generic_headers
                        }}
        response_obj = func_timeout_wrapper(global_timeout, requests.get, request_args)
        if response_obj['error']:
            return url_obj
        response = response_obj['output']
        content_type = response_obj['output'].headers.get('content-type')
        if content_type:
            if ';' in content_type:
                content_type = content_type.split(';')[0]
            extension = mimetypes.guess_extension(content_type)
            url_obj['extension'] = extension
        soup = BeautifulSoup(response.text, features="lxml", parser="lxml")
        url_obj['description'] = summarize_url_content(_url, soup)
        url_obj['type'] = content_type

        # Tag any additional information found from within `property` metadata to the url_obj
        metas = soup.find_all('meta')
        for meta in metas:
            if 'property' in meta.attrs and 'title' in meta.attrs['property']:
                url_obj['title'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if 'property' in meta.attrs and 'image' in meta.attrs['property']:
                url_obj['image'].add(meta.attrs['content'])
            if 'property' in meta.attrs and 'description' in meta.attrs['property']:
                if len(meta.attrs['content']) > content_length:
                    url_obj['description'] = meta.attrs['content'][:content_length-1]
                    tags.append(meta.attrs['content'][:content_length-1])
                else:
                    url_obj['description'] = meta.attrs['content']
                    tags.append(meta.attrs['content'])
            if 'property' in meta.attrs and 'site_name' in meta.attrs['property']:
                url_obj['site_name'] = meta.attrs['content']
                tags.append(meta.attrs['content'])

            # If comments section is detected in content, minimize the noise by removing it, if possible.
            if ' votes and ' in url_obj['description'] and ' comments so far on ' in url_obj['description']:
                new_description_str = ''
                content = list(filter(None, soup.text.split('\n')))[:-1]
                _continue = True
                for entry in content:
                    if ('Press J to jump to the feed' in entry) or ('Posted by' in entry and 'Days Ago' in entry):
                        _continue = False
                    if _continue:
                        new_description_str += f' {entry}'
                if len(new_description_str) > content_length:
                    url_obj['description'] = new_description_str[:content_length-1]
                    tags.append(new_description_str[:content_length-1])
                else:
                    url_obj['description'] = new_description_str
                    tags.append(new_description_str)

    except Exception as e:
        logging.info(e)

    # Correct `title` if it is blank by pulling the first delimited section of `description`.
    if isinstance(url_obj, dict) and not url_obj['title']:
        url_obj['title'] = re.split(r'; |, |: |- |\*|\n|\r\n', url_obj['description'])[0]

        # Correct 'site_name' if empty: by pulling the domain from the url only
        if not url_obj['site_name']:
            url_obj['site_name'] = get_tld(_url, as_object=True).fld

    # Check saved content against any tags found in `cybersecurity.tags` and sum occurrence to define category.
    full_content = ' '.join(tags)
    for tag in global_tags:
        if tag in full_content and tag in url_obj['tags']:
            url_obj['tags'][tag] += 1
        elif tag in full_content and tag not in url_obj['tags']:
            url_obj['tags'][tag] = 1

    # Save content if content is confirmed to be of any other type than `.html`
    if url_obj['extension'] and '.html' not in url_obj['extension']:
        url_obj = save_obj(url_obj)

    # Optional mechanism passed as a keyword arg to print ongoing progress to `stdout`.
    if print_progress:
        msg = f'[+] URL Built\t{_url}\n\tURl Obj {url_obj}\n'
        logging.info(msg)
        print(msg)

    return url_obj


# Pull all newline-delimited tags defined in the global variable path `gmail_tags_path`
def populate_global_tags():
    global gmail_tags_path, global_tags
    f_in = open(gmail_tags_path, 'r')
    for line in f_in:
        _tag = line.replace('\r\n', '').replace('\r', '').replace('\n', '').strip().lower()
        global_tags.add(_tag)


# General purpose, elapsed time updater used throughout processing.
def print_elapsed_time(_start_time):
    seconds = round(int(time.time() - _start_time), 2)
    minutes = math.trunc(seconds / 60)
    remaining_seconds = math.trunc(seconds - (minutes * 60))
    if len(f'{remaining_seconds}') != 2:
        remaining_seconds = f'0{remaining_seconds}'
    elapsed_time = f'{minutes}:{remaining_seconds}'
    time_message = f'[i] Total_Time Elapsed: {elapsed_time}\n'
    logging.info(time_message)


# Initial Gmail authorization mechanism required prior to initial gmail email pull
def gmail_authorize(gmail_service):
    try:
        _return_value, _data = gmail_service.login(gmail_email, gmail_passwd)
    except imaplib.IMAP4.error as e:
        logging.warning(f'[!] Login Failed\n[!] {e}\n')
        sys.exit(1)


# Parse through the emails available in the mailbox defined in the global variable `gmail_folder`
def process_mailbox(_gmail_service):
    global url_block_list, sender_allow_list, output_dict
    _return_value, _data = _gmail_service.search(None, "ALL")

    # If the return value is anything but okay, avoid any unnecessary cpu cost by passing the remainder.
    if _return_value != 'OK':
        logging.warning('[!] No messages found!\n')
        return

    # If data is returned properly, parse each and continue processing and formatting of returned data.
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


# Parse the given folder defined with the global variable `gmail_folder`
def parse_email_list(gmail_service):
    global gmail_folder
    return_value, data = gmail_service.select(gmail_folder)
    if return_value == 'OK':
        print(f'[i] Processing mailbox: {gmail_folder}\n')
        process_mailbox(gmail_service)
        gmail_service.close()
    else:
        logging.info(f'[!] Error: Unable to open mailbox `{return_value}`')


# Simple description summarizer based on (https://github.com/thavelick/summarize/)
# Author cspeakes - "13alvone": Modified several lines to operate properly in python3 and with gmailrunner
# Original license can be located here: (https://github.com/thavelick/summarize/blob/master/LICENSE.TXT)
def summarize_url_content(_url, _soup):
    global simple_summarizer
    raw = _soup.get_text()
    raw_sentences = ' '.join(nltk.word_tokenize(raw)).replace(' .', '.')
    summary = simple_summarizer.summarize(raw_sentences, 4)
    return summary


# Convert dictionary to output `.json` file
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
