# Gmail Runner

## About

Gmail Runner is a component I created to run as a local task to poll data that I want to share with myself. The ultimate goal is to create an email address that automatically parses any artifacts, documents, links, and eventually other file types into a local database that can later be presented to me as a master database of all artifacts of interest. Organization and information consumption speed is most valuable for this project.

## Prerequisites

There is a requirements.txt file, but there is also a special package that requires a manual local installation by way of a python3 terminal:

`pip3 install -r requirements.txt`

`nltk.download()`

The later of these commands installs the components needed for use in the summary generation process.