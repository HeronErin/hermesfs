from io import BytesIO

from tenacity import retry, stop_after_attempt
import time, random, json, hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Lock
from mega import Mega
from Crypto.Cipher import ChaCha20
from Crypto.Random import get_random_bytes
import zlib, json, os

import base64

from multiprocessing.managers import BaseManager



BASE_DIR_PATH = os.path.dirname(os.path.dirname(__file__))

class FutureValue(Thread):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.running = True
        self.ret = None
        Thread.__init__(self)
        self.start()
    def run(self):
        try:
            self.ret=self.func(*self.args, **self.kwargs)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        finally:
            self.running = False
    def rjoin(self):
        self.join()
        return self.ret

BaseManager.register("FutureValue", FutureValue)

def mega_from_json(json):
    mega = Mega()
    for k, v in json.items():
        setattr(mega, k, v)
    return mega
def randomAccount():
    f = open(os.path.join(BASE_DIR_PATH, "data", "accounts"), "r")
    
    rc = random.choice([ff for ff in f.read().split("\n") if len(ff.strip()) != 0])
    f.close()
    return rc
def upload_segment(byteio, key, nonce):
    cipher = ChaCha20.new(key=key, nonce=nonce)
    # cipher.seek(segnum*SEGMENT_SIZE)


    byteio.seek(0)
    bio2 = BytesIO(cipher.encrypt(zlib.compress(byteio.read(), 2)))
    while True:
        try:
            bio2.seek(0)
            print("MF: Uploading byteio of length "+ str(bio2.getbuffer().nbytes))

            account = randomAccount()
            m=mega_from_json(json.loads(account))
            file = m.upload(str(random.randrange(0, 1000000))+".txt", byteio=bio2)
            r=  m.get_upload_link(file)
            print("Link at", r)
            return r
        except Exception as e:
            print("Retrying", e)
            time.sleep(0.5)
            # import traceback
            # print(traceback.format_exc())

SEGMENT_SIZE = 1024*1024*10
def get_segment(seg, key, nonce):
    print("Getting segment", seg)
    cipher = ChaCha20.new(key=key, nonce=nonce)
    # cipher.seek(segnum*SEGMENT_SIZE)
    def tmp(seg2):
        while True:
            try:
                b = b""
                for chunck in Mega().download_url(seg2, do_yield=True):
                    b+= chunck
                bio = BytesIO(zlib.decompress(cipher.decrypt(b)))
                return bio
            except Exception as e: print(e)

    return FutureValue(tmp, seg)


class Segment():
    def __init__(self, url=None, byteio=None,shash=None, zfilled=False, nonce = None):
        self.dataType = "url" if url is not None else ("byteio" if byteio is not None else "zfilled")
        self.url = url
        self.byteio = byteio
        self.zfilled = zfilled
        self.shash = shash
        if nonce is not None:
            nonce = base64.b64decode(nonce.encode("utf-8"))
        self.nonce = nonce

        self.byteio_future = None

        self.laccess = time.time()
        self.writeLock = Lock()
    def asBytesIO(self, key):
        self.laccess = time.time()
        try:
            self.writeLock.acquire()
            if self.byteio_future is not None:
                if self.byteio_future.running:
                    return self.byteio_future
                else:
                    
                    self.byteio = self.byteio_future.ret
                    self.byteio_future = None
                    
                    return self.byteio

            if self.byteio is not None:
                return self.byteio
            if self.zfilled:
                return BytesIO(b"\x00"*SEGMENT_SIZE)
            if self.dataType == "url":
                
                self.byteio_future = get_segment(self.url, key, self.nonce)
                return self.byteio_future
            raise Exception("?")
        finally:

            self.writeLock.release()
def handleFuture(x):
    if type(x) is FutureValue:
        return x.rjoin()
    else:
        return x


def splittr(size,offset, buff):
    ret = []
    bio = BytesIO(buff)
    bio.seek(0)
    offset2 = offset
    while (x:=bio.read(size - (offset%size) )):
        ret.append([offset%size, x])
        offset2+=len(x)
        offset=0

    return ret
def genSizeChuncks(seg_size, offset, size):
    First = (int(offset/seg_size)+1)*seg_size-offset
    size -= First
    if size < 0:
        return [  [int(offset/seg_size), offset%seg_size, First-abs(size)     ]   ]
    
    fo = int(offset/seg_size)
    ret = [  [int(offset/seg_size), offset%seg_size, First ]  ]
    while size > 0:
        fo+=1
        seg_size = size if size < seg_size else seg_size
        size-=seg_size
        ret.append([fo, 0,  seg_size])
        
    return ret

try:from . import backupUtils
except ImportError: import backupUtils

class InternetBytesIO(Thread):
    def __init__(self, key, segments=None, fileName="data/fs.json"):
        self.segments = []
        self.size = 0

        self.fileName = fileName
        self.key=key
        # self.nounce=nonce


        self.futureValues = {}        

        if segments is not None:
            self.size = segments.pop(0)
            for s in segments:
                if s[0] == "zfilled":
                    self.segments.append(Segment(zfilled=True))
                elif s[0] == "url":

                    self.segments.append(Segment(url = s[1], shash=s[-2], nonce=s[-1]))
                else:
                    raise Exception("Malformed input", s)
        
        self.background_running = True
        Thread.__init__(self)
        self.start()
       
    def run(self):
        lhash = -1
        while self.background_running:
            for _ in range(120):
                if not self.background_running:
                    return
                time.sleep(1)
            self.sync_segments()
            jso = json.dumps(self.close(full=False))
            h = hash(jso)
            if h != lhash:
                lhash = h
                f = open(self.fileName, "w")
                f.write(jso)
                f.close()
                Thread(target = backupUtils.zipThisBitch).start()
           
    def segment_hash_lookup(self, hashed):
        for s in self.segments:
            if s.shash == hashed and s.url is not None:
                return (s.url, s.nonce)
    def sync_segments(self, force=False):
        futures = []
        with ThreadPoolExecutor(max_workers=25) as exe:
            tm = time.time()
            for i, s in enumerate(self.segments):
                if s.dataType != "url" and s.dataType != "zfilled":
                    if tm-s.laccess > 180 or force:
                        bio = s.asBytesIO(self.key)
                        bio.seek(0)
                        hashed= hashlib.md5( bio.read() ).hexdigest()
                        bio.seek(0)
                        looked_up = self.segment_hash_lookup(hashed) 
                        if looked_up is not None:
                            futures.append([looked_up[0], i, hashed, looked_up[1]])
                        else:
                            no=get_random_bytes(24)
                            futures.append([exe.submit(upload_segment, bio, self.key, no), i, hashed, no])
                elif s.dataType == "url":
                    if tm-s.laccess > 180 or force:
                        if s.byteio_future is not None:
                            bio = handleFuture(s.byteio_future)
                            s.byteio = bio
                            s.byteio_future = None
                        if s.byteio is not None:
                            bio = s.byteio
                            bio.seek(0)
                            hashed= hashlib.md5( bio.read() ).hexdigest()
                            bio.seek(0)

                            looked_up = self.segment_hash_lookup(hashed) 
                            if hashed != s.shash:
                                if looked_up is not None:
                                    futures.append([looked_up[0], i, hashed, looked_up[1]])
                                else:
                                    no=get_random_bytes(24)
                                    futures.append([exe.submit(upload_segment, bio, self.key, no), i, hashed, no])

        for url, segment_number, hashed, no in futures:
            
            self.segments[segment_number].dataType = "url"
            self.segments[segment_number].url = url if type(url) is str else url.result()
            self.segments[segment_number].shash = hashed
            self.segments[segment_number].nonce = no
            self.segments[segment_number].byteio = None

    def get_size(self):
        return self.size
    def read(self, offset, length):
        futures = []
        lnum = -1
        for snum, seg_seek, seg_len in genSizeChuncks(SEGMENT_SIZE, offset, length):
            if snum < len(self.segments):
                lnum=snum
                futures.append((seg_seek, self.segments[snum].asBytesIO(self.key) ))
        if lnum != -1:
            for _ in range(2):
                lnum+=1
                if lnum < len(self.segments):
                    self.segments[lnum].writeLock.acquire()
                    if self.segments[lnum].dataType == "url" and self.segments[lnum].byteio is None and self.segments[lnum].byteio_future is None:

                        self.segments[lnum].byteio_future = get_segment(self.segments[lnum].url, self.key, self.segments[lnum].nonce)
                    self.segments[lnum].writeLock.release()
                    # self.segments[lnum].asBytesIO()
        def tmp(_futures):
            ret = b""
            for seg_seek, fut in _futures:
                b = handleFuture(fut)
                b.seek(seg_seek)
                ret+=b.read(seg_len)
            return ret
        if any((1 for _, x in futures if type(x) is FutureValue )):
            futureId = str(random.randrange(0, 1000000))
            self.futureValues[futureId] = FutureValue(tmp, futures)
            return futureId
        return tmp(futures)
    def getFutureValue(self, fid):
        if self.futureValues[fid].running == False:
            ret = self.futureValues[fid].ret
            del self.futureValues[fid]
            return ret
        else:
            return "Not yet"
    def write(self, offset, buf):

        self.size = max(self.size, offset+len(buf))
        snum = offset // SEGMENT_SIZE 
        for o2, buff2 in splittr(SEGMENT_SIZE,offset, buf):
            bio = handleFuture(self.segments[snum].asBytesIO(self.key)) if snum < len(self.segments) else BytesIO()
            bio.seek(o2)
            bio.write(buff2)
            if snum < len(self.segments):
                self.segments[snum] = Segment(byteio=bio)
            else:
                while snum != len(self.segments):
                    self.segments.append(Segment(zfilled=True))
                self.segments.append(Segment(byteio=bio))
            snum +=1
    def truncate(self, length):
        if self.size == length:
            return
        elif self.size < length:
            for snum, seg_seek, seg_len in genSizeChuncks(SEGMENT_SIZE, self.size, length):
                if seg_seek != 0 or seg_len != SEGMENT_SIZE:
                    self.write(self.size, b"\x00" * (length-self.size))
                else:
                    self.segments.append(Segment(zfilled=True))
                    self.size+=SEGMENT_SIZE
        elif self.size > length:
            st = 0
            ed = SEGMENT_SIZE
            sgs = []
            for i, sg in enumerate(self.segments):
                if st > length:
                    break
                elif ed > length:
                    sg22 = handleFuture(sg.asBytesIO(self.key))
                    sg22.truncate(length-st)
                    sgs.append(Segment(byteio=sg22))
                else:
                    sgs.append(sg)

                st+=SEGMENT_SIZE
                ed+=SEGMENT_SIZE
            self.segments = sgs
            self.size = length
    def close(self, full=False):


        try:
            if full:
                self.background_running = False
                self.join()
                self.sync_segments(force=True)

            jso = [self.size]
            for s in self.segments:
                if s.dataType == "url":

                    jso.append(["url", s.url, s.shash, base64.b64encode(s.nonce).decode("utf-8")])
                elif s.dataType == "zfilled":
                    jso.append(["zfilled"])
            if full:
                backupUtils.zipThisBitch(extra='exit')

            return jso
        except Exception as e:
            import traceback
            print(traceback.format_exc())

