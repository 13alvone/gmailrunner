from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
import argparse
import logging
import smtplib
import ssl
import os
import re

# Global Variables
email_message = MIMEMultipart()
email_message['From'] = '<From Email Address>'
email_message['To'] = '<To Email Address>'
context = ssl.create_default_context()
passwd = os.environ.get('GMAIL')        # Define your local password as environment variable
smtp_server = "smtp.gmail.com"
port = 465  # TLS --> OR OPTION: SSL 465


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--subject', help='Email Subject Line', default='BLANK', type=str, required=False)
    parser.add_argument('-o', '--object', help='File or Web Path', type=str, required=True)
    arguments = parser.parse_args()
    return arguments


def attach_file(__object):
    part = MIMEBase('application', "octet-stream")
    with open(__object, 'rb') as file_in:
        part.set_payload(file_in.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="{}"'.format(Path(__object).name))
    email_message.attach(part)
    file_in.close()


def is_valid_url(__object):
    try:
        URLValidator()(__object)
        return True
    except ValidationError as e:
        logging.info(e)
        return False


def send_message(__object,):
    global email_message, context, passwd, smtp_server, port
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(email_message['From'], passwd)
        formatted_message = f'subject:{__object["subject"]}\n{__object}'
        server.sendmail(email_message['From'], email_message['To'], formatted_message)


def main():
    global email_message, context, passwd, smtp_server, port
    args = parse_args()
    subject = args.subject
    _object = args.object
    email_message['Subject'] = subject
    if is_valid_url(_object) or (isinstance(_object, str) and re.match('^http', _object)):
        email_message.attach(MIMEText(_object))
        send_message(email_message)
    else:
        print(hasattr(_object, 'r'))
        attach_file(_object)
        send_message(email_message)


if __name__ == '__main__':
    main()
