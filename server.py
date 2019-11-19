import numpy as np
import cv2 as cv
import socket
from pickle import loads, dumps
import sys
from tempfile import TemporaryFile as tmpFile
from PIL import Image
import matplotlib.pyplot as plt
import time
import threading
#import socket.timeout as TimeoutException

BUFFER_SIZE = 2048

user_list = {}

def writeLog(s, file=None):
    if file == None:
        print(s)
    else:
        file.write(s+'\n')
    return

class user:
    def __init__(self, addr, seq, rtt, wind):
        self.addr = addr
        self.seq = seq
        self.rtt = 0
        self.wind = wind

    def push(self, sock, data):
        data[0] = self.seq
        sock.sendto(dumps(data), self.addr)
        self.seq = (self.seq+1)%self.wind
        return

def getSock(IP, port, UDP=False, timeout=None):
    typ = socket.SOCK_DGRAM if UDP else socket.SOCK_STREAM
    t = socket.socket(socket.AF_INET, typ)
    t.bind((IP, port))
    t.settimeout(timeout)
    return t

def calculateWindowSize(rtt):
    if rtt < 1:
        rtt = 5
    return rtt*15

def sendWindowSize(sock, user_data, probe_count=5):
    writeLog("Sending window size")
    seq_no = user_data.seq
    wind_size = user_data.wind
    sock.settimeout(user_data.rtt+0.1)
    data = None
    for i in range(probe_count):
        sock.sendto(dumps([seq_no+i,9,wind_size]),user_data.addr)
    start = time.time()
    while(time.time()-start < 30):
        try:
            data = sock.recv(BUFFER_SIZE)
            data = loads(data)
            if seq_no<=data[0]<seq_no+probe_count and data[1]==9:
                return 1
        except socket.timeout:
            # continue in case of timeout
            pass
        except Exception as e:
            s = "Exception occurred in sendWindowSize: "+e
            writeLog(s)
    return -1

def listen(sock):
    seq_no = -1
    rtt = -1
    while(True):
        #print('Listening')
        try:
            data, client = sock.recvfrom(BUFFER_SIZE)
            data = loads(data)
            seq_no = data[0]
            if data[1] == 8:
                rtt = 2*(time.time()-data[2])
                if client not in user_list:
                    tmp_usr = user(client, data[0], rtt, calculateWindowSize(rtt))
                    writeLog("Someone new is here, sending ACK")
                    sock.sendto(dumps([data[0],8,1]),client)
                    writeLog("ACK sent and sending window size")
                    stat = sendWindowSize(sock, tmp_usr)
                    writeLog("Window size set, adding new user: "+str(stat)) 
                    if stat == 1:
                        user_list[client] = tmp_usr
                        print("New user added")
                else:
                    sock.sendto(dumps([data[0],8,1]),client)
            elif data[1] == 9:
                # ACK for window_size
                if client not in user_list:
                    # terminate connection
                    pass
            elif data[1] == 10:
                writeLog("Removing user")
                if client in user_list:
                    del(user_list[client])
            else:
                # send NAK
                pass
        except Exception as e:
            print("An exception occured:", e)
            pass
    print('Returning')
    return

def capAndSend(sock, src):
    cap = cv.VideoCapture(src)
    while(True):
        ret, frame = cap.read()
        img = Image.fromarray(frame)
        f = tmpFile()
        img.save(f, 'JPEG') 
        f.seek(0)
        data = [-1,2,f.read()]
        for each in user_list.values():
            each.push(sock, data)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv.destroyAllWindows()

def broadcast(sock, src=0):
    writeLog("In BroadCast")
    t = threading.Thread(target=listen, args=(sock,))
    s = threading.Thread(target=capAndSend, args=(sock, src))
    t.start()
    s.start()
    t.join()
    print("Join 1")
    print("Join 2")
    return

ip = '127.0.0.1'
port = 64000

s = getSock(ip, port, UDP=True, timeout=40)
broadcast(s)