#!/usr/bin/env python3
import random
import subprocess

RUNS = 5

for i in range(1, RUNS + 1):
    subprocess.run("rm -rf local* dummy* output*", shell=True, check=True)

    port = random.randint(5000, 65000)
    
    print(f"[{i}/{RUNS}] Running: python3 check.py {port}")

    result = subprocess.run(
        ["python3", "check.py", str(port)],
        check=False
    )
