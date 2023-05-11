try:from .internetBytesIO import *
except ImportError: from internetBytesIO import *

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import os, subprocess

def getBackupAccount():
	f=open(os.path.join(BASE_DIR_PATH, "data", "backupAccount"), "r")
	jso = f.read()
	f.close()
	return jso


account = getBackupAccount()
m=mega_from_json(json.loads(account))
megafs_folder = m.find('megafs')

def encrypt_for_backup(data):
	file_out = BytesIO()

	recipient_key = RSA.import_key(open( os.path.join(BASE_DIR_PATH, "data", "publickey.crt") ).read())
	session_key = get_random_bytes(16)

	# Encrypt the session key with the public RSA key
	cipher_rsa = PKCS1_OAEP.new(recipient_key)
	enc_session_key = cipher_rsa.encrypt(session_key)

	# Encrypt the data with the AES session key
	cipher_aes = AES.new(session_key, AES.MODE_EAX)
	ciphertext, tag = cipher_aes.encrypt_and_digest(data)
	[ file_out.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext) ]
	file_out.seek(0)
	return file_out
def zipThisBitch(extra=None):
	print("Backing up files")
	lst = [os.path.join(BASE_DIR_PATH, f) for f in os.listdir(BASE_DIR_PATH) if f!="img_mount_point"]
	p = subprocess.Popen(["zip", "-r", "-"]+lst,
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
	zipped = encrypt_for_backup(p.stdout.read())

	while True:
		try: return m.upload(str(time.ctime()) +(extra if extra is not None else "")+".zip", megafs_folder[0], byteio=zipped)
		except Exception as e: print("Backing up err",e)


# file = m.upload("megafs/wow.txt", folder[0], byteio=BytesIO(b"asdf"))