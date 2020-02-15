# Created by Gurudev Dutt <gdutt@pitt.edu> on 1/31/20
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

"""The purpose of this code is to simulate an FTP server on the AWG which will take the wfm files
and seq files and upload them."""
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 63217        # Port to listen on (non-privileged ports are > 1023)
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer,FTPServer
import os
import logging

class MyHandler(FTPHandler):
    def on_connect(self):
        print("{0}:{1} connected".format(self.remote_ip, self.remote_port))

    def on_disconnect(self):
        # do something when client disconnects
        pass

    def on_login(self, username):
        # do something when user login
        pass

    def on_logout(self, username):
        # do something when user logs out
        pass

    def on_file_sent(self, file):
        # do something when a file has been sent
        pass

    def on_file_received(self, file):
        # do something when a file has been received
        pass

    def on_incomplete_file_sent(self, file):
        # do something when a file is partially sent
        pass

    def on_incomplete_file_received(self, file):
        # remove partially uploaded files
        os.remove(file)

def main():
    authorizer = DummyAuthorizer()
    authorizer.add_user("usr", "pw", "./dummyAWG", perm="elradfmw")
    authorizer.add_anonymous("./dummyAWG")
    logging.basicConfig(filename='./logs/pyftpd.log', level=logging.INFO)

    handler = MyHandler
    handler.authorizer = authorizer

    server = ThreadedFTPServer((HOST, PORT), handler)
    server.serve_forever()

if __name__ == '__main__':
    main()