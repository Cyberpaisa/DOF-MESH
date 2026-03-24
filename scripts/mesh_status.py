
import json
import os
import sys
import time
from tabulate import tabulate

def read_json_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def print_status(nodes, orchestrator_memory, json_output=False, watch=False):
    table = []
    for node in nodes:
        table.append([node['node_id'], node['status'], node['provider'], node['last_active']])
    if json_output:
        print(json.dumps(table, indent=4))
    else:
        print(tabulate(table, headers=['Node ID', 'Status', 'Provider', 'Last Active'], tablefmt='grid'))
    if watch:
        while True:
            os.system('clear')
            nodes = read_json_file('logs/mesh/nodes.json')
            print_status(nodes, orchestrator_memory, json_output, watch)
            time.sleep(5)

def main():
    nodes = read_json_file('logs/mesh/nodes.json')
    orchestrator_memory = read_json_file('logs/mesh/orchestrator_memory.json')
    json_output = '--json' in sys.argv
    watch = '--watch' in sys.argv
    print_status(nodes, orchestrator_memory, json_output, watch)

if __name__ == '__main__':
    main()
