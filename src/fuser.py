#!/usr/bin/env python

from __future__ import with_statement

from multiprocessing.managers import BaseManager

# import os
# import sys
# import errno
# import json
# # try:from .cacheLayer import *
# # except ImportError: from cacheLayer import *
# from fuse import FUSE, FuseOSError, Operations, fuse_get_context


from io import BytesIO



import logging

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
import time, json

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from io import BytesIO

import errno, os

from io import BytesIO

try:from .internetBytesIO import *
except ImportError: from internetBytesIO import *





MOUNT_NAME = "vault"



class Memory(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self, file, readMng):
        self.fd = 0
        # self.file = BytesIO()
        self.file = file
        self.readMng=readMng
        self.readOnlyKey = open("data/key2.key", "rb").read()
    def chmod(self, path, mode):
        raise FuseOSError(errno.ENOENT)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.ENOENT)

    def create(self, path, mode):
        raise FuseOSError(errno.ENOENT)

    def getattr(self, path, fh=None):
        if path == "/"+MOUNT_NAME:
            # return {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 33279, 'st_mtime': 0, 'st_nlink': 1, 'st_size': self.file.getbuffer().nbytes, 'st_uid': 1000}
            return {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 33279, 'st_mtime': 0, 'st_nlink': 1, 'st_size': self.file.get_size(), 'st_uid': 1000}
            
        if path.startswith("/files/"):
            lar = os.path.abspath(os.path.join("data", path[1:]))
            if os.path.isfile(lar):
                f = open(lar, "r")
                x = ""
                while not( (d:=f.read(1)) in ["]", ',']  ):
                    if d in "1234567890":
                        x+=d
                f.close()
                return {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 33279, 'st_mtime': 0, 'st_nlink': 1, 'st_size': int(x), 'st_uid': 1000}
        return  {'st_atime': 0, 'st_ctime': 0, 'st_gid': 1000, 'st_mode': 16895, 'st_mtime': 0, 'st_nlink': 1, 'st_size': 0, 'st_uid': 1000}

    getxattr = None

    def listxattr(self, path):
        print("listxattr", path)
        # attrs = self.files[path].get('attrs', {})
        # return attrs.keys()

    def mkdir(self, path, mode):
        raise FuseOSError(errno.ENOENT)



    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        # self.file.seek(offset)
        # return self.file.read(size)
        if path.startswith("/files/"):
            lar = os.path.abspath(os.path.join("data", path[1:]))
            self.readMng.createFromFile(lar, self.readOnlyKey)
            rd = self.readMng.readFile(lar, offset, size)
            if type(rd) is bytes:
                return rd
            else:
                while (ret:=self.readMng.getFutureValue(lar, rd)) == "Not yet":
                    time.sleep(0.1)
                return ret
        else:
            rd = self.file.read(offset, size)
            if type(rd) is bytes:
                return rd
            else:
                while (ret:=self.file.getFutureValue(rd)) == "Not yet":
                    time.sleep(0.1)
                return ret

    def readdir(self, path, fh):
        if path == "/":
            return ['.', '..', MOUNT_NAME, "files"]
        else:
            return os.listdir(os.path.join("data", path[1:]))

    def readlink(self, path):
        print("read link", path)
        # return self.data[path]

    def removexattr(self, path, name):
        print("remove attr", path, name)
        # attrs = self.files[path].get('attrs', {})

        # try:
        #     del attrs[name]
        # except KeyError:
        #     pass        # Should return ENOATTR

    def rename(self, old, new):
        raise FuseOSError(errno.ENOENT)

    def rmdir(self, path):
        raise FuseOSError(errno.ENOENT)

    def setxattr(self, path, name, value, options, position=0):
        print("setxattr",path, name, value, options, position)
        # # Ignore options
        # attrs = self.files[path].setdefault('attrs', {})
        # attrs[name] = value
    def setattr(self, *args, **kwargs):
        print("ATTTTRRRR",args, kwargs)

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        raise FuseOSError(errno.ENOENT)
    def truncate(self, path, length, fh=None):
        if path.startswith("/files"):
            raise FuseOSError(errno.ENOENT)
        print("truncate", path, length)
        self.file.truncate(length)
        # self.file.truncate(length)
        # size = self.file.getbuffer().nbytes
        # if size != length:
        #     self.file.seek(size)
        #             # write zeroes
        #     self.file.write(b"\x00" * (length-size))
        #     self.file.seek(0)
        return length

    def unlink(self, path):
        raise FuseOSError(errno.ENOENT)

    def utimens(self, path, times=None):
        return 0

    def write(self, path, data, offset, fh):
        if path.startswith("/files"):
            raise FuseOSError(errno.ENOENT)

        # self.file.seek(offset)
        # return self.file.write(data)
        self.file.write(offset, data)
        return len(data)


class myMng(BaseManager): pass

def mount(mount_point):

    myMng.register("InternetBytesIO", InternetBytesIO)
    myMng.register("ReadOnlyManager", ReadOnlyManager)
    with myMng() as m:

        jso = json.load(open("data/fs.json", "r"))
        key = open("data/key.key", "rb").read()
        # nonce = open("data/nonce.dat", "rb").read()
        file = m.InternetBytesIO(key=key, segments=jso, fileName = "data/fs.json")
        rmng = m.ReadOnlyManager()
        try:   
            fuse = FUSE(Memory( file, rmng ), mount_point, foreground=True, allow_other=True, nothreads=False, debug=False)
        finally:
            print("Closing")
            os.system("sudo umount /mnt/vault ; sudo rmdir /mnt/vault")
            f = open("data/fs.json", "w")
            f.write(json.dumps(file.close(full=True)))
            f.close()

    # fs.softKill()
