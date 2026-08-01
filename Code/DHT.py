import socket
import threading
import os
import time
import hashlib


class Node:
	def __init__(self, host, port):
		self.stop = False
		self.host = host
		self.port = port
		self.M = 16
		self.N = 2**self.M
		self.key = self.hasher(host+str(port))
		# You will need to kill this thread when leaving, to do so just set self.stop = True
		threading.Thread(target=self.listener, daemon=True).start()
		self.files = []
		self.backup_files = []
		os.makedirs(f"./{self.host}_{self.port}", exist_ok=True)

		'''
		------------------------------------------------------------------------------------
		DO NOT EDIT ANYTHING ABOVE THIS LINE
		'''
		# Set value of the following variables appropriately to pass Intialization test
		self.successor = None
		self.predecessor = None
		# additional state variables

	def hasher(self, key):
		'''
		DO NOT EDIT THIS FUNCTION.
		You can use this function as follow:
				For a node: self.hasher(node.host+str(node.port))
				For a file: self.hasher(file)
		'''
		return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N

	def handle_connection(self, client, addr):
		'''
		 Function to handle each inbound connection, called as a thread from the listener.
		'''

	def listener(self):
		"""
		This method listens for inbound connections on self.host:self.port.
		It uses a context manager to ensure the socket is automatically closed
		when exiting the 'with' block. For each inbound connection, it spawns a new thread
		"""
		# Using a 'with' statement to handle the socket context
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_socket:
			srv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			srv_socket.bind((self.host, self.port))
			srv_socket.listen(10)
			srv_socket.settimeout(1)

			while not self.stop:
				try:
					client, addr = srv_socket.accept()
					threading.Thread(
						target=self.handle_connection,
						args=(client, addr),
						daemon=True
					).start()
				except socket.timeout:
					# Timeout allows us to periodically check the stop condition
					continue
				except OSError as e:
					print(f"[ERROR] Listener socket error: {e}")
					break

		print("Shutting down node:", self.host, self.port)

	def join(self, joining_addr):
		'''
		This function handles the logic of a node joining. This function should do a lot of things such as:
		Update successor, predecessor, getting files, back up files. SEE MANUAL FOR DETAILS.
		'''

	def put(self, file_name):
		'''
		This function should first find node responsible for the file given by file_name, then send the
		file over the socket to that node Responsible node should then replicate the file on appropriate node. 
		SEE MANUAL FOR DETAILS. Responsible node should save the files
		in directory given by host_port e.g. "localhost_20007/file.py".
		'''

	def get(self, file_name):
		'''
		This function finds node responsible for file given by file_name, gets the file from responsible node, 
		saves it in "test" directory i.e. "./test/file.py" and returns the name of file. If the file is not 
		present on the network, return None.
				'''

	def leave(self):
		'''
		When called leave, a node should gracefully leave the network i.e. it should update its predecessor 
		that it is leaving it should send its share of file to the new responsible node, close all the threads
		and leave. You can close listener thread by setting self.stop flag to True
		'''

	def send_file(self, soc, file_name):
		''' 
		Utility function to send a file over a socket
				Arguments:	soc => a socket object
										file_name => file's name including its path e.g. NetCen/PA3/file.py
		'''
		file_size = os.path.getsize(file_name)
		soc.send(str(file_size).encode('utf-8'))
		soc.recv(1024).decode('utf-8')
		with open(file_name, "rb") as file:
			content_chunk = file.read(1024)
			while content_chunk != "".encode('utf-8'):
				soc.send(content_chunk)
				content_chunk = file.read(1024)

	def recieve_file(self, soc, file_name):
		'''
		Utility function to recieve a file over a socket
				Arguments:	soc => a socket object
										file_name => file's name including its path e.g. NetCen/PA3/file.py
		'''
		file_size = int(soc.recv(1024).decode('utf-8'))
		soc.send("ok".encode('utf-8'))
		content_recieved = 0
		file = open(file_name, "wb")
		while content_recieved < file_size:
			content_chunk = soc.recv(1024)
			content_recieved += len(content_chunk)
			file.write(content_chunk)
		file.close()

	def kill(self):
		# DO NOT EDIT THIS, used for code testing
		self.stop = True