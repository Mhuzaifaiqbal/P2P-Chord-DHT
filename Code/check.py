from DHT import Node
import time
import os
import sys
import uuid
from typing import List
from dataclasses import dataclass, field
import hashlib
import argparse
import logging
import colorlog

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)s - %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
))

logger = colorlog.getLogger(f"logger_{uuid.uuid4()}")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = True

	
@dataclass
class DHTTestSuite:
	start_port: int
	port_list: List[int] = field(init=False)
	test_files: List[str] = field(init=False)
	nodes: List[Node] = field(default_factory=list)
	total_points: int = 0
	file_checksums: dict = field(default_factory=dict)

	def __post_init__(self):
		self.port_list = [self.start_port + i for i in range(5)]
		self.test_files = [
			f"dummy{i}_{self.start_port}.txt" if i != 1 else f"dummy_{self.start_port}.txt"
			for i in range(1, 9)
		]
		os.makedirs("test", exist_ok=True)

	@staticmethod
	def compute_checksum(file_path: str) -> str:
		hasher = hashlib.sha256()
		with open(file_path, "rb") as f:
			while chunk := f.read(8192):
				hasher.update(chunk)
		return hasher.hexdigest()

	@staticmethod
	def print_header(message: str) -> None:
		border = "=" * 50
		magenta = "\033[95m"
		reset = "\033[0m"

		logger.debug(f"{magenta}\n{border}\n{message}\n{border}\n{reset}")

	def generate_files(self, files: List[str]) -> None:
		self.file_checksums.clear()
		for f in files:
			with open(f, "w") as file:
				lowercase_str = uuid.uuid4().hex
				file.write(lowercase_str.upper())
			self.file_checksums[f] = self.compute_checksum(f)

	def check_file_duplication(self) -> bool:
		all_files = [f for node in self.nodes for f in node.files]
		if not all_files:
			logger.error("No files found in the nodes.")
			return False

		evalulation = len(all_files) == len(set(all_files))
		if not evalulation:
			logger.error(
				f"File duplication detected! Here is the list of all stored files across nodes: {all_files}")
			logger.error(
				f"Length of stored files: {len(all_files)} vs. unique files: {len(set(all_files))}")
			logger.error(f"Length of test files: {len(self.test_files)}")
		return evalulation

	def check_extra_files_stored(self) -> bool:
		stored_files = [
			file for node in self.nodes
			for file in os.listdir(f"localhost_{node.port}")
		]
		evaluation = len(stored_files) == 2*len(self.test_files)
		if not evaluation:
			logger.error(f"Extra or missing files detected in your DHT storage.")
			logger.error(f"Your stored files: {stored_files}")
			logger.error(f"Length of stored files: {len(stored_files)}")
			logger.error(f"Length of test files: {len(self.test_files)}")
			logger.error(
				f"Note: Only two copies of each file are expected (file itself and backup) in your entire DHT.")
		return evaluation

	def verify_file_transfer(self) -> bool:
		for node in self.nodes:
			folder_name = f"{node.host}_{node.port}"
			for f in node.files:
				path = os.path.join(folder_name, f)
				if not os.path.exists(path):
					logger.error(f"File {f} missing in {folder_name}.")
					logger.error("Make sure your file transfer logic is correct.")
					return False
				stored_checksum = self.compute_checksum(path)
				if f not in self.file_checksums:
					logger.error(
						f"Unexpected file {f} found in {folder_name}, or missing from checksums.")
					return False
				if self.file_checksums[f] != stored_checksum:
					logger.error(f"Checksum mismatch for {f} in {folder_name}.")
					logger.error(
						f"Expected: {self.file_checksums[f]}, Found: {stored_checksum}")
					return False
		logger.info("File transfer and checksums verified. (+0)") # no mark deduction
		return True

	def check_backup_duplication(self) -> bool:
		all_files = [f for node in self.nodes for f in node.backup_files]
		if not all_files:
			logger.error("No backup files found in the nodes.")
			return False

		logger.debug(f"All backup files are {all_files}")
		for  node in self.nodes:
			for f in node.backup_files:
				logger.debug(f"Node {node.port} has backup file {f}")

		evaluation = len(all_files) == len(set(all_files))
		if not evaluation:
			logger.error(
				f"Backup file duplication detected! Here is the list of all backup files across nodes: {all_files}")
			logger.error(
				f"Length of backup files: {len(all_files)} vs. unique files: {len(set(all_files))}")
			logger.error(f"Length of test files: {len(self.test_files)}")
		return evaluation

	def verify_backup_transfer(self) -> bool:
		for node in self.nodes:
			logger.debug(
				f"Verifying backup files for node with port={node.port}, key={node.key}")
			folder_name = f"{node.host}_{node.port}"
			for f in node.backup_files:
				logger.debug(
					f"Verifying backup file {f} in folder {folder_name}...")
				path = os.path.join(folder_name, f)
				if not os.path.exists(path):
					logger.error(f"Backup file {f} missing in {folder_name}.")
					logger.error(
						"Ensure your backup logic handles all scenarios correctly.")
					return False
				stored_checksum = self.compute_checksum(path)
				if f not in self.file_checksums:
					logger.error(
						f"Unexpected backup file {f} found in {folder_name}, or missing from checksums.")
					return False
				if self.file_checksums[f] != stored_checksum:
					logger.error(
						f"Checksum mismatch for backup file {f} in {folder_name}.")
					logger.error(
						f"Expected: {self.file_checksums[f]}, Found: {stored_checksum}")
					return False
		logger.debug("Backup transfer and checksums verified.")
		return True

	def initiate(self) -> int:
		self.print_header("Testing Initialization")
		points = 0
		try:
			self.nodes = [
				Node("localhost", port) for port in self.port_list
			]
			logger.debug("Nodes created for testing:")
			for node in self.nodes:
				logger.debug(
					f"Node: Host={node.host}, Port={node.port}, Key={node.key}"
				)

			logger.info("Nodes initialized successfully.")
		except Exception as e:
			logger.error(f"Error during node initialization: {e}")
			return points

		single_node = self.nodes[0]
		# Expect single node's successor and predecessor to be itself
		expected_successor = ("localhost", self.port_list[0])
		expected_predecessor = ("localhost", self.port_list[0])

		if single_node.successor == expected_successor and single_node.predecessor == expected_predecessor:
			logger.info("Single node successor/predecessor check passed. (+1)")
			points += 1
		else:
			logger.error("Single node successor/predecessor check failed.")
			logger.error(
				f"Expected successor: {expected_successor}, Found: {single_node.successor}"
			)
			logger.error(
				f"Expected predecessor: {expected_predecessor}, Found: {single_node.predecessor}"
			)

		logger.debug(f"Initialization testing completed. Points: {points}/1")
		return points

	def test_join(self) -> int:
		self.print_header("Testing Join")
		points = 0

		# Case 1: Single node join
		self.nodes[0].join("")
		time.sleep(2)
		expected_succ_pred = ("localhost", self.port_list[0])
		if (
			self.nodes[0].successor == expected_succ_pred
			and self.nodes[0].predecessor == expected_succ_pred
		):
			logger.info("Case 1 (single node join) passed. (+1)")
			points += 1
		else:
			logger.error("Case 1 (single node join) failed.")
			logger.error(
				f"Expected successor/predecessor: {expected_succ_pred}, "
				f"Found successor: {self.nodes[0].successor}, "
				f"Found predecessor: {self.nodes[0].predecessor}"
			)

		# Case 2: Two-node join
		self.nodes[1].join(("localhost", self.port_list[0]))
		time.sleep(2)
		# Here we expect:
		#   - Node1 successor = Node0, predecessor = Node0
		#   - Node0 successor = Node1, predecessor = Node1
		case2_pass = (
			self.nodes[1].successor == ("localhost", self.port_list[0])
			and self.nodes[1].predecessor == ("localhost", self.port_list[0])
			and self.nodes[0].successor == ("localhost", self.port_list[1])
			and self.nodes[0].predecessor == ("localhost", self.port_list[1])
		)
		if case2_pass:
			logger.info("Case 2 (two-node join) passed. (+3)")
			points += 3
		else:
			logger.error("Case 2 (two-node join) failed.")
			logger.error("Detailed mismatch info:")
			logger.error(
				f"Node0 successor expected: ('localhost', {self.port_list[1]}), found: {self.nodes[0].successor}"
			)
			logger.error(
				f"Node0 predecessor expected: ('localhost', {self.port_list[1]}), found: {self.nodes[0].predecessor}"
			)
			logger.error(
				f"Node1 successor expected: ('localhost', {self.port_list[0]}), found: {self.nodes[1].successor}"
			)
			logger.error(
				f"Node1 predecessor expected: ('localhost', {self.port_list[0]}), found: {self.nodes[1].predecessor}"
			)

		# Case 3: General case
		for i in range(2, 5):
			self.nodes[i].join(("localhost", self.port_list[0]))
			time.sleep(2)

		self.nodes.sort(key=lambda x: x.key)
		correct = True
		for i in range(len(self.nodes)):
			expected_successor = self.nodes[(i + 1) % len(self.nodes)].port
			expected_predecessor = self.nodes[i - 1].port
			found_successor = self.nodes[i].successor[1]
			found_predecessor = self.nodes[i].predecessor[1]
			if not (found_successor == expected_successor and found_predecessor == expected_predecessor):
				correct = False
				logger.error(
					f"Mismatch in Case 3 (general join) for node with port {self.nodes[i].port}"
				)
				logger.error(
					f"Expected successor: {expected_successor}, Found: {found_successor}"
				)
				logger.error(
					f"Expected predecessor: {expected_predecessor}, Found: {found_predecessor}"
				)

		if correct:
			logger.info("Case 3 (general case) passed. (+5)")
			points += 5
		else:
			logger.error("Case 3 (general case) failed.")

		logger.debug(f"Join testing completed. Points: {points}/9")
		return points

	def test_put_and_get(self) -> int:
		self.print_header("Testing Put and Get")
		points = 0

		for file in self.test_files:
			self.nodes[0].put(file)
		time.sleep(1)
		logger.debug(
			"Files placed on DHT. Verifying correctness of put operation...")

		correct_put = True
		for file in self.test_files:
			file = file.split("/")[-1]
			hashed_key = self.nodes[0].hasher(file)
			assigned_node = next(
				(node for node in self.nodes if hashed_key <= node.key or (
					hashed_key > self.nodes[-1].key and node == self.nodes[0])),
				None
			)
			if assigned_node and file not in assigned_node.files:
				logger.error(
					f"File {file} not found in the assigned node's storage. "
					f"Assigned node port: {assigned_node.port} (key={assigned_node.key}), hashed_key={hashed_key}."
				)
				correct_put = False

		if correct_put and self.check_file_duplication() and self.verify_file_transfer():
			logger.info("Put operation verified successfully. (+7)")
			points += 7
		else:
			logger.error("Put operation verification failed.")

		logger.debug("Attempting to get an absent file: 'absent.txt'...")
		if not self.nodes[0].get("absent.txt"):
			logger.info("Node correctly returned False for a non-existent file.")
			logger.debug(f"Attempting to get an existing file: {self.test_files[0]}...")

			for i in range(0, 3):
				if self.nodes[i].get(self.test_files[i]):
					logger.debug(f"Checking test directory for file: {self.test_files[i]}")
					if os.path.exists(os.path.join("test", self.test_files[i])):

						logger.info("Get operation verified successfully. (+3)")
						points += 1
					else:
						logger.error("Get operation failed: file not physically stored.")
				else:
					logger.error("Get operation failed: file not retrieved.")

		else:
			logger.error("Get operation failed: retrieved a non-existent file.")

		logger.debug(f"Put and Get testing completed. Points: {points}/10")
		return points

	def test_file_rehashing(self, sp: int) -> int:
		self.print_header("Testing File Rehashing")
		points = 0

		new_ports = [sp + i for i in range(3)]
		new_nodes = [Node("localhost", port) for port in new_ports]
		for node in new_nodes:
			node.join(("localhost", self.port_list[0]))
			self.nodes.append(node)
			time.sleep(2)
		self.nodes.sort(key=lambda x: x.key)

		logger.debug(
			"Verifying that files are rehashed correctly and moved to the right nodes after ring expansion...")
		correct_rehash = True
		for file in self.test_files:
			hashed_key = self.nodes[0].hasher(file)
			assigned_node = next(
				(node for node in self.nodes if hashed_key <= node.key or (
					hashed_key > self.nodes[-1].key and node == self.nodes[0])),
				None
			)
			if assigned_node and file not in assigned_node.files:
				logger.error(
					f"File {file} not found in the assigned node's storage after rehashing. "
					f"Assigned node port: {assigned_node.port} (key={assigned_node.key}), hashed_key={hashed_key}."
				)
				correct_rehash = False

		if correct_rehash and self.check_file_duplication() and self.verify_file_transfer():
			logger.info("File rehashing verified successfully. (+5)")
			points += 5
		else:
			logger.error("File rehashing verification failed.")

		logger.debug(f"File Rehashing testing completed. Points: {points}/5")
		return points

	def test_leave(self) -> int:
		self.print_header("Testing Leave")
		points = 0

		leave_node = self.nodes.pop(0)
		logger.debug(
			f"Node leaving: port={leave_node.port}, key={leave_node.key}")
		leave_node.leave()
		time.sleep(1)

		correct = True
		for i, node in enumerate(self.nodes):
			expected_successor = self.nodes[(i + 1) % len(self.nodes)].port
			expected_predecessor = self.nodes[i - 1].port
			found_successor = node.successor[1]
			found_predecessor = node.predecessor[1]
			if not (found_successor == expected_successor and found_predecessor == expected_predecessor):
				correct = False
				logger.error(
					f"Mismatch in successor/predecessor after node leave for node with port {node.port}"
				)
				logger.error(
					f"Expected successor: {expected_successor}, Found: {found_successor}"
				)
				logger.error(
					f"Expected predecessor: {expected_predecessor}, Found: {found_predecessor}"
				)

		if correct and self.check_file_duplication() and self.verify_file_transfer():
			logger.info("Leave operation verified successfully. (+5)")
			points += 5
		else:
			logger.error("Leave operation verification failed.")

		logger.debug(f"Leave testing completed. Points: {points}/5")
		return points

	def test_failure_tolerance(self) -> int:
		self.print_header("Testing Failure Tolerance")
		points = 0

		logger.debug("\nVerifying backup storage BEFORE killing a node...")
		if self.check_backup_duplication() and self.verify_backup_transfer():
			logger.info(
				"Before killing node, backup storage verified successfully. (+2)")
			points += 2
		else:
			logger.error(
				"Before killing the node, backup storage verification failed.")

		failed_node = self.nodes.pop(0)
		logger.debug(
			f"\nKilling node with port={failed_node.port}, key={failed_node.key}\n")
		failed_node.kill()
		time.sleep(3)

		correct = True
		for i, node in enumerate(self.nodes):
			expected_successor = self.nodes[(i + 1) % len(self.nodes)].port
			expected_predecessor = self.nodes[i - 1].port
			found_successor = node.successor[1]
			found_predecessor = node.predecessor[1]
			if not (found_successor == expected_successor and found_predecessor == expected_predecessor):
				correct = False
				logger.error(
					f"Mismatch in successor/predecessor after node kill for node with port {node.port}"
				)
				logger.error(
					f"Expected successor: {expected_successor}, Found: {found_successor}"
				)
				logger.error(
					f"Expected predecessor: {expected_predecessor}, Found: {found_predecessor}"
				)

		if correct and self.check_file_duplication() and self.verify_file_transfer():
			logger.info("Failure tolerance verified successfully. (+6)")
			points += 6
		else:
			logger.error("Failure tolerance verification failed.")

		logger.debug("\nVerifying backup storage AFTER killing a node...")
		if self.check_backup_duplication() and self.verify_backup_transfer():
			logger.info(
				"After killing node, backup storage verified successfully. (+2)")
			points += 2
		else:
			logger.error(
				"After killing the node, backup storage verification failed.")

		return points

	def stop_all_threads(self) -> None:
		"""Signal all threads to stop and wait for them to finish."""
		logger.debug("Stopping all nodes/threads gracefully...")
		for node in self.nodes:
			node.kill()
		time.sleep(1)

	def run_tests(self) -> None:
		try:
			logger.debug("Starting DHT Test Suite...")
			points = 0

			points += self.initiate()
			points += self.test_join()

			self.generate_files(self.test_files)
			points += self.test_put_and_get()
			points += self.test_file_rehashing(self.start_port + 5)
			points += self.test_leave()
			points += self.test_failure_tolerance()

			if not self.check_extra_files_stored():
				logger.error(
					"Extra files stored in DHT. There should not be more than two copies of a file "
					"(the file itself and its backup) anywhere in the ring. (-10)"
				)
				points -= 10

			logger.info(f"Final Score: {points}/40")

		except Exception as e:
			logger.critical(f"Error during tests: {e}")
		finally:
			self.stop_all_threads()
			return points

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Run DHTTestSuite on multiple ports and calculate average score.")
	parser.add_argument('port', type=int,
						help="A port to run the tests on.")
	args = parser.parse_args()
	port = args.port
	
	if port and 1005 < port < 65500:
		try:
			file_handler = logging.FileHandler(f"output_{port}.log", mode="w")
			file_handler.setLevel(logging.DEBUG)
			logger.addHandler(file_handler)
			test_suite = DHTTestSuite(port)
			score = test_suite.run_tests()
			sys.exit(score)
		except Exception as e:
			logger.critical("Exception occured ", e)
		sys.exit(0)
	else:
		logger.critical("Specify one port number between 1005 and 65500 to run the test suite on.")
		