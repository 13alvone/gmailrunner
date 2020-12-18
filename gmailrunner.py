from __future__ import print_function
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import requests
import pickle
import os.path
import base64
import re

# Global variables
scopes = ['https://www.googleapis.com/auth/gmail.readonly']
_path = '/root/gmailrunner.tags'
_trash_set = set()
master_tags = set()
master_dict = {}


def authorize():
    global scopes
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service


def gather_urls():
    global _trash_set
    raw_url_list = []
    url_list = set()
    service = authorize()
    results = service.users().messages().list(userId='me').execute()
    email_messages = results['messages']
    for email_message in email_messages:
        thread_id = email_message['id']
        _trash_set.add(thread_id)
        message_container = service.users().messages().get(userId='me', id=email_message['id']).execute()
        message_subcontainer = message_container['payload']['parts']
        for item in message_subcontainer:
            try:
                base64_message = item['body']['data']
                message_bytes = base64.b64decode(base64_message)
                message = message_bytes.decode('ascii')
                print(f'Item: {item}\nMessage: {message}\n\n')
                raw_url_list.append(message)
            except:
                pass
    for raw_url in raw_url_list:
        if 'http' in raw_url:
            unclean_list = re.findall(r'(https?://\S+)', raw_url)
            for unclean_item in unclean_list:
                if unclean_item not in url_list:
                    url_list.add(unclean_item)
    return url_list


def populate_master_tags():
    global _path, master_tags
    f_in = open(_path, 'r')
    for line in f_in:
        x = line.replace('\r\n', '').replace('\r', '').replace('\n', '')
        y = x.lstrip(' ').rstrip(' ').replace(' ', '_')
        master_tags.add(y.lower())


def build_url_obj(url):
    global master_dict, master_tags
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    metas = soup.find_all('meta')
    tags = []
    preview_obj = {
        'og_title': '',
        'og_description': '',
        'og_image': '',
        'og_site_name': ''
    }
    url_obj = {
        'full_title': '',
        'short_title': '',
        'site_name': '',
        'image_urls': [],
        'item_tags': {},
        'item_type': '',
        'preview_obj': {},
        'description': '',
    }

    for meta in metas:
        if 'name' in meta.attrs and meta.attrs['name'] == 'title':
            url_obj['full_title'] = meta.attrs['content']
            tags.append(meta.attrs['content'])
        if 'property' in meta.attrs:
            if meta.attrs['property'] == 'og:title':
                url_obj['short_title'] = meta.attrs['content']
                preview_obj['og_title'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if meta.attrs['property'] == 'og:image':
                url_obj['image_urls'].append(meta.attrs['content'])
                preview_obj['og_image'] = meta.attrs['content']
            if meta.attrs['property'] == 'og:description':
                url_obj['description'] = meta.attrs['content']
                preview_obj['og_description'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if meta.attrs['property'] == 'og:site_name':
                url_obj['site_name'] = meta.attrs['content']
                preview_obj['og_site_name'] = meta.attrs['content']
                tags.append(meta.attrs['content'])
            if meta.attrs['property'] == 'og:type':
                url_obj['item_type'] = meta.attrs['content']

    for tag_set in tags:
        tag_up = tag_set.lstrip(' ').rstrip(' ').replace(' ', '_')
        for tag in master_tags:
            if tag in tag_up and tag in url_obj['item_tags']:
                url_obj['item_tags'][tag] += 1
            elif tag in tag_up and tag not in url_obj['item_tags']:
                url_obj['item_tags'][tag] = 1
    url_obj['preview_obj'] = preview_obj
    return url_obj


def main():
    global _trash_set, master_dict
    populate_master_tags()
    url_list = gather_urls()
    print(url_list)
    for url in url_list:
        url_object = build_url_obj(url)
        master_dict[url] = url_object
        # print(f'[URL] {url}')
        # print('\n----------------------------\n')
        # print(url_object)
        # print('\n-------------------\n')
        # print(_trash_set)
    # for item in master_dict:
    #    print(f'[URL] {item}', '\n--------------------\n')
    #    print(f'[+] {master_dict[item]}', '\n')


if __name__ == '__main__':
    main()
