# Created by Gurudev Dutt <gdutt@pitt.edu> on 2/15/20
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

HOST = '127.0.0.1'  # Standard loopback interface address (localhost),
PORT = 65432        # Port to listen on (non-privileged ports are > 1023),
FTP_PORT = 63217    # Port for ftp testing, change to 21 for device

import socket
import os,time

def handle_connection(client,addr):
    with client:
        #client.send('Connected by', addr)
        #print("Got connection")
        data = client.recv(1024)
        if not data:
            return 'Nodata'
        elif (data == b'*IDN?\n'):
            print('SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
            client.sendall(b'SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
            return 'IDN'
        else:
            client.sendall(data)
            return 'Data'


# this server simulates the AWG command protocol, simply echoing the command back except for IDN?
p_pid = os.getpid()
print('Starting echo server with process id:{0}'.format(p_pid))
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    try:
        while True:
            print("Waiting for connection...")
            client, addr = s.accept()
            #handle_connection(client,addr)
            with client:
                #client.send(b'Connected by', addr)
                # print("Got connection")
                data = client.recv(1024)
                if not data:
                    break
                elif (data == b'*IDN?\n'):
                    #print('SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
                    client.sendall(b'SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n')
                else:
                    client.sendall(data)
    finally:
        time.sleep(1)
        print('Exiting echo server:'.format(p_pid))
