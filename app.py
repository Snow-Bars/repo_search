from flask import Flask, render_template, request
import json
import os
from vars import base_url, base_catalogs, files_list, res_folder
import subprocess, sys
import csv
from io import StringIO

app = Flask(__name__)

#функция загрузки данных о пакетах
def load_file_info(storage_path):
    if not os.path.exists(storage_path):
        return []
    with open(storage_path, 'r') as f:
        return json.load(f)

def calculate_relevance_score(filename, query_terms):
    filename_lower = filename.lower()
    total_score = 0
    
    for query in query_terms:
        query_lower = query.lower()
        term_score = 0
        
        if query in filename:
            term_score += 100
        
        if query_lower in filename_lower:
            position = filename_lower.index(query_lower)
            term_score += 50 * (1.0 / (position + 1))
            match_ratio = len(query) / len(filename)
            term_score += 30 * match_ratio
        
        total_score += term_score
    
    return total_score

def csv_to_html_table(csv_content):
    output = StringIO()
    csv_reader = csv.reader(StringIO(csv_content))
    html = ['<table class="table table-striped table-bordered">']
    header = next(csv_reader)
    html.append('<thead><tr>')

    for column in header:
        html.append(f'<th>{column}</th>')

    html.append('</tr></thead>') 
    html.append('<tbody>')

    for row in csv_reader:
        html.append('<tr>')
        for cell in row:
            html.append(f'<td>{cell}</td>')
        html.append('</tr>')

    html.append('</tbody>')
    html.append('</table>')

    return '\n'.join(html)

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
    query = request.form.get('query', '').strip()
    selected_root = request.form.get('root_dir', '')
    #загруазка информацию о пакетах
    file_info = load_file_info(files_list)

    #фильтрация по корневому каталогу
    if selected_root:
        file_info = [f for f in file_info if f['url'].startswith(base_url+selected_root)]

    #поиск с сортировкой по релевантности
    if query:
        query_terms = [term.strip() for term in query.split() if term.strip()]
        matching_files = []

        for f in file_info:
            filename_lower = f['name'].lower()
            if all(term.lower() in filename_lower for term in query_terms):
                score = calculate_relevance_score(f['name'], query_terms)
                matching_files.append((f, score))
        
        matching_files.sort(key=lambda x: x[1], reverse=True)
        file_info = [f[0] for f in matching_files]

    return render_template('search_results.html', root_dirs=sorted(root_dirs), results=file_info)

@app.route('/vuln', methods=['GET', 'POST'])
def vulnerabilities():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'vuln.csv')

        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        csv_data = list(csv.reader(StringIO(csv_content)))
        headers = csv_data[0]
        rows = csv_data[1:]
        search_query = request.form.get('query', '').lower()

        if search_query and request.method == 'POST':
            filtered_rows = []
            for row in rows:
                if any(search_query in cell.lower() for cell in row):
                    filtered_rows.append(row)
            rows = filtered_rows
        
        table_html = '<table class="table table-striped table-bordered">'
        table_html += '<thead><tr>'

        for header in headers:
            table_html += f'<th>{header}</th>'

        table_html += '</tr></thead>'
        table_html += '<tbody>'

        for row in rows:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell}</td>'
            table_html += '</tr>'

        table_html += '</tbody></table>'
        
        return render_template('vulnerabilities.html', table=table_html, search_query=search_query)
    except Exception as e:
        return f'Error: {str(e)}', 500

@app.route('/logs')
def logs():
    try:
        search_query = request.form.get('query', '').strip().lower()
        parsed_logs_dir = os.path.join(os.path.dirname(__file__), 'nginx', 'parsed')
        table_html = '<table class="table table-striped table-bordered">'
        table_html += '<thead><tr>'
        headers = ['Дата', 'Время', 'Аджрес источника', 'Имя репозитария', 'Запрошенный путь', 'Запрошенный файл']
        
        for header in headers:
            table_html += f'<th>{header}</th>'

        table_html += '</tr></thead><tbody>'
        json_files = [f for f in os.listdir(parsed_logs_dir) if f.endswith('.json')]
        
        for json_file in sorted(json_files, reverse=True):
            file_path = os.path.join(parsed_logs_dir, json_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                logs_data = json.load(f)
                
                for entry in logs_data:
                    if search_query:
                        entry_text = ' '.join(str(v) for v in entry.values()).lower()
                        if search_query not in entry_text:
                            continue
                    
                    table_html += '<tr>'
                    table_html += f'<td>{entry.get("date", "")}</td>'
                    table_html += f'<td>{entry.get("time", "")}</td>'
                    table_html += f'<td>{entry.get("source_address", "")}</td>'
                    table_html += f'<td>{entry.get("repo_name", "")}</td>'
                    table_html += f'<td>{entry.get("package_path", "")}</td>'
                    table_html += f'<td>{entry.get("package_name", "")}</td>'
                    table_html += '</tr>'
        
        table_html += '</tbody></table>'
        return render_template('logs.html', table=table_html, search_query=search_query)
        
    except Exception as e:
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True)