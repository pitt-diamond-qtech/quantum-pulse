# Created by Gurudev Dutt <gdutt@pitt.edu> on 1/16/20
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
#!/usr/bin/env python3

import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

# this server simulates the AWG command protocol, simply echoing the command back except for IDN?
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    try:
        while True:
            print('waiting for connection')
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
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
