# Created on 2/1/20 by gurudev
from Hardware.AWG520 import AWG520 # looks like python has no problem finding this when the top-level directory is
# the same as the project name
import subprocess
import socket
import time
import pytest

HOST = '127.0.0.1'  # Standard loopback interface address (localhost), change to '179.17.39.2' for device
PORT = 65432        # Port to listen on (non-privileged ports are > 1023), change to 4000 for device
FTP_PORT = 63217    # Port for ftp testing, change to 21 for device


@pytest.fixture(scope="session")
def awgserver():
    print("loading server")
    p = subprocess.Popen(["python3", "awg_dummy_server.py"])
    time.sleep(1)
    yield p
    p.terminate()


@pytest.fixture
def clientsocket(request):
    print("entering client part")
    server = getattr(request.module, "HOST")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mysock:
        mysock.connect((HOST, PORT))
        yield mysock
        print("finalizing {} ({})".format(mysock, server))
        mysock.close()

# first we test the very basic socket communication which requires strings to be encoded
@pytest.mark.run_this
def test_echo(awgserver, clientsocket):
    clientsocket.send(b"*IDN?\n")
    assert clientsocket.recv(1024) == b"SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0 USR:4.0\n"
    #assert clientsocket.recv(10) == b"TEK" # deliberately make test fail


@pytest.mark.run_this
def test_echo2(awgserver, clientsocket):
    clientsocket.send(b"def")
    assert clientsocket.recv(3) == b"def"

# now we test the AWG520 class
@pytest.mark.run_this
def test_awg520():
    with pytest.raises(AssertionError):
        c = AWG520(HOST,PORT)
        reply = c.set_clock_external()
        assert reply == 'TEK' # deliberate fail to show that pytest will not flag this since it is expected

@pytest.mark.run_this
def test_awg520_2():
    c = AWG520(HOST,PORT)
    reply = c.sendcommand('TRG?')
    assert reply == 'TEK' # deliberate fail to show that pytest will flag this

# when pytest is run with the '-m run_this' flag this test will not be executed
def test_awgfile():
    d = AWGFile(ftype="SEQ")
    from matplotlib import pyplot as plt
    plt.plot(d.sequence.wavedata[1,:])
    plt.show()
    d.write_waveform("test",1,d.sequence.wavedata[0,:],d.sequence.c1markerdata)
    d.write_sequence()

