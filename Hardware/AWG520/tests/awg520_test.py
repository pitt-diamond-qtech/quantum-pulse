# Created on 2/1/20 by gurudev

from pathlib import Path
import os
from Pulseshaping.Hardware.AWG520 import AWG520
import pytest
from multiprocessing import Pipe,Process

HOST = '127.0.0.1'  # Standard loopback interface address (localhost), change to '179.17.39.2' for device
PORT = 65432        # Port to listen on (non-privileged ports are > 1023), change to 4000 for device
FTP_PORT = 63217    # Port for ftp testing, change to 21 for device

print('Module name is: ',__name__)
import socket

# def run_echo_server():
#     with open('echo-server.py') as f:
#         code = compile(f.read(),'echo-server.py','exec')
#         exec(code)

def echo_server(c_conn,host=HOST,port=PORT):
    import socket

    # this server simulates the AWG command protocol, simply echoing the command back except for IDN?
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        try:
            while True:
                c_conn.send('waiting for connection')
                conn, addr = s.accept()
                with conn:
                    c_conn.send('Connected by', addr)
                    data = conn.recv(1024)
                    if not data:
                        break
                    elif (data == b'*IDN?\n'):
                        print('SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
                        conn.sendall(b'SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
                        c_conn.send(b'SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
                    else:
                        conn.sendall(data)
                        c_conn.send(data)
        finally:
            conn.close()


def start_echo_server():
    parent_conn, child_conn = Pipe()
    p = Process(target=echo_server, args=(child_conn,HOST,PORT),daemon=True)
    p.start()
    print(parent_conn.recv())
    p.join(1)
    return p


def test_awg520():
    '''Prior to running pytest on this folder you should start the echo-server and teh ftp-server.
    eventually i need to start those servers from within the testing script but for now this works.'''


    try:
        # proc = start_echo_server()
        c = AWG520(HOST,PORT)
        c.setup()
        print('current directory is',os.getcwd())
        #c.sendfile('0_2.wfm','../sequencefiles/0_2.wfm') # testing the FTP file transfer
        c.green_off()
        # proc.close()
    except:
        raise

def test_awgfile():
    d = AWGFile(ftype="SEQ")
    from matplotlib import pyplot as plt
    plt.plot(d.sequence.wavedata[1,:])
    plt.show()
    d.write_waveform("test",1,d.sequence.wavedata[0,:],d.sequence.c1markerdata)
    d.write_sequence()

