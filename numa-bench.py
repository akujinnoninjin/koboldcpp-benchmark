import os
import time
import subprocess
import json
import requests
import csv
from pathlib import Path

API_URL = "http://10.10.100.55:5001/api"
CSV_FILE = 'benchmark_results.csv'

# For E5-2660v1
#THREADS = [1, 2, 4, 7, 8, 15, 16, 24, 31, 32]
#CORE_COUNT = 8

# For E5-2697v2
THREADS = [1, 2, 4, 8, 11, 12, 16, 20, 23, 24, 28, 32, 36, 40, 44, 47, 48]
CORE_COUNT = 12

# Number of repeats for each test
REPEATS  = 3

# Do BLAS Token Tests
TEST_BLASTOKENS = FALSE
BLASTOKENS = [512, 1024, 2048]



#### Shell Command Generator ########################
def generate_numactl_command(threads, single, USEBLAS, blastokens):
  cores_selected = []
  if single:
    interleave_range = "0"
    for i in range(threads):
      if i < CORE_COUNT:
        cores_selected.append(str(i))
      else:
        cores_selected.append(str(i+CORE_COUNT))
  else:
    interleave_range = "0-1"
    threads_per_socket = threads // 2
    threads_left_over = threads % 2

    # For 1-16 threads, add to P1/P2. For 17-32 add to P1+P2 then V1+V2  
    for i in range(threads_per_socket):
      if i < CORE_COUNT:
        cores_selected.append(str(i               )) # Socket 1
        cores_selected.append(str(i + CORE_COUNT  )) # Socket 2
      else:
        cores_selected.append(str(i + CORE_COUNT ))  # HT1
        cores_selected.append(str(i + CORE_COUNT*2)) # HT2
        
    cores_selected = sorted(cores_selected, key=int)
    
    if threads_left_over:
      if threads_per_socket < CORE_COUNT :
        cores_selected.append(str(threads_per_socket))               # Extra Socket1
      else:
        cores_selected.append(str(threads_per_socket + CORE_COUNT ))     # Extra HT1

  command = [
    'numactl',
    '-i',
    interleave_range,
    '-C',
    ','.join(cores_selected),
    'python3',
    './koboldcpp/koboldcpp.py',
    '--skiplauncher',
    '--smartcontext',
    '--nommap',
    '--usemlock',
    '--threads',
    str(threads),
    '--highpriority',
    '--contextsize',
    '8192',
    '--ropeconfig',
    '1.0', '10000',
    '--onready',
    'touch benchmark_temp',
    '--model',
    './koboldcpp/models/ColdMeds16b.gguf',
    #'./koboldcpp/models/OpenHermesSlerp.gguf',
    #'--debug',
    '--quiet',
    ] 
  if USEBLAS:
     command.append("--blasbatchsize")
     command.append(str(blastokens))
  else:
     command.append("--noavx2")
  return command


#### Prompt Generator ###############################
def genprompts(threads,singlethread,useblas, blastokens):
  # Start kcpp instance
  command = generate_numactl_command(threads, singlethread, useblas, blastokens)
  process = subprocess.Popen(command)
  
  print("Command:", " ".join(process.args))
  
  # Wait until lock file is created
  while not os.path.exists('./benchmark_temp'):
    time.sleep(1)  # Sleep for a second to avoid CPU hogging
  os.remove('./benchmark_temp')

  seeds = range(1, REPEATS+1)
  # process the SEEDS
  for seed in seedS:
    # API POST request payload
    payload = json.dumps({
      "max_context_length": 1600,
      "max_length": 120,
      "rep_pen": 1.1,
      "temperature": 0.7,
      "top_p": 0.92,
      "top_k": 100,
      "top_a": 0,
      "typical": 1,
      "tfs": 1,
      "rep_pen_range": 320,
      "rep_pen_slope": 0.7,
      "sampler_order": [6, 0, 1, 3, 4, 2, 5],
      "memory": " ***** INSERT TEST CONTEXT HERE ***** ",
      "min_p": 0,
      "dynatemp_range": 0,
      "presence_penalty": 0,
      "logit_bias": {},
      "prompt": "You: Hey Larissa, how are you today?\nLarissa:",
      "quiet": True,
      "stop_sequence": ["You:", "\nYou ", "\nLarissa: "],
      "use_default_badwordsids": False,
      "sampler_seed": seed
    })
  
    # API POST request headers
    headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json' #,
      #'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
  
    # make API POST request
    response = requests.post("http://127.0.0.1:5001/api/v1/generate", headers=headers, data=payload)
  
    #time.sleep(1)
    
    # make API GET request and extract required fields
    response = requests.get('http://10.10.100.55:5001/api/extra/perf')
    data = response.json()
    last_process = data['last_process']
    last_eval = data['last_eval']
  
    # write data to CSV
    with open(CSV_FILE, mode='a') as f:
      writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
      writer.writerow({
        'SINGLE': singlethread,
        'THREADS': threads,
        'SEED': seed,
        'BLAS': useblas,
        'BLASTOKENS': blastokens,
        'last_process': last_process,
        'last_eval': last_eval
      })
  
    # kill the process
  process.kill()
  
  # Print completion message
  print(f"Processing for {threads} thread(s) completed. BLAS: {useblas} SINGLETHREAD: {singlethread}")


#### MAIN ###############################
CSV_FIELDS = ['SINGLE', 'THREADS', 'SEED', 'BLAS', 'BLASTOKENS', 'last_process', 'last_eval']

# check if CSV file exists, if not, create it and write headers
if not Path(CSV_FILE).is_file():
  with open(CSV_FILE, mode='w') as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()

# cleanup failed run flag files
  if os.path.exists('./benchmark_temp'):
    os.remove('./benchmark_temp')

# Multi-socket, NOBLAS
for threads in THREADS:
  genprompts(threads,False,False,512) 
  
# Single-socket, NOBLAS
for threads in THREADS:
  if threads <= CORE_COUNT*2:
    genprompts(threads,True,False,512)
  
# Multi-socket, BLAS
if TEST_BLASTOKENS
  for threads in [12,24,36,48]:
    for blastokens in BLASTOKENS:
      genprompts(threads,False,True,blastokens)
  
print("Script execution finished.")
