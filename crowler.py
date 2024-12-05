import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from vars import *

#получение файлов
def fetch_files_recursive(url, visited=None):
    if visited is None:
        visited = set()

    #предотвращение повторного посещения одной и той же ссылки
    if url in visited:
        return []

    visited.add(url)
    response = requests.get(url)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    file_info = []

    #парсинг ссылок
    for link in soup.find_all('a'):
        href = link.get('href')
                
        full_url = url + href

        if href.endswith('/') and (not href.startswith('.')):  #проверка, является ли ссылка директорией
            file_info.extend(fetch_files_recursive(full_url, visited)) #переход в директорию
        elif (not href.startswith('.')) and (not href.endswith(exclude_suffix)): #формирование списка файлов
            file_name = link.get_text()
            file_info.append({
                'name': file_name,
                'url': full_url
                })
    
    return file_info

def fetch_root_catalogs(url):
    response = requests.get(url)
    
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    catalogs = []

    for link in soup.find_all('a'):
        href = link.get('href')
                
        if href.endswith('/') and (not href.startswith('.')):
            cat_name = href.strip('/')
            catalogs.append({
                'catalogue': cat_name
            })
        
    return catalogs

def load_file_info(storage_path):
    if not os.path.exists(storage_path):
        return []
    with open(storage_path, 'r') as f:
        return json.load(f)

def fetch_reponames(file, url):
    unique_reponames = set()
    reponames = []
    for f in load_file_info(file):
        reponame = f.get('url').removeprefix(url).split('/')[1]
        print(reponame)
        if reponame not in unique_reponames:
            unique_reponames.add(reponame)
            reponames.append({
                'reponame': reponame
            })

    return reponames

#сохранение данных в json
def save_file_info(info, storage_path):
    with open(storage_path, 'w') as f:
        json.dump(info, f, ensure_ascii=False, indent=4)

#получение данных из json
def load_file_info(storage_path='file_data.json'):
    if not os.path.exists(storage_path):
        return []
    
    with open(storage_path, 'r') as f:
        return json.load(f)

def run_scraper():
    file_info = fetch_files_recursive(base_url)
    save_file_info(file_info,files_list)
    catalogs = fetch_root_catalogs(base_url)
    save_file_info(catalogs,base_catalogs)
    reponames = fetch_reponames(files_list, base_url)
    save_file_info(reponames,reponames_list)

run_scraper()