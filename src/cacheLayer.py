from multiprocessing.connection import Listener, Client
try:from .internetBytesIO import *
except ImportError: from internetBytesIO import *
import time
from threading import Thread

import concurrent.futures
import asyncio

Mode = 2

ak = b'iajoqihqqu10h8'
address = ('localhost', 6000)     # family is deduced to be 'AF_INET'





class FileServer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.running = True

    def run(self):
        # f = open("data.json", "r")
        # jso = json.loads(f.read())
        # f.close()

        self.fileHandler = InternetBytesIO()

        try:
            self.listener = Listener(address, authkey=ak)
            try:
                while self.running:
                    conn = self.listener.accept()
                    while True:
                        msg = conn.recv()
                        # do something with msg
                        if msg == 'exit':
                            conn.close()
                            self.listener.close()
                            self.running=False
                            break

                        elif msg == "func":
                            ret = getattr(self.fileHandler ,conn.recv())
                            para = conn.recv()
                            
                            ret = ret(*para)

                            conn.send(ret)

                            conn.recv()

                        elif msg == "get":
                            ret = getattr(self.fileHandler ,conn.recv())
                            conn.send(ret)

                            conn.recv()

            except Exception as e:
                import traceback
                print(traceback.format_exc())
        finally:
            pass
            # f = open("data.json", "w")
            # f.write(self.fileHandler.close())
            # f.close()

            self.running = False

    def softKill(self):
        if self.is_alive:
            conn = Client(address, authkey=ak)
            conn.send('exit')
            self.join()
class NetFile:
    def __init__(self):
        self.conn = Client(address, authkey=ak)
    def call(self, name, *args):
        self.conn.send("func")
        self.conn.send(name)
        self.conn.send(args)
        ret= self.conn.recv()
        self.conn.send("z")
        return ret

    def getSegment(self, *args):
        return self.call("getSegment", *args)

    def getWrite(self):
        return self.call("getWrite")
    def write(self, *args):
        return self.call("write", *args)
    def read(self, *args):
        return self.call("read", *args)
    def flush(self, *args):
        return self.call("flush", *args)
    def truncate(self, *args):
        return self.call("truncate", *args)
    def close(self):
        return self.call("close")
    def removeWrite(self, *args):
        return self.call("removeWrite", *args)

    def __getattr__(self, name):
        if name == "size":
            self.conn.send("get")
            self.conn.send(name)
            ret= self.conn.recv()
            self.conn.send("z")
            return ret
        else:
            raise AttributeError("Can't find "+name)