class ReadOnlySegmentIO(InternetBytesIO):
    def __init__(self, key, segments):
        self.segments = []
        self.size = 0

        self.fileName = "/dev/null"
        self.key=key
        # self.nounce=nonce


        self.futureValues = {}        

        if segments is not None:
            self.size = segments.pop(0)
            for s in segments:
                self.segments.append(Segment(url = s[0], shash=None, nonce=s[-1]))
   
        
        self.background_running = True
        Thread.__init__(self)
        self.start()
    def write(self, offset, buf): pass
    def sync_segments(self, force=False):
        tm = time.time()
        for i, s in enumerate(self.segments):
            if s.dataType == "url":
                if tm-s.laccess > 180 or force:
                    if s.byteio_future is not None:
                        bio = handleFuture(s.byteio_future)
                        s.byteio = bio
                        s.byteio_future = None
                    if s.byteio is not None:
                        self.segments[i].byteio = None
    def close(self, *args, **kwargs):
        return "[]"

class ReadOnlyManager():
    def __init__(self):
        self.files = {}
    def createFromFile(self, path, key):
        if not (path in self.files):
            f = open(path, "r")
            jso = json.loads(f.read())
            f.close()
            self.files[path] = ReadOnlySegmentIO(key, jso)
    def readFile(self, path, offset, length):
        return self.files[path].read(offset, length)
    def close(self):
        for k, v in self.files.items():
            v.close(full=True)
    def getFutureValue(self, path, fid):
        return self.files[path].getFutureValue(fid)
