from flask import Flask, render_template, request
import json
import os
from vars import base_url, base_catalogs, files_list
import subprocess, sys

app = Flask(__name__)

#функция загрузки данных о пакетах
def load_file_info(storage_path):
    if not os.path.exists(storage_path):
        return []
    with open(storage_path, 'r') as f:
        return json.load(f)

@app.route('/')
def index():
    #загруазка информацию о пакетах
    file_info = load_file_info(base_catalogs)

    #извлечение корневых каталогов
    root_dirs = set()
    for file in file_info:
        root_dir = file['catalogue']
        root_dirs.add(root_dir)

    return render_template('index.html', root_dirs=sorted(root_dirs))

@app.route('/search', methods=['GET', 'POST'])
def search():
    root_dirs = set()
    file_cats = load_file_info(base_catalogs)
    for file in file_cats:
        root_dir = file['catalogue']
        root_dirs.add(root_dir)
    query = request.form.get('query', '')
    selected_root = request.form.get('root_dir', '')
    #загруазка информацию о пакетах
    file_info = load_file_info(files_list)

    #фильтрация по корневому каталогу
    if selected_root:
        file_info = [f for f in file_info if f['url'].startswith(base_url+selected_root)]

    #поиск
    if query:
        file_info = [f for f in file_info if query.lower() in f['name'].lower()]

    return render_template('search_results.html', root_dirs=sorted(root_dirs), results=file_info)

#старт сервиса
if __name__ == '__main__':
    app.run(debug=True)
