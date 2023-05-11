#!/usr/bin/env python3

from mega import Mega
from mega.errors import RequestError
import sys, io
import json, os
import time, random
from concurrent.futures import ThreadPoolExecutor

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes


from src import fuser


def runner(account):
	mega = Mega()
	print(account["email"])
	while True:
		m = None
		try:
			m = mega.login(account["email"], account["password"])
		except RequestError as e:
			if str(e) == "ENOENT, Object (typically, node or user) not found":
				print("Error on "+account["email"])
				break
		except Exception as e:
			print("retry")
			time.sleep(1)
			continue

		account["quota"] = m.get_quota()
		account = {**account, **m.__dict__}
		f = open("accounts2", "a")
		f.write(json.dumps(account) + "\n")
		f.close()
		break

def _upload_to_link(m, bio):
	print(bio, "start")
	file = m.upload(str(random.randrange(0, 1000000))+".txt", byteio=bio)
	print(bio, "end")
	return m.get_upload_link(file)

def mega_from_json(json):
	mega = Mega()
	for k, v in json.items():
		setattr(mega, k, v)
	return mega

# print(m.get_quota())
if __name__ == "__main__":
	if len(sys.argv) != 1:
		if sys.argv[1] == "renew":
			f = open("accounts", "r")
			lines = [json.loads(a) for a in f.read().split("\n") if len(a.strip()) != 0]
			f.close()
			with ThreadPoolExecutor(max_workers=40) as executor:
				for account in lines:
					executor.submit(runner, account)
		elif sys.argv[1] == "fuse":
			if sys.argv[-1] == "mount":
				os.system("(sleep 5 ; sudo mkdir /mnt/vault ; sudo mount img_mount_point/vault /mnt/vault && sleep 5 &&  sudo chown -R \"$(whoami)\" /mnt/vault/)&")
			fuser.mount("img_mount_point")

		elif sys.argv[1] == "init":
			os.mkdir("data")
			os.system("openssl rand 32 > data/key.key")
			os.system("openssl rand 24 > data/nonce.dat")
			os.system("echo [0] > data/fs.json")
		elif sys.argv[1] == "sec":
			if len(sys.argv) == 3:
				import getpass
				password = getpass.getpass()
				password2 = getpass.getpass()
				if password == password2:
					f = open(sys.argv[2], "rb")
					data = f.read()
					f.close()

					key = SHA256.new(password.encode("utf-8")).digest()
					iv = get_random_bytes(16)
					encryptor = AES.new(key, AES.MODE_CBC, iv)

					padding = AES.block_size - len(data) % AES.block_size
					data += bytes([padding]) * padding
					data = iv + encryptor.encrypt(data)

					f = open(sys.argv[2]+".enc", "wb")
					f.write(data)
					f.close()
				else:
					print("passwords don't match!!!")
	else:
		print("The Hermes file system:")
		print("For all your slow file storage needs.")
		print()
		print()
		print("Commands:")
		print("python main.py renew")
		print("python main.py fuse")

