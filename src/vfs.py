import os
import sys
import errno
import json
try:from .xxfile import *
except ImportError: from file import *
from fuse import FUSE, FuseOSError, Operations, fuse_get_context

class Passthrough(Operations):
	def __init__(self, file):
		self.xxfile = file

	# Helpers
	# =======

	# def _full_path(self, partial):
	# 	if partial.startswith("/"):
	# 		partial = partial[1:]
	# 	path = os.path.join(self.root, partial)
	# 	return path

	# Filesystem methods
	# ==================

	def access(self, path, mode):
		pass
		# full_path = self._full_path(path)
		# if not os.access(full_path, mode):
		# 	raise FuseOSError(errno.EACCES)

	def chmod(self, path, mode):
		raise FuseOSError(errno.EACCES)

	def chown(self, path, uid, gid):
		raise FuseOSError(errno.EACCES)

	def getattr(self, path, fh=None):
		print("getattr", path)
		
		
		if path == "/rd.img":
			return {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 33279, 'st_mtime': 0, 'st_nlink': 1, 'st_size': self.xxfile.size, 'st_uid': 1000}
			
		return  {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 16895, 'st_mtime': 0, 'st_nlink': 1, 'st_size': 0, 'st_uid': 1000}
		# full_path = self._full_path(path)
		# st = os.lstat(full_path)
		# return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
		# 			 'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

	def readdir(self, path, fh):
		print("readdir")
		dirents = ['.', '..', "rd.img"]
		for r in dirents:
			yield r

	def readlink(self, path):
		print("readlink")
		pathname = os.readlink(self._full_path(path))
		if pathname.startswith("/"):
			# Path name is absolute, sanitize it.
			return os.path.relpath(pathname, self.root)
		else:
			return pathname

	def mknod(self, path, mode, dev):
		print("mknod")
		raise FuseOSError(errno.EACCES)
		# return os.mknod(self._full_path(path), mode, dev)

	def rmdir(self, path):
		print("rmdir")
		raise FuseOSError(errno.EACCES)
		# full_path = self._full_path(path)
		# return os.rmdir(full_path)

	def mkdir(self, path, mode):
		print("mkdir")
		raise FuseOSError(errno.EACCES)
		# return os.mkdir(self._full_path(path), mode)

	def statfs(self, path):
		print("statfs")
		stv = os.statvfs("..")
		return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
			'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
			'f_frsize', 'f_namemax'))

	def unlink(self, path):
		print("unlink")
		raise FuseOSError(errno.EACCES)

	def symlink(self, name, target):
		print("syslnk")
		raise FuseOSError(errno.EACCES)

	def rename(self, old, new):
		print("rename")
		raise FuseOSError(errno.EACCES)

	def link(self, target, name):
		print("link")
		raise FuseOSError(errno.EACCES)

	def utimens(self, path, times=None):
		print("utime")
		return 0
		# return os.utime(self._full_path(path), times)

	# File methods
	# ============

	def open(self, path, flags):
		print("open", self.xxfile)
		if "/rd.img" == path:
			# print(flags & os.O_WRONLY)
			if os.O_WRONLY & flags == 1:
				# print("writing")
				return int(self.xxfile.getWrite())
			else:
				return 69
		else:
			print(path, "open err")
			raise FuseOSError(errno.EACCES)


	def create(self, path, mode, fi=None):
		print("create")
		raise FuseOSError(errno.EACCES)

	def read(self, path, length, offset, fh):
		print("read")
		return self.read(offset, length)

	def write(self, path, buf, offset, fh):
		print("write", self.xxfile)
		return self.xxfile.write(buf, offset, fh)

	def truncate(self, path, length, fh=None):
		self.xxfile.truncate(length)
		return length

	def flush(self, path, fh):
		if fh != 69:
			return self.xxfile.flush(fh)

	def release(self, path, fh):
		if fh != 69:
			fl= self.flush(path, fh)

			self.xxfile.writeLock.acquire()
			del self.xxfile.writing[fid]
			print("removing", fid)
			self.xxfile.writeLock.release()

			return fl
		

	def fsync(self, path, fdatasync, fh):
		print("fsync")
		# return self.flush(path, fh)
		return 0


def main(mountpoint, jso):
	pt = Passthrough(FileHandler(jso["segments"], jso["size"]))
	# print(pt.xxfile)
	try:
		FUSE(pt, mountpoint, nothreads=True, foreground=True, allow_other=True, debug=True)
	finally:
		x = pt.xxfile.close()
		if type(x) is str:
			f = open("data.json", "w")
			f.write(x)
			f.close()


if __name__ == "__main__":
	f = open("data.json", "r")
	jso = json.loads(f.read())
	f.close()

	main("x2", jso)