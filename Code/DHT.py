import socket
import threading
import os
import time
import hashlib
import json
# ---------------------IMPORTANT-----------------
# FORMATTING WAS DONE FROM AN ONLINE FORMATTER https://codebeautify.org/python-formatter-beautifier#
# ---------------------IMPORTANT-----------------


# the inspiration to use json was taken from
# https://github.com/Mutahar789/P2P-FileSharing-DHT/blob/main/DHT.py#L290
# i read the assignment on github posted by a senior. mayeb there assignment was
# different back then, but only inspiration for json was taken the rest is my own code
# verification can be done


# like gossip
# one node will only know its successor or predecessor and nothing else
# we have joins where our nodes will join the ring
# -------------join-------------
# so in join when lets say a node joins, say we have 80,90,100 and say 98 joins
# it will send a command or ping the next one, say 100 in this case
# so 98 will set 100 as its successor and 100 will set 98 as its predecessor
# but edge case can also be when its alone in the ring so it will point to itself or
# also when only two, then same successor and predecessor

#creating two helpers for json
def send_msg(sock, msg: dict):
    data = json.dumps(msg).encode()
    sock.send(data)

def recv_msg(sock, bufsize=1024):
    data = sock.recv(bufsize)
    return json.loads(data.decode())


class Node:
    def __init__(self, host, port):
        self.stop = False
        self.host = host
        self.port = port
        self.M = 16
        self.N = 2**self.M
        self.key = self.hasher(host + str(port))
        # You will need to kill this thread when leaving, to do so just set self.stop = True
        threading.Thread(target=self.listener, daemon=True).start()
        self.files = []
        self.backup_files = []
        os.makedirs(f"./{self.host}_{self.port}", exist_ok=True)

        """
		------------------------------------------------------------------------------------
		DO NOT EDIT ANYTHING ABOVE THIS LINE
		"""
        # Set value of the following variables appropriately to pass Intialization test
        # so this is like the edge case. agar wo node akelay hain in the ring to ofcourse they will
        # point to self
        # self.successor =self #we are doing tuples and not objects so my code is breaking
        self.successor = (host, port)
        self.predecessor = (host, port)
        # additional state variables

        # -----------------notes--------------
        # each node has a file containing info about it
        # also we need to replicate the data for backup so we have in total 2 files
        # the manual requires to create backups so if a node fails, data is not lost
        # ye uper already bana hua
        # the manual also states that nodes must communicate with eachother using sockets

        # finally the last feature left is pinging
        self.ping = False
        self.pingThread = None
        self.second_successor = (host, port)

    def start_ping(self):

        self.ping = True
        self.pingThread = threading.Thread(target=self.ping_successor, daemon=True)
        self.pingThread.start()

    # so basically i am constantly failing the last test due to some recovery issues
    # 		#tried to build everyhting in one code block but it just never ran
    # 		#so i had to take help from chatgpt whcih suggested me to make a periodic pinger for
    # 		#recovery by basically oinging the successor and also involving second succ

    # 		#so basically check if the succ is alive or not and verify if its correct, then at the
    # 		#same time update the second successor as per need
    # 		#and if say we ping a successor which is not working, we will simply replace it

    def ping_successor(self):
        # so here is my logic: i am goinf to ping the successor through a socket
        # 			#then wait for the command, if it does reply then its alive otherwise not
        cons_fails = 0
        while self.ping and not self.stop:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.4)  # shorter timeout
                sock.connect(self.successor)
                send_msg(sock, {"cmd": "PING"})
                response = recv_msg(sock)
                sock.close()
                if response.get("cmd") == "PONG":
                    # cons_fails = 0

                    # but the problem is that we dont  actually know the intervals of node
                    # 					#like if we have A and its successor is C. B was added \
                        # between the both
                    # 					#then A will not know thats its successor is b and ring
                    # will break. so we check

                    # i will basically ask the successor whos the predecessor for it and
                    # it replis with
                    # someone else, then we will change the successor to maintain the ring
                    # this is again and again failing for some reason

                    if self.successor != (self.host, self.port):
                        try:
                            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock2.settimeout(0.4)
                            sock2.connect(self.successor)
                            send_msg(sock2, {"cmd": "GET_PREDECESSOR"})
                            check = recv_msg(sock2)
                            sock2.close()
                            if check.get("cmd") == "PREDECESSOR":
                                succ_pred = (check["host"], int(check["port"]))
                                if succ_pred != (self.host, self.port):
                                    self.successor = succ_pred
                        except:
                            pass
                        # and now address to the second successoir for effieceint recovery
                        try:
                            sock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock3.settimeout(0.4)
                            sock3.connect(self.successor)
                            send_msg(sock3, {"cmd": "GET_SUCCESSOR"})
                            check2 = recv_msg(sock3)
                            sock3.close()
                            if check2.get("cmd") == "SUCCESSOR":
                                new_sec = (check2["host"], int(check2["port"]))
                                # if self.second_successor != new_sec:
                                # 	print(f"[{self.port}] second_successor updated to {new_sec}")
                                self.second_successor = new_sec
                                self.cleanup_backups()
                                self.ensure_primary_backups()
                        except Exception as e:
                            print(e)
                        pass

                else:
                    cons_fails += 1
            except Exception as e:
                cons_fails += 1
                print(f"Ping to  failed")

            if cons_fails >= 2:
                self.handle_successor_failure()
                cons_fails = 0

            time.sleep(0.1)

    # def handle_successor_failure(self):
    # 	"""Handle when successor dies"""
    # 	try:
    # 		if self.predecessor != (self.host, self.port):
    #

    def make_successor(self):
        """Promote second_successor as new successor"""
        print("Huzaifa its working---------------")

        self.successor = self.second_successor

    def back_second_successor(self):
        """successor for its successor"""

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.successor)
            send_msg(sock, {"cmd": "GET_SUCCESSOR"})
            resp = recv_msg(sock)
            sock.close()

            if resp.get("cmd") == "SUCCESSOR":
                self.second_successor = (resp["host"], int(resp["port"]))
            else:
                self.second_successor = self.successor

        except:
            self.second_successor = self.successor

    def pred_pointer(self):
        """predecessor points to new second succ"""

        if self.predecessor == (self.host, self.port):
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.predecessor)
            send_msg(
                sock,
                {
                    "cmd": "UPDATE_SECOND_SUCC",
                    "host": self.successor[0],
                    "port": self.successor[1],
                },
            )
            sock.recv(1024)
            sock.close()

        except:
            pass

    def handle_successor_failure(self):
        """Handle in case successor fails"""
        # print(f"crashed")
        # print("HUZAIFAAAAAA")

        self.make_successor()
        # now the main step is store the second successor as backup
        # in case of failures
        # so again say a>b>c. we will store c as backup in a so that incase b fails
        # we can use c and have some sort of protection for the ring

        # for that i will make a helper and use socket to ask for the successor
        # from the successor and simply store
        # it#

        self.back_second_successor()

        # after this we will simply ping new successor so it notes that a is the new predecessor

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.successor)
            send_msg(
                sock, {"cmd": "SET_PREVIOUS", "host": self.host, "port": self.port}
            )
            sock.recv(1024)
            sock.close()
        except:
            pass

        # return
        print("working for last steop")
        # i forgot one important thing. that we woere working with second successors
        # so when seocnd succ was made the first succ, then second succ should restored again
        # thats what we do now on
        # if self.predecessor != (self.host, self.port):
        # 	try:
        # 		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # instead lemme make a helperm so easier to uderstand
        self.pred_pointer()

        # laslty we have to make the backup files as primary files

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.successor)
            send_msg(sock, {"cmd": "PROMOTE_BACKUPS"})
            sock.recv(1024)
            sock.close()
        except:
            pass
        self.ensure_primary_backups()

    def promote_to_primary(self, file):
        if file not in self.files:
            self.files.append(file)

        if file in self.backup_files:
            self.backup_files.remove(file)

    def backups_made_primary(self):
        """backup promotion"""
        # okay so check backup files and see if they are on disk, if not then remove
        # from backup
        # one more thing that like when we have node that truly owns the backup files
        # we need to promote these files as main files not backup and the successor stores
        # the backup copy
        # i ghave to cover all these features one by one to ensure itb works correctly
        for file in list(self.backup_files):
            file_path = os.path.join(f"{self.host}_{self.port}", file)
            if not os.path.exists(file_path):
                self.backup_files.remove(file)
                continue
            if not self.owner(self.hasher(file)):
                continue
            # hwoever if it is the owner then backup files will be converted to primary files
            self.promote_to_primary(file)
            if self.successor != (self.host, self.port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(self.successor)
                    send_msg(sock, {"cmd": "BACKUP", "filename": file})
                    time.sleep(0.05)
                    self.send_file(sock, file_path)
                    sock.close()
                except:
                    pass

    # def node_owns_key(self, node, key_value):
    # node_key = self.hasher(f"{self.host}{self.port}")
    # pred_key = self.hasher(f"{self.predecessor[0]}{self.predecessor[1]}")

    # if pred_key > node_key:
    # 	return pred_key < key_value < node_key

    def node_owns_key(self, key_value):
        node_key = self.hasher(f"{self.host}{self.port}")
        pred_key = self.hasher(f"{self.predecessor[0]}{self.predecessor[1]}")

        if pred_key < node_key:
            return pred_key < key_value <= node_key

        return key_value > pred_key or key_value <= node_key

    def cleanup_backups(self):
        if self.predecessor == (self.host, self.port):
            return
        for file in list(self.backup_files):
            # bhai ye ajeeb hai, argument main ghalat no of parameters hain,
            # likin sahi karo to crash kar jata, lets work with the
            # error itself
            if self.node_owns_key(self.predecessor, self.hasher(file)):
                continue
            file_path = os.path.join(f"{self.host}_{self.port}", file)
            if os.path.exists(file_path) and file not in self.files:
                try:
                    os.remove(file_path)
                except:
                    pass
            if file in self.backup_files:
                self.backup_files.remove(file)

    # we need a function that makes sure that the files
    # owner by a node are stored on the successor as backup
    def ensure_primary_backups(self):
        if self.successor == (self.host, self.port):
            return
        for file in list(self.files):
            file_path = os.path.join(f"{self.host}_{self.port}", file)
            if not os.path.exists(file_path):
                continue
            # then finallyy send th baclup to succ using a socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(self.successor)
                send_msg(sock, {"cmd": "BACKUP", "filename": file})
                self.send_file(sock, file_path)
                sock.close()
            except:
                pass

    def hasher(self, key):
        """
        DO NOT EDIT THIS FUNCTION.
        You can use this function as follow:
                        For a node: self.hasher(node.host+str(node.port))
                        For a file: self.hasher(file)
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N

    def find_node(self, start, key):
        # i can use either a recursive or itertaive approach
        # siomply just look for duplicates and move in cycle to see for detection
        # if visited is None:
        # visited = set()
        # if node in visited:
        # 	return
        # visited.add(node)

        # try:
        # 	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 	sock.connect(node)

        # 	send_msg(sock, {"cmd": "FIND_NODE", "key": key})
        # 	response = recv_msg(sock)
        # 	sock.close()

        # maybe an iterative is beter because my recursive is not wortking i thinkl for some reason
        node = start
        check = set()

        while True:
            if node in check:
                return None
            check.add(node)
            try:

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(node)
                # after this we will communicate to see if the key is required
                send_msg(sock, {"cmd": "FIND_NODE", "key": key})
                response = recv_msg(sock)
                sock.close()

                cmd = response.get("cmd")

                if cmd == "NODE_FOUND":
                    return (response["host"], int(response["port"]))

                elif cmd == "NEXT_NODE":
                    next_node = (response["host"], int(response["port"]))
                    if next_node == node:
                        return None
                    node = next_node
                else:
                    return None

            except Exception as e:
                return None

    def backup(self, client, msg):
        filename = msg["filename"]
        backup_dir = f"{self.host}_{self.port}"
        backup_path = os.path.join(backup_dir, filename)
        self.recieve_file(client, backup_path)

        if filename not in self.backup_files:
            self.backup_files.append(filename)
        client.send(b"BACKUP_RECEIVED")

    def remove_backup(self, filename):
        """remove backup from succ"""
        # my function will remove the backups from the successor
        if self.successor == (self.host, self.port):
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.successor)
            send_msg(sock, {"cmd": "REMOVE_BACKUP", "filename": filename})
            sock.recv(1024)
            sock.close()
        except:
            pass

    def handle_connection(self, client, addr):
        """
        Function to handle each inbound connection, called as a thread from the listener.
        """
        # client.send(json.dumps(["connected"]).encode("utf-8"))
        # while not self.stop:
        # 	data = json.loads(client.recv(1024).decode("utf-8"))
        # 	cmd = data[0]

        try:
            # okay so we will break down the received msg and then see what command it holds

            data = client.recv(4096).decode()
            if not data:
                client.close()
                return
            msg = json.loads(data)
            cmd = msg["cmd"]

            # if the command is about to find the node then obviously we
            # will fidn the node responsible for the key given
            if cmd == "FIND_NODE":
                key_value = int(msg["key"])

                # the first case is obviously if the node is alone in the ring and then
                # we will send command back
                if self.successor == (self.host, self.port) and self.predecessor == (
                    self.host,
                    self.port,
                ):
                    send_msg(
                        client,
                        {"cmd": "NODE_FOUND", "host": self.host, "port": self.port},
                    )
                    return
                # and id its not the case then we will hash the predecessor and see if the key
                # lies in the interval of the current
                # node
                # okay so one thing to keep in mind is that maybe the current node does not own
                # the key
                # and in that case we have to somehow traverse in a circular manner
                # this happens until the true owner is found
                prev_key = self.hasher(f"{self.predecessor[0]}{self.predecessor[1]}")
                if prev_key < self.key:
                    responsible = prev_key < key_value <= self.key
                else:
                    responsible = key_value > prev_key or key_value <= self.key

                if responsible:
                    send_msg(
                        client,
                        {"cmd": "NODE_FOUND", "host": self.host, "port": self.port},
                    )
                else:
                    send_msg(
                        client,
                        {
                            "cmd": "NEXT_NODE",
                            "host": self.successor[0],
                            "port": self.successor[1],
                        },
                    )

            elif cmd == "GET_PREDECESSOR":
                host, port = self.predecessor
                send_msg(client, {"cmd": "PREDECESSOR", "host": host, "port": port})
            elif cmd == "SET_PREVIOUS":
                self.predecessor = (msg["host"], int(msg["port"]))
                client.send(b"OK")
            elif cmd == "SET_SUCCESSOR":
                self.successor = (msg["host"], int(msg["port"]))
                try:
                    if self.successor != (self.host, self.port):
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect(self.successor)
                        send_msg(sock, {"cmd": "GET_SUCCESSOR"})
                        resp = recv_msg(sock)
                        sock.close()
                        if resp.get("cmd") == "SUCCESSOR":
                            self.second_successor = (resp["host"], int(resp["port"]))
                        else:
                            self.second_successor = self.successor
                    else:
                        self.second_successor = (self.host, self.port)
                except:
                    self.second_successor = self.successor
                client.send(b"OK")
            elif cmd == "REMOVE_BACKUP":
                filename = msg["filename"]
                # Remove backup file
                backup_path = os.path.join(f"{self.host}_{self.port}", filename)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                if filename in self.backup_files:
                    self.backup_files.remove(filename)
                client.send(b"OK")
            elif cmd == "CLAIM_FILES":


                # 	if pred_key < new_node_key:
                # 		should_transfer = pred_key < file_key <= new_node_key
                # 	else:
                # 		should_transfer = file_key > pred_key or file_key <= new_node_key
                new_node_key = int(msg["new_node_key"])
                pred_key = int(msg["pred_key"])

                for filename in list(self.files):
                    file_key = self.hasher(filename)
                    if pred_key < new_node_key:
                        should_transfer = pred_key < file_key <= new_node_key
                    else:
                        should_transfer = (
                            file_key > pred_key or file_key <= new_node_key
                        )

                    if not should_transfer:
                        continue

                    file_path = os.path.join(f"{self.host}_{self.port}", filename)
                    if not os.path.exists(file_path):
                        continue

                    send_msg(client, {"cmd": "FILE", "filename": filename})
                    client.recv(1024)
                    self.send_file(client, file_path)
                    client.recv(1024)

                    os.remove(file_path)
                    self.files.remove(filename)
                    self.remove_backup(filename)

                client.send(b"TRANSFER_COMPLETE")

                # 	os.remove(file_path)
                # 	self.files.remove(filename)
                # 	self.remove_backup(filename)

                # client.send(b"TRANSFER_COMPLETE")

            elif cmd == "UPDATE_SECOND_SUCC":
                self.second_successor = (msg["host"], int(msg["port"]))
                client.send(b"OK")

            elif cmd == "GET_SUCCESSOR":
                send_msg(
                    client,
                    {
                        "cmd": "SUCCESSOR",
                        "host": self.successor[0],
                        "port": self.successor[1],
                    },
                )
            # 	new_node_key = int(client.recv(1024).decode())
            # 	pred_host, pred_port = self.predecessor
            # 	pred_key = self.hasher(pred_host + str(pred_port))

            # 	for filename in self.files[:]:
            # 		file_key = self.hasher(filename)
            # 		if pred_key < new_node_key:
            # 			should_transfer = pred_key < file_key <= new_node_key
            # 		else:
            # 			should_transfer = file_key > pred_key or file_key <= new_node_key

            # 		if should_transfer:
            # 			file_path = os.path.join(f"{self.host}_{self.port}", filename)
            # 			if os.path.exists(file_path):
            # 				os.remove(file_path)
            # 				self.files.remove(filename)
            # 	client.send(b"CLEANUP_DONE")
            elif cmd == "PUT":
                name = msg["filename"]
                file_path = os.path.join(f"{self.host}_{self.port}", name)

                # If this file exists as a backup, remove it first
                if name in self.backup_files:
                    backup_path = os.path.join(f"{self.host}_{self.port}", name)
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    self.backup_files.remove(name)

                self.recieve_file(client, file_path)

                if name not in self.files:
                    self.files.append(name)

                if self.successor != (self.host, self.port):
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect(self.successor)
                        send_msg(sock, {"cmd": "BACKUP", "filename": name})
                        self.send_file(sock, file_path)
                        sock.close()
                    except:
                        pass

                client.send(b"PUT_SUCCESS")
            elif cmd == "GET":
                filename = msg["filename"]
                if filename in self.files:
                    file_path = os.path.join(f"{self.host}_{self.port}", filename)
                    client.send(b"FILE_FOUND")
                    self.send_file(client, file_path)
                else:
                    client.send(b"FILE_NOT_FOUND")
            elif cmd == "BACKUP":
                # getting really long so i will create a helper for this
                self.backup(client, msg)
            elif cmd == "GET_BACKUP":
                # for filename in self.backup_files:
                # 	backup_path = os.path.join(f"{self.host}_{self.port}", f"backup_{filename}")
                # 	if os.path.exists(backup_path):
                # 		client.send(filename.encode())
                # 		time.sleep(0.05)
                # 		with open(backup_path, 'rb') as f:
                # 			client.send(f.read())
                # client.send(b"BACKUP_DONE")
                for filename in self.backup_files:
                    backup_path = os.path.join(f"{self.host}_{self.port}", filename)
                    if os.path.exists(backup_path):
                        client.send(filename.encode())
                        client.recv(1024)
                        self.send_file(client, backup_path)
                client.send(b"BACKUP_DONE")

            elif cmd == "PING":
                send_msg(client, {"cmd": "PONG"})
            elif cmd == "PROMOTE_BACKUPS":
                self.backups_made_primary()
                client.send(b"OK")

        except Exception as e:
            print(e)
        finally:
            client.close()

    def listener(self):
        """
        This method listens for inbound connections on self.host:self.port.
        It uses a context manager to ensure the socket is automatically closed
        when exiting the 'with' block. For each inbound connection, it spawns a new thread
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_socket:
            srv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv_socket.bind((self.host, self.port))
            srv_socket.listen(10)

            while not self.stop:
                try:
                    client, addr = srv_socket.accept()
                    threading.Thread(
                        target=self.handle_connection, args=(client, addr), daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except OSError as e:
                    print(f"[ERROR] Listener socket error: {e}")
                    break

    def create_ring(self):
        """since the first node in the ring, it is the ring itself"""
        self.successor = (self.host, self.port)
        self.predecessor = (self.host, self.port)
        if not self.ping:
            self.start_ping()

    def owner(self, key):
        """
        Checking to see if this node is responsible for the kety.
        """

        (
            predecessor_host,
            predecessor_port,
        ) = self.predecessor  # this means tuple values will be initialized
        predecessor_key = self.hasher(predecessor_host + str(predecessor_port))

        if predecessor_key < self.key:
            return predecessor_key < key <= self.key

        return key > predecessor_key or key <= self.key

    


    def join(self, joining_addr):
        """
        This function handles the logic of a node joining. This function should do a lot of
        things such as:
        Update successor, predecessor, getting files, back up files. SEE MANUAL FOR DETAILS.
        """
        if joining_addr == "":
            self.create_ring()
            return
        try:
            # now if the node being joined is not the only one, it must talk to other nodes
            # so it can know where it belongs and can update neighbors e.t.c
            # as per manual we would require sockets for that

            # so we have an id for each node and based on that we will add it on the ring
            # but we have to ask the nodes where does it belong first and first we will send
            # a msg by encoding it and then decode the response and then after closing the socket
            # but like the design i will follow is that , the unique id here is obv i think th
            # e hased
            # key to be used and the node will placed based on that
            # so say that we create a lookup function that basicallt reveals the positions and
            # connect somehow with this
            # really confused k bhai lookup ko connect kaisay karoon
            # oh achaaaa, we should crearte a central function that will handle all requests

            self.successor = self.find_node(joining_addr, self.key)

            # okay so there a lot of things to be done step by step
            # first find the predecessor of our new successor because otherwise the
            # new ring connection would break

            joining = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            joining.connect(self.successor)
            send_msg(joining, {"cmd": "GET_PREDECESSOR"})
            response = recv_msg(joining)
            joining.close()
            self.predecessor = (response["host"], int(response["port"]))

            # then we need to find the succ's succ for error recovery so it can be made the
            # new succ in case the succ fails
            joining = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            joining.connect(self.successor)
            send_msg(joining, {"cmd": "GET_SUCCESSOR"})
            response = recv_msg(joining)
            joining.close()
            if response.get("cmd") == "SUCCESSOR":
                self.second_successor = (response["host"], int(response["port"]))

            # ping the succ and tell it about myself so it knows who its treu pred is
            joining = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            joining.connect(self.successor)
            send_msg(
                joining, {"cmd": "SET_PREVIOUS", "host": self.host, "port": self.port}
            )
            joining.recv(1024)
            joining.close()

            # now the next step is to tell pred that i am its new successor
            joining = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            joining.connect(self.predecessor)
            send_msg(
                joining, {"cmd": "SET_SUCCESSOR", "host": self.host, "port": self.port}
            )
            joining.recv(1024)
            joining.close()

            pred_key = self.hasher(f"{self.predecessor[0]}{self.predecessor[1]}")

            claim = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            claim.connect(self.successor)
            send_msg(
                claim,
                {"cmd": "CLAIM_FILES", "new_node_key": self.key, "pred_key": pred_key},
            )
            # self.handle_file_claim(joining_addr) #MY HELPER IS NOT WORKING FOR SOME REASON,
            # SO I AM GOING
            # TO WRITE CODE HERE SIMPLY
            while True:
                raw = claim.recv(1024).decode()
                if not raw or raw == "TRANSFER_COMPLETE":
                    break
                try:
                    file_msg = json.loads(raw)
                except:
                    continue
                if file_msg.get("cmd") != "FILE":
                    continue
                name = file_msg["filename"]
                backup_path = os.path.join(f"{self.host}_{self.port}", name)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                if name in self.backup_files:
                    self.backup_files.remove(name)
                check_key = self.hasher(name)
                if self.owner(check_key):
                    claim.send(b"READY")
                    path = os.path.join(f"{self.host}_{self.port}", name)
                    self.recieve_file(claim, path)
                    claim.send(b"RECEIVED")
                    if name not in self.files:
                        self.files.append(name)
                else:
                    claim.send(b"SKIP")

            claim.close()
            self.start_ping()

        except Exception as e:
            print(f"Join error: {e}")

    def _copy_file(self, source, destination):
        with open(source, 'rb') as src, open(destination, 'wb') as dst:
            dst.write(src.read())

    def put(self, file_name):
        """
        This function should first find node responsible for the file given by file_name
        , then send the
        file over the socket to that node Responsible node should then replicate the file
        on appropriate node.
        SEE MANUAL FOR DETAILS. Responsible node should save the files
        in directory given by host_port e.g. "localhost_20007/file.py".
        """
        # firstly, find the node responsible, already find node banaya hua usko use kar
        # saktay to find the node
        # replication karni
        # also we will use hasher again to find the key
        # 	fileKey=self.hasher(file_name)
        # 	#and now i will use the findnode function to find k konsa owner has iska
        # 	owner=self.find_node((self.host,self.port),fileKey)
        # 	current_node=(self.host,self.port)
        # 	# if owner!=current_node:
        # 	# 	#if not the correct node responsible then send it to the real owner
        # 	# 	#like think of A,B,C correct node is B but right now the current node is A
        # 	# 	#which is not responsible, so we send to B the real one responsible for the key
        # 	# 	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 	# 	sock.connect(owner
        # 	# 	)
        # 	ead())

        # 		sock.close()
        # 	else:
        # 		# then the responsible node is the current one and hence there are two main
        # things
        # 		#basically a full flow of things to be done. first we have to create and
        # save a copy
        # 		#but then we also need to create a backup saved on successor take lets say
        # agar hamara node fail
        # 		#karjaye to we can use backup and restore the lost files
        # 		#but see there can be a problwm agar say k client ne ghalat node ko contact
        # karlia
        # 		#then forward to correct one, store primary anc reate backup, backup to
        # successor which stores backup

        # 		#first step is to save the file locally and then save backup to successor

        # 
        fileKey = self.hasher(file_name)
        owner = self.find_node((self.host, self.port), fileKey)
        current_node = (self.host, self.port)

        # Find source file
        if os.path.exists(f"./{file_name}"):
            source = f"./{file_name}"
        elif os.path.exists(f"./test/{file_name}"):
            source = f"./test/{file_name}"
        else:
            print(f"File {file_name} not found")
            return

        if owner != current_node:
            # Send to owner
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(owner)
            send_msg(sock, {"cmd": "PUT", "filename": file_name})
            time.sleep(0.05)
            self.send_file(sock, source)
            sock.close()
        else:
            # I am the owner - store locally
            file_path = f"./{self.host}_{self.port}/{file_name}"
            self._copy_file(source, file_path)
            if file_name not in self.files:
                self.files.append(file_name)
            print("Stored ")

            # Backup on successor
            if self.successor != current_node:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(self.successor)
                    send_msg(sock, {"cmd": "BACKUP", "filename": file_name})
                    time.sleep(0.05)
                    self.send_file(sock, file_path)
                    sock.close()
                    print(f"Backed up {file_name} to successor {self.successor}")
                except Exception as e:
                    print(f"Backup failed: {e}")

    def get(self, file_name):
        """
        This function finds node responsible for file given by file_name, gets the file
        from responsible node,
        saves it in "test" directory i.e. "./test/file.py" and returns the name of file.
        If the file is not
        present on the network, return None.
        """
        # so agaon we have been provided with the name of this file
        # simple hash it first to get the key
        our_key = self.hasher(file_name)
        addr = self.find_node((self.host, self.port), our_key)
        if not addr:
            return None
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(addr)
            send_msg(sock, {"cmd": "GET", "filename": file_name})
            response = sock.recv(1024).decode()
            if response == "FILE_FOUND":
                os.makedirs("./test", exist_ok=True)
                self.recieve_file(sock, f"./test/{file_name}")
                return file_name
            return None
        except Exception as e:
            return None
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass


    def leave(self):
        """
        When called leave, a node should gracefully leave the network i.e. it should update
        its predecessor
        that it is leaving it should send its share of file to the new responsible node,
        close all the threads
        and leave. You can close listener thread by setting self.stop flag to True
        """
        self.ping = False
        #trhis function will have 4 things to rtake care of
		# Stop participating in failure detection, transfer its primary files
		# and transfer its backup files
        if self.successor != (self.host, self.port):
            for file in list(self.files):
                file_path = os.path.join(f"{self.host}_{self.port}", file)
                if not os.path.exists(file_path):
                    continue
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(self.successor)
                    send_msg(sock, {"cmd": "PUT", "filename": file})
                    time.sleep(0.05)
                    self.send_file(sock, file_path)
                    sock.recv(1024)  # wait for PUT_SUCCESS
                    sock.close()
                    os.remove(file_path)
                    self.files.remove(file)
                except Exception as e:
                    print(f"Leave transfer error: {e}")

            for file in list(self.backup_files):
                file_path = os.path.join(f"{self.host}_{self.port}", file)
                if not os.path.exists(file_path):
                    self.backup_files.remove(file)
                    continue
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(self.successor)
                    send_msg(sock, {"cmd": "BACKUP", "filename": file})
                    time.sleep(0.05)
                    self.send_file(sock, file_path)
                    sock.close()
                    os.remove(file_path)
                    self.backup_files.remove(file)
                except Exception as e:
                    print(f"Leave backup transfer error: {e}")

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(self.successor)
                send_msg(
                    sock,
                    {
                        "cmd": "SET_PREVIOUS",
                        "host": self.predecessor[0],
                        "port": self.predecessor[1],
                    },
                )
                sock.recv(1024)
                sock.close()
            except:
                pass

        if self.predecessor != (self.host, self.port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(self.predecessor)
                send_msg(
                    sock,
                    {
                        "cmd": "SET_SUCCESSOR",
                        "host": self.successor[0],
                        "port": self.successor[1],
                    },
                )
                sock.recv(1024)
                sock.close()
            except:
                pass

        self.stop = True


    def send_file(self, soc, file_name):
        """
        Utility function to send a file over a socket
                        Arguments:	soc => a socket object
                            file_name => file's
                            name including its path e.g. NetCen/PA3/file.py
        """
        file_size = os.path.getsize(file_name)
        soc.send(str(file_size).encode("utf-8"))
        soc.recv(1024).decode("utf-8")
        with open(file_name, "rb") as file:
            content_chunk = file.read(1024)
            while content_chunk != "".encode("utf-8"):
                soc.send(content_chunk)
                content_chunk = file.read(1024)

    def recieve_file(self, soc, file_name):
        """
        Utility function to recieve a file over a socket
                        Arguments:	soc => a socket object
         file_name => file's name including its path e.g. NetCen/PA3/file.py
        """
        file_size = int(soc.recv(1024).decode("utf-8"))
        soc.send("ok".encode("utf-8"))
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
