from flask import Flask, render_template, request, jsonify
import json
import os
from vars import base_url, base_catalogs, files_list, reponames_list
import subprocess, sys
import csv
from io import StringIO
from datetime import datetime, timedelta

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
    return render_template('log_analitics.html')

@app.route('/analyze_sources', methods=['POST'])
def analyze_sources():
    results, json_files, days = [], [], []
    source_counts = {}
    parsed_logs_dir = os.path.join(app.root_path, 'nginx', 'parsed')
    if request.form.get('start_date', '') and request.form.get('end_date', ''):
        search_start_date = datetime.strptime(request.form.get('start_date', ''),'%Y-%m-%d')
        search_end_date = datetime.strptime(request.form.get('end_date', ''),'%Y-%m-%d')
        date_range = 'Начиная с ' + search_start_date.date().strftime('%Y-%m-%d') + ', и заканчивая ' + search_end_date.date().strftime('%Y-%m-%d')
        day = [search_start_date + timedelta(days=x) for x in range((search_end_date - search_start_date).days + 1)]
    
        for i in day:
            days.append(i.date().strftime('%Y-%m-%d') + '_parsed-logs.json')

        json_files = list(set(days) & set(os.listdir(parsed_logs_dir)))
    else:
        date_range = 'все время'
        json_files = os.listdir(parsed_logs_dir)

    for json_file in json_files:
        log_file = os.path.join(parsed_logs_dir, json_file)
        with open(log_file, 'r') as f:
            logs = json.load(f)
            for log in logs:
                source_address = log.get('source_address')
                if source_address:
                    source_counts[source_address] = source_counts.get(source_address, 0) + 1
    
    for source, count in source_counts.items():
        results.append({
            'source_address': source,
            'count': count
        })

    results.sort(key=lambda x: x['count'], reverse=True)
    table_html = '<table class="table table-striped table-bordered">'
    table_html += '<thead><tr>'
    headers = ['source_address', 'count']

    for header in headers:
        table_html += f'<th>{header}</th>'
    
    table_html += '</tr></thead><tbody>'

    for entry in results:
        table_html += '<tr>'
        table_html += f'<td>{entry.get("source_address", "")}</td>'
        table_html += f'<td>{entry.get("count", "")}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'
    return render_template('sourses_ip.html', table=table_html, date_range=date_range)

@app.route('/requests')
def requests():
    return render_template('requests_analitics.html')

@app.route('/analyze_content', methods=['POST'])
def analyze_content():
    results, json_files, days = [], [], []
    content_counts = {}
    parsed_logs_dir = os.path.join(app.root_path, 'nginx', 'parsed')
    if request.form.get('start_date', '') and request.form.get('end_date', ''):
        search_start_date = datetime.strptime(request.form.get('start_date', ''),'%Y-%m-%d')
        search_end_date = datetime.strptime(request.form.get('end_date', ''),'%Y-%m-%d')
        date_range = 'Начиная с ' + search_start_date.date().strftime('%Y-%m-%d') + ', и заканчивая ' + search_end_date.date().strftime('%Y-%m-%d')
        day = [search_start_date + timedelta(days=x) for x in range((search_end_date - search_start_date).days + 1)]
    
        for i in day:
            days.append(i.date().strftime('%Y-%m-%d') + '_parsed-logs.json')

        json_files = list(set(days) & set(os.listdir(parsed_logs_dir)))
    else:
        date_range = 'все время'
        json_files = os.listdir(parsed_logs_dir)

    for json_file in json_files:
        log_file = os.path.join(parsed_logs_dir, json_file)
        with open(log_file, 'r') as f:
            logs = json.load(f)
            for log in logs:
                package_name = log.get('package_name')
                package_path = log.get('package_path')
                
                if all([package_name, package_path]):
                    key = (package_name, package_path)
                    content_counts[key] = content_counts.get(key, 0) + 1
    
    for (pkg_name, pkg_path), count in content_counts.items():
        results.append({
            'package_name': pkg_name,
            'package_path': pkg_path,
            'count': count
        })
    
    results.sort(key=lambda x: x['count'], reverse=True)
    table_html = '<table class="table table-striped table-bordered">'
    table_html += '<thead><tr>'
    headers = ['package name', 'package path', 'count']

    for header in headers:
        table_html += f'<th>{header}</th>'
    
    table_html += '</tr></thead><tbody>'

    for entry in results:
        table_html += '<tr>'
        table_html += f'<td>{entry.get("package_name", "")}</td>'
        table_html += f'<td>{entry.get("package_path", "")}</td>'
        table_html += f'<td>{entry.get("count", "")}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'

    return render_template('requests_table.html', table=table_html, date_range=date_range)

@app.route('/repo_requests')
def repo_requests():
    return render_template('repo_requests.html')

@app.route('/repo_analyse', methods=['POST'])
def repo_analyse():
    results, json_files, days = [], [], []
    content_counts = {}
    parsed_logs_dir = os.path.join(app.root_path, 'nginx', 'parsed')
    if request.form.get('start_date', '') and request.form.get('end_date', ''):
        search_start_date = datetime.strptime(request.form.get('start_date', ''),'%Y-%m-%d')
        search_end_date = datetime.strptime(request.form.get('end_date', ''),'%Y-%m-%d')
        date_range = 'Начиная с ' + search_start_date.date().strftime('%Y-%m-%d') + ', и заканчивая ' + search_end_date.date().strftime('%Y-%m-%d')
        day = [search_start_date + timedelta(days=x) for x in range((search_end_date - search_start_date).days + 1)]
    
        for i in day:
            days.append(i.date().strftime('%Y-%m-%d') + '_parsed-logs.json')

        json_files = list(set(days) & set(os.listdir(parsed_logs_dir)))
    else:
        date_range = 'все время'
        json_files = os.listdir(parsed_logs_dir)

    for json_file in json_files:
        log_file = os.path.join(parsed_logs_dir, json_file)
        with open(log_file, 'r') as f:
            logs = json.load(f)
            for log in logs:
                package_path = log.get('package_path')
                repo_name = package_path.split('/')[2]
                if repo_name:
                    content_counts[repo_name] = content_counts.get(repo_name, 0) + 1
    
    for repo_name, count in content_counts.items():
        results.append({
            'repo_name': repo_name,
            'count': count
        })
    
    results.sort(key=lambda x: x['count'], reverse=True)
    table_html = '<table class="table table-striped table-bordered">'
    table_html += '<thead><tr>'
    headers = ['repo_name', 'count']

    for header in headers:
        table_html += f'<th>{header}</th>'
    
    table_html += '</tr></thead><tbody>'

    for entry in results:
        table_html += '<tr>'
        table_html += f'<td>{entry.get("repo_name", "")}</td>'
        table_html += f'<td>{entry.get("count", "")}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'

    return render_template('repo_analyse.html', table=table_html, date_range=date_range)

@app.route('/repo_list')
def repo_list():
    results = load_file_info(reponames_list)
    print(results)
    table_html = '<table class="table table-striped table-bordered">'
    table_html += '<thead><tr>'
    headers = ['reponame']

    for header in headers:
        table_html += f'<th>{header}</th>'
    
    table_html += '</tr></thead><tbody>'

    for entry in results:
        table_html += '<tr>'
        table_html += f'<td>{entry.get("reponame", "")}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'

    return render_template('repo_list.html', table=table_html)
    
if __name__ == '__main__':
    app.run(debug=True)