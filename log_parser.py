import json
import os
from vars import *

def pars_log_line(log_line):
    date, log_line, trash = log_line.split('] ')
    date = date.lstrip('[')
    date, time = date.split('T')
    time = time.split('+')[0]
    source_address, log_line = log_line.split(' - - ')
    package_path = log_line.split(' ')[1]
    repo_name = package_path.split('/')[1]
    package_name = package_path.rsplit('/')[-1]
    return date, time, source_address, repo_name, package_path, package_name

def get_log_files(dir):
    arr = os.listdir(dir)
    return arr

def get_res(filename):
    parser_result = []
    with open(filename, 'r') as f:
        for log_line in f:
            date, time, source_address, repo_name, package_path, package_name = pars_log_line(log_line)
            parser_result.append({
                'date': date,
                'time': time,
                'source_address': source_address,
                'repo_name': repo_name,
                'package_path': package_path,
                'package_name': package_name
                })
    return parser_result

def save_file_info(info, results_folder, storage_path):
    path = results_folder + info[1]['date'] + '_' + storage_path
    with open(path, 'w') as f:
        json.dump(info, f, ensure_ascii=False, indent=4)

def run_parse():
    for file in get_log_files(nginx_log_folder):
        a = get_res(nginx_log_folder + file)
        save_file_info(a, res_folder, res_file)

run_parse()