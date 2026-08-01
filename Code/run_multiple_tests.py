from multiprocessing import Pool
import subprocess
import sys
import ast
from typing import List
import time
import os
import argparse

import ast
import os

ALLOWED_IMPORTS = {"socket", "threading", "time", "random", "json", "os", "hashlib", "typing", "dataclasses"}
ALLOWED_FROM_IMPORTS = {"socket", "threading", "time", "random", "json", "hashlib", "typing", "dataclasses"} # Basically I wante to make sure that students cannot do from os import rename etc. So FROM imports from os are not allowed

ALLOWED_OS_FUNCTIONS = {"os.remove", "os.makedirs"} # All other other os functions are not allowed

ALLOWED_OPEN_FUNCTIONS = {"send_file", "recieve_file"} # Only these functions are allowed to use open()

def analyze_code(file_path: str) -> bool:
	"""
	Analyze the student's code:
	- Only allowed modules are imported
	- Only allowed os functions are called
	- open() is only used inside allowed methods
	"""
	if not os.path.exists(file_path):
		print(f"File {file_path} does not exist.")
		return False

	with open(file_path, "r") as f:
		code = f.read()

	alias_map = {}

	try:
		tree = ast.parse(code)
		errors = []

		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				for alias in node.names:
					alias_map[alias.asname or alias.name] = alias.name
					if alias.name not in ALLOWED_IMPORTS:
						print(f"\033[91m[RESTRICTED IMPORT]\033[0m {alias.name} found!")
						return True

			elif isinstance(node, ast.ImportFrom):
				if node.module not in ALLOWED_FROM_IMPORTS:
					print(f"\033[91m[RESTRICTED IMPORT]\033[0m from {node.module} import ... is not allowed!")
					return True

				for alias in node.names:
					full_name = f"{node.module}.{alias.name}"
					alias_map[alias.asname or alias.name] = full_name

		def visit_with_open_check(node, inside_allowed=False):
			nonlocal errors

			if isinstance(node, ast.FunctionDef):
				inside = node.name in ALLOWED_OPEN_FUNCTIONS
				for child in ast.iter_child_nodes(node):
					visit_with_open_check(child, inside_allowed=inside)

			elif isinstance(node, ast.Call):
				func = node.func

				if isinstance(func, ast.Name) and func.id == "open":
					if not inside_allowed:
						errors.append((node.lineno, "[UNAUTHORIZED OPEN] open() used outside allowed functions"))

				elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
					module = alias_map.get(func.value.id, func.value.id)
					full_name = f"{module}.{func.attr}"
					if module == "os" and full_name not in ALLOWED_OS_FUNCTIONS:
						errors.append((node.lineno, f"[RESTRICTED OS USAGE] {full_name} is not allowed"))

				for child in ast.iter_child_nodes(node):
					visit_with_open_check(child, inside_allowed=inside_allowed)

			else:
				for child in ast.iter_child_nodes(node):
					visit_with_open_check(child, inside_allowed=inside_allowed)

		visit_with_open_check(tree)

		if errors:
			for lineno, msg in errors:
				print(f"\033[91m{msg}\033[0m on line {lineno}")
			return True

	except Exception as e:
		print(f"Error analyzing code: {e}")
		return False

	return False



def run_test_on_port(port: int, timeout: int) -> int:
	"""
	Run the DHTTestSuite on a specific port with a timeout and return the final score.
	"""
	try:
		result = subprocess.run(
			[sys.executable, "check.py", str(port)],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			timeout=timeout
		)

		score = result.returncode 
		return score
	except subprocess.TimeoutExpired:
		print(f"Test on port {port} timed out after {timeout} seconds.")
		return 0
	except Exception as e:
		print(f"Error running test on port {port}: {e}")
		return 0


def run_test_on_port_wrapper(port, timeout):
	return run_test_on_port(port, timeout)


def run_tests_on_multiple_ports(start_ports: List[int], timeout: int = 60) -> None:
	"""
	Run the DHTTestSuite on multiple ports using multiprocessing and calculate average score.
	"""
	print("Starting tests on multiple ports using multiprocessing...")
	with Pool(processes=len(start_ports)) as pool:
		results = pool.starmap(run_test_on_port_wrapper, [(port, timeout) for port in start_ports])

	scores = []
	for port, score in zip(start_ports, results):
		print(f"Port {port}: Score = {score}")
		scores.append(score)

	if scores:
		average_score = sum(scores) / len(scores)
		print(f"\nAverage Score across all ports: {average_score:.2f}/40")
	else:
		print("No scores collected. Something might have gone wrong.")


if __name__ == "__main__":
	
	parser = argparse.ArgumentParser(description="Run DHTTestSuite on multiple ports and calculate average score.")
	parser.add_argument('ports', nargs="*", type=int, help="List of ports to run the tests on.", default=[9580, 59580, 28161, 50396, 2765])

	args = parser.parse_args()
	test_ports = args.ports

	if len(test_ports) < 1:
		print("Usage: python run_multiple_tests.py <start_port1> <start_port2> ...")
		sys.exit(0)

	for pattern in ["localhost*", "dummy*", "output*", "test/*"]:
		subprocess.run(f"rm -rf {pattern}", shell=True, check=False)
 
	time.sleep(1)
	
	voilation = analyze_code("DHT.py")
 
	if voilation:
		print("Code contains restricted imports or functions. Skipping tests.")
		print("Final Score: 0/40")
		sys.exit(0)

	run_tests_on_multiple_ports(test_ports)
	subprocess.run(
		"lsof -nP -iTCP -sTCP:LISTEN | grep -i 'python' | awk '{print $2}' | xargs -r kill -9", shell=True, check=False) # just killing all the python processes that are listening on ports. Sorry if you had a python server running lol
