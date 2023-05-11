from threading import Lock
import random, json
from io import BytesIO
from requests.exceptions import ConnectionError
from mega import Mega

from functools import lru_cache

from tenacity import retry, stop_after_attempt

from threading import Thread

def mega_from_json(json):
	mega = Mega()
	for k, v in json.items():
		setattr(mega, k, v)
	return mega

def randomAccount():
	f = None
	try: f = open("accounts", "r")
	except FileNotFoundError: f = open("../accounts", "r")
	rc = random.choice([ff for ff in f.read().split("\n") if len(ff.strip()) != 0])
	f.close()
	return rc

@retry(stop=stop_after_attempt(24))
def get_segment(seg):
	data = BytesIO(b"")
	for chunck in Mega().download_url(seg, do_yield=True):
		data.write(chunck)
	data.seek(0)
	return data

def upload_segment(byteio):
	while True:
		try:
			print("MF: Uploading byteio of length "+ str(byteio.getbuffer().nbytes))

			account = randomAccount()
			m=mega_from_json(json.loads(account))
			file = m.upload(str(random.randrange(0, 1000000))+".txt", byteio=byteio)
			r=  m.get_upload_link(file)
			print("Link at", r)
			return r
		except ConnectionError:
			print("Retrying")
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
	# print(size)
# print(genSizeChuncks(4, 0, 5))
# exit()
class Segment():
	def __init__(self, url=None, byteio=None,shash=None, vacant=False):
		self.dataType = "url" if url is not None else ("byteio" if byteio is not None else "vacant")
		self.url = url
		self.byteio = byteio
		self.vacant = vacant
		self.shash = shash
class SegmentMiddleman(Thread):
	def __init__(self, pre_segments=None):
		self.segments = [] if pre_segments is None else [Segment(**s) for s in pre_segments]
		self.cache = {}

		self.running = True
		Thread.__init__(self)
		self.start()
	def indexSegmentGet(self, snum):
		if snum > len(self.segments):
			return b""
		else:
			sid = str(snum)
			if sid in self.cache:
				return self.cache[sid]
			else:
				if len(self.segments) <= snum:
					print(snum, "too small for", self.segments)
					return b""
				sg = self.segments[snum]
				if sg.dataType == "url":
					data = get_segment(sg.url)
					self.cache[sid] = data
					return data
				elif sg.dataType == "byteio":
					sg.byteio.seek(0)
					return sg.byteio.read()
				elif sg.vacant:
					return b""
				else:
					print(snum, "failed", sg.__dict__, sg)
	def indexSegmentUpdate(self, snum, data):
		self.cache[str(snum)] = data
		while snum > len(self.segments):
			self.segments.append(Segment(vacant=True))
		if snum == len(self.segments):
			self.segments.append(Segment(byteio=BytesIO(data)))
			return
		if snum < len(self.segments):
			self.segments[snum] = Segment(byteio=BytesIO(data))
			
	def run(self):
		pass



SEG_SIZE = 5*1024*1024
# SEG_SIZE=10
class FileHandler:
	def __init__(self, segments = None, size = None):
		self.size = 0 if size is None else size

		self.segmentMng = SegmentMiddleman()
		
	def getSegment(self, snum):
		if len(self.segments) > snum:
			return self.segments[snum]
		else:
			return None

	def getWrite(self):
		fid = 21
		return int(fid)

	def write(self, buf, offset, fid):
		
		# self.size = max(self.size, offset+len(buf))
		# fid = str(fid)
		# segments = {}


		# writes = splittr(SEG_SIZE, offset, buf)


		# for offset, buf in writes:
		# 	segnum = int(offset/SEG_SIZE)

		# 	byteio=BytesIO(self.segmentMng.indexSegmentGet(segnum))

		# 	byteio.seek(offset%SEG_SIZE)
		# 	byteio.write(buf)
		# 	segments[str(segnum)] = byteio
		# for seg_num, byteio in segments.items():
		# 	seg_num = int(seg_num)

		# 	byteio.seek(0)
		# 	d = byteio.read()
		# 	self.segmentMng.indexSegmentUpdate(seg_num, d)



		segments = {}

		self.size = max(self.size, offset+len(buf))
		snum = offset // SEG_SIZE 
		for o2, buff2 in splittr(SEG_SIZE,offset, buf):
			bio = BytesIO(self.segmentMng.indexSegmentGet(snum))
			bio.seek(o2)
			bio.write(buff2)
			segments[str(snum)] =bio
			snum +=1

		for seg_num, byteio in segments.items():
			seg_num = int(seg_num)

			byteio.seek(0)
			d = byteio.read()
			self.segmentMng.indexSegmentUpdate(seg_num, d)

	def read(self, offset, length):
		segnum = int(offset/SEG_SIZE)
		segoff = int(offset%SEG_SIZE)
		if len(self.segmentMng.segments) > segnum:
			if segoff+length <= SEG_SIZE:
				# surl = self.getSegment(segnum)
				
				byteio = BytesIO(self.segmentMng.indexSegmentGet(segnum))
				byteio.seek(segoff)
				return byteio.read(length)
			else:
				ret = b""
				for seg_num, seg_offset, seg_len in genSizeChuncks(SEG_SIZE, offset, length):
					ret+=self.read((seg_num*SEG_SIZE)+seg_offset, seg_len)
				return ret
			# bio = get_segment(self.segments[snum])
			# return bio.read(length)
		else:
			return b""
	def flush(self, fid):
		pass
	def truncate(self, length):
		if self.size == length:
			return
		elif self.size < length:
			self.write(b"\x00" * (length-self.size), self.size, -1)
			# self.size = length
		elif self.size > length:
			st = 0
			ed = SEG_SIZE
			sgs = []
			for i, sg in enumerate(self.segmentMng.segments):
				if st > length:
					break
				elif ed > length:
					bio = BytesIO(self.segmentMng.indexSegmentGet(i))
					bio.truncate(length-st)
					sgs.append(Segment(byteio=bio))

				st+=SEG_SIZE
				ed+=SEG_SIZE
			self.segmentMng.segments = sgs
			self.size = length
		# self.size = length

		# new_segments = []
		# if length != 0:
		# 	for seg_num, seg_offset, seg_len in genSizeChuncks(SEG_SIZE, 0, length):
		# 		snum = self.getSegment(seg_num)
		# 		if seg_len==SEG_SIZE:
		# 			new_segments.append(snum)
		# 		else:
		# 			if snum is None:
		# 				new_segments.append(upload_segment(BytesIO(b"\x00"*seg_len)))
		# 			else:
		# 				byteio = get_segment(snum)
		# 				byteio.truncate(seg_len)
		# 				byteio.seek(0)
		# 				new_segments.append(upload_segment( byteio   ))
		# self.segments = new_segments
	def close(self):
		return json.dumps({"segments": self.segments, "size": self.size})

	def removeWrite(self, fid):
		self.writeLock.acquire()
		del self.writing[fid]
		print("removing", fid)
		self.writeLock.release()
