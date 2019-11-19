import numpy as np
import cv2 as cv
import socket
from pickle import loads, dumps
from tempfile import TemporaryFile as tmpFile
from PIL import Image
import random
import time

BUFFER_SIZE = 320000

GLOB_SEQ = -1
GLOB_WIND = 1

def writeLog(s, file=None):
    if file == None:
        print(s)
    else:
        file.write(s+'\n')
    return

def getSock(IP=None, port=None, UDP=False, timeout=None):
    typ = socket.SOCK_DGRAM if UDP else socket.SOCK_STREAM
    t = socket.socket(socket.AF_INET, typ)
    if IP != None:
        t.bind((IP, port))
    t.settimeout(timeout)
    return t

def handshake(sock, dest, probe_count=5):
    writeLog("Starting handshake")
    seq_no = random.randint(0,1024)
    ack_count = 0
    for i in range(probe_count):
        sock.sendto(dumps([seq_no+i,8,time.time()]),dest)
        time.sleep(0.2)
    start = time.time()
    while(time.time()-start < 30):
        writeLog("Waiting for response")
        data = sock.recv(BUFFER_SIZE)
        data = loads(data)
        if seq_no<=data[0]<seq_no+probe_count and data[1]==8 and data[2]==1:
            writeLog("Handshake succeeded")
            GLOB_SEQ = data[0]%GLOB_WIND
            return 1
        elif seq_no<=data[0]<seq_no+probe_count and data[1]==8 and data[2]==0:
            return -1
        time.sleep(0.2)
    writeLog("Bad handshake")
    return -1

def sendWindAck(sock, seq, dest):
    sock.sendto(dumps([seq,9,1]),dest)
    return

def sendFinAck(sock, seq, dest, probe_count=5):
    for _ in range(probe_count):
        sock.sendto(dumps([seq,10,1]),dest)
    return

def getAndShow(sock, dest):
    global GLOB_WIND
    global GLOB_SEQ
    while(True):
        data = sock.recv(BUFFER_SIZE)
        data = loads(data)
        if data[1] < 8:
            print('Got frame', data[0],GLOB_SEQ)
            pass
        elif data[1] == 8:
            continue
        elif data[1] == 9:
            GLOB_WIND = data[2]
            sendWindAck(sock, data[0], dest)
            continue
        if ((GLOB_SEQ-data[0]+GLOB_WIND)%GLOB_WIND)>100:
            continue
        else:
            GLOB_SEQ = data[0]
        frame = tmpFile()
        frame.write(data[2])
        img = Image.open(frame)
        cv.imshow('frame',np.asarray(img))
        if cv.waitKey(1) & 0xFF == ord('q'):
            writeLog("FINishing connection")
            sendFinAck(sock, data[0], dest)
            sock.close()
            break

def requestStream(sock, dest):
    writeLog("Requesting stream")
    stat = handshake(sock, dest)
    if stat == -1:
        raise Exception("Server can't connect")
    getAndShow(sock, dest)
    return

ip = '127.0.0.1'
port = 64001
dest = (ip, 64000)
sock = getSock(ip, port, UDP=True)
requestStream(sock, dest)
