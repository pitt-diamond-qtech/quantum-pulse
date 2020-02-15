import socket
from multiprocessing import Process, Pipe

HOST = '127.0.0.1'  # Standard loopback interface address (localhost), change to '179.17.39.2' for device
PORT = 65432        # Port to listen on (non-privileged ports are > 1023), change to 4000 for device
FTP_PORT = 63217    # Port for ftp testing, change to 21 for device

def handle_connection(conn):
    with conn:
        conn.send('Connected by', addr)
        data = conn.recv(1024)
        if not data:
            break
        elif (data == b'*IDN?\n'):
            print('SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
            conn.sendall(b'SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
        else:
            conn.sendall(data)
    finally:
        conn.close()

def echo_server(host=HOST,port=PORT):
    # this server simulates the AWG command protocol, simply echoing the command back except for IDN?
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        try:
            while True:
                conn, addr = s.accept()
                client_proc = Process(target=handle_connection,args=(conn))
                client_proc.start()



def test_echo_server():
    parent_conn, child_conn = Pipe()

    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as mysock:
        mysock.connect((HOST,PORT))
        mysock.sendall('test'.encode())
    if parent_conn.poll(1):
        print(parent_conn.recv())
    p.join(1)


