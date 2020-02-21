# Created by Gurudev Dutt <gdutt@pitt.edu> on 1/4/20
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

# this code re-uses parts of Kai Zhang's code for other experiments in our group
# and is still being worked on to make it complete with the new pulse sequences introduced by Gurudev Dutt

from ftplib import FTP
import socket,sys, struct
import numpy as np
from pathlib import Path
import logging
# from Pulse import Gaussian,Sech,Square,Marker
from .Sequence import Sequence, SequenceList
import time

_DAC_BITS = 10
_IP_ADDRESS = '172.17.39.2' # comment out for testing
#_IP_ADDRESS = '127.0.0.1'# use loopback for testing
_PORT = 4000 # comment out for testing
#_PORT = 65432 #switch ports for loopback
_FTP_PORT = 21 # 63217 use this for teting
_MW_S1 = 'S1' #disconnected for now
_MW_S2 = 'S2'#channel 1, marker 1
_GREEN_AOM = 'Green' # ch1, marker 2
_ADWIN_TRIG = 'Measure' # ch2, marker 2
_WAVE = 'Wave' #channel 1 and 2, analog I/Q data
_DAC_UPPER = 1024.0 # DAC has only 1024 levels
_DAC_MID = 512
_WFM_MEMORY_LIMIT = 1048512 # at most this many points can be in a waveform
_SEQ_MEMORY_LIMIT = 8000
_IQTYPE = np.dtype('<f4') # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1') # AWG520 stores marker values as 1 byte

privatelogger = logging.getLogger('awg520private')
dirpath = Path('.') /'sequencefiles'
privatelogger.setLevel(logging.DEBUG)
logfilepath = Path('.')/'logs'
# create a file handler that logs even debug messages
fh = logging.FileHandler((logfilepath / 'awg520private.log').resolve())
fh.setLevel(logging.DEBUG)
# create a console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
privatelogger.addHandler(fh)
privatelogger.addHandler(ch)

class AWG520(object):
    def __init__(self,ip_address=_IP_ADDRESS,port=_PORT):
        self.addr=(ip_address,port)
        self.logger = logging.getLogger('awg520private.awg520cls')
        #logging.basicConfig(format='%(asctime)s %(message)s')
        self.logger.info("Initializing AWG instance...")
        self.logger.debug('AWG model = ', self.sendcommand('*IDN?'))  # =='SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0
        print('AWG model = ', self.sendcommand('*IDN?'))
        # USR:4.0\n'
        self.myftp = FTP('')
        self.myftp.connect(self.addr[0])  # TODO: will need to check FTP port on AWG
        self.myftp.login('usr', 'pw')  # user name and password, these can be anything; no real login
        
    def sendcommand(self,command):
        query='?' in command
        if not command.endswith('\n'):
            command+='\n'
        try:
            self.logger.info('Sending AWG command: %s',command)
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as self.mysocket:
                self.mysocket.connect(self.addr)
                self.mysocket.sendall(command.encode()) # check if this works with real AWG later
                # TODO: AWG status checking should go here in future
                if query:
                    reply=b''
                    while not reply.endswith(b'\n'):
                        reply+=self.mysocket.recv(1024)
                        self.logger.info('waiting for AWG reply')
                    self.logger.info("Received AWG reply: %s", reply.decode())
                    return reply.decode()
                else:
                    return None
        except IOError as error:
            #sys.stderr.write(sys.exc_info())
            #sys.stderr.write(error.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("OS Error:{0}".format(error))
            return None

    def sendfile(self,fileRemote,fileLocal):
        try:
            strIt = 'STOR ' + str(fileRemote)
            self.logger.info('Sending file {} to {}'.format(fileLocal, fileRemote))
            t = time.process_time()
            self.myftp.storbinary(strIt, open(fileLocal, 'rb'))  # store file on awg
            elapsed_time = time.process_time() - t
            self.logger.info("Elapsed time in transferring file is {0:6f} secs".format(elapsed_time))
            # self.myftp.close()
            return 0
        except IOError as err:
            # sys.stderr.write(str(sys.exc_info()[0]))
            # sys.stderr.write(str(sys.exc_info()[1]))
            # sys.stderr.write(e.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("OS Error:{0}".format(err))
            return -1

    def set_clock_external(self):
        self.sendcommand('AWGC:CLOC:SOUR EXT')

    def set_clock_internal(self):
        self.sendcommand('AWGC:CLOC:SOUR INT')

    def set_ref_clock_external(self):
        self.sendcommand('SOUR1:ROSC:SOUR EXT')
        self.sendcommand('SOUR2:ROSC:SOUR EXT')

    def set_ref_clock_internal(self):
        self.sendcommand('SOUR1:ROSC:SOUR INT')
        self.sendcommand('SOUR2:ROSC:SOUR INT')

    def trigger(self):
        self.sendcommand('*TRG\n')

    def event(self):
        self.sendcommand('AWGC:EVEN\n')

    def jump(self, line):
        self.sendcommand('AWGC:EVEN:SOFT ' + str(line) + '\n')

    def setup(self,enableiq=False):
        self.logger.info('Setting up AWG...')

        self.set_clock_external()
        # load seq
        self.sendcommand('SOUR1:FUNC:USER "scan.seq","MAIN"\n')
        self.sendcommand('SOUR2:FUNC:USER "scan.seq","MAIN"\n')

        # set up voltages
        # mysocket.sendall('SOUR2:VOLT:AMPL 2000mV\n')
        # mysocket.sendall('SOUR2:VOLT:OFFS 1000mV\n')
        # '''edited on 8/6/2019 for use w/ IQ modulator: max Vpp = 1.0'''
        # mysocket.sendall('SOUR1:MARK1:VOLT:LOW 0\n')
        # mysocket.sendall('SOUR1:MARK1:VOLT:HIGH 1.9\n')
        # mysocket.sendall('SOUR1:MARK2:VOLT:LOW 0\n')
        # mysocket.sendall('SOUR1:MARK2:VOLT:HIGH 2.0\n')
        # mysocket.sendall('SOUR2:MARK1:VOLT:LOW 0\n')
        # mysocket.sendall('SOUR2:MARK1:VOLT:HIGH 2.0\n')
        # mysocket.sendall('SOUR2:MARK2:VOLT:LOW 0\n')
        # mysocket.sendall('SOUR2:MARK2:VOLT:HIGH 2.0\n')
        self.sendcommand('SOUR2:VOLT:AMPL 2000mV\n')
        self.sendcommand('SOUR2:VOLT:OFFS 1000mV\n')
        '''edited on 8/6/2019 for use w/ IQ modulator: max Vpp = 1.0'''
        self.sendcommand('SOUR1:MARK1:VOLT:LOW 0\n')
        self.sendcommand('SOUR1:MARK1:VOLT:HIGH 1.9\n')
        self.sendcommand('SOUR1:MARK2:VOLT:LOW 0\n')
        self.sendcommand('SOUR1:MARK2:VOLT:HIGH 2.0\n')
        self.sendcommand('SOUR2:MARK1:VOLT:LOW 0\n')
        self.sendcommand('SOUR2:MARK1:VOLT:HIGH 2.0\n')
        self.sendcommand('SOUR2:MARK2:VOLT:LOW 0\n')
        self.sendcommand('SOUR2:MARK2:VOLT:HIGH 2.0\n')

        # turn on channels
        if enableiq:
            self.sendcommand('OUTP1:STAT ON\n')
            self.sendcommand('OUTP2:STAT ON\n')
        else:
            self.sendcommand('OUTP1:STAT ON\n')


    def run(self):
        self.sendcommand('AWGC:RUN\n')  # runs a sequence in enhanced mode

    def stop(self):
        self.sendcommand('AWGC:STOP\n')


    #TODO: these 3 funcs needs to be altered if our connections change
    def green_on(self):
        self.logger.info('turning on green')
        self.sendcommand('SOUR1:MARK2:VOLT:LOW 2.0\n')

    def green_off(self):
        self.logger.info('turning off green')
        self.sendcommand('SOUR1:MARK2:VOLT:HIGH 0.0\n')

    def mw_on(self):
        self.sendcommand('SOUR1:MARK1:VOLT:LOW 2.0\n')

    # cleanup the connections
    def cleanup(self):
        if self.mysocket:
            self.mysocket.close()
        if self.myftp:
            self.myftp.close()
    # functions that can help with error checking and remote file manipulation
    def status(self):
        # TODO: this needs to be written referring to section 3-1 of the AWG520 programmer manual
        pass

    def error_check(self):
        pass

    def list_awg_files(self):
        pass

    def remove_awg_file(self,filename):
        pass

    def remove_all_awg_files(self):
        pass

    def remove_selected_awg_files(self, pattern):
        pass

    def get_awg_ftp_status(self):
        pass


    # def __del__(self):
    #     self.mysocket.close()
    #     self.myftp.close()



"""THE AWG FILE FORMAT: There are 2 types of files, a sequence file which we typically store in NAME.seq and a number of
 waveform files which we store in NAME.wfm. 
 
 WFM files: The .wfm files have a header, body, and a trailer. 
 The header  is the string 'MAGIC 1000 \r\n'
 the body is  #<numdigits><numbytes><data(1)>....<data(n)>
            where num digits is the number of digits in numbytes and numbytes is the byte 
             count of the data that follows 
             <data(i)> is a 5 byte value : the first 4 bytes are teh floating point value in little-endian format for
              teh Analog channel , the full scale of the D/A converter of teh AWG is -1.0 to 1.0
             the 5th byte is one byte of marker data where the bit 0 (LSB) is marker 1 and bit 1 is marker 2
the trailer is the string 'CLOCK <clock> \r\n'
            where <clock> is value of teh sample clock in ASCII
            
SEQUENCE FILES: The sequence files have teh format Header, seq. definition, <optional info>
header is the string 'MAGIC 3002 \r\n' where the 2 in 3002 comes from 2 channels
sequence definition is LINES <N><line(1)><line(2)>....<line(n)>
<N> is the number of lines that follow
<line(n)> is <ch1_filename>, <ch2_filename>, <Repeat count>, [<wait trigger>,[Goto-1,[logic_jump_target]]]\r\n
here <chX_filename> is the wfm file name for the specified channel x (which can be 1 or 2 in AWG520)
    <repeat count> is a integer specifying how many times to repeat , 0 means infinity
    <wait trigger> = 0 means do not wait for trigger, 1 means wait for trigger
    Goto-l  = 0 means do not go to next line, 1 means yes
    Logic-jump target is a integer that is line number for logic-jump, where 0 means off, -1 is next, -2 is table-jump
<optional info> = <Table-jump-table>  <logic_jump-table>  <Jump mode>  <jump_timing> <strobe>
        <table-jump-table> = 'TABLE_JUMP <jump target(1), <jump target 2>...<jump target 16> \r\n'
            where <jump target n> = line number to table-jump or 0 (off)
        <logic-jump-table> = 'LOGIC_JUMP <jump on/off (1)>,<jump on/foff (2), <jump on/off (3), <jump on/off(4) \r\n
            where jump on/off(n) is an integer setting logic-jump on or off, 0 is off, postivie is on, negative is 
            ignore
        <jump-mode> = JUMP_MODE (LOGIC | TABLE | SOFTWARE) \r\n
        <jump-timing> = JUMP_TIMING (SYNC | ASYNC) \r\n 
        <strobe> = STROBE <num> \r \n where <num> = 0 is off for using strobe from event in connector on rear, 1 is on.
         """

class AWGFile(object):
    def __init__(self,sequence = None,sequencelist = None,ftype='WFM',timeres=1,dirpath=dirpath):
        """This class will create and write files of sequences and sequencelists to the default sequencfiles
        directory specified. Args are:
        1. sequence: an object of Sequence type. If you don't specify any, a default sequence is used.
        2. sequencelist: an object of Sequencelist type. If you don't specify any, a default seqlist is used
        3. ftype: can be either WFM or SEQ indicating which one you want to write
        4. timeres: clock rate in ns.
         """
        # first we clear out the directory
        import os
        self.dirpath = dirpath  # will normally write to sequencefiles directory, change this after initialization if
        # you want the files stored elsewhere.
        for filename in os.listdir(self.dirpath):
            if (filename.endswith('.wfm') or filename.endswith('.seq')):
                os.unlink(filename)
                #print(filename) # used this to test that it works correctly
       # now initalize the other variables
        self.logger = logging.getLogger('awg520private.awg520_file')
        self.wfmheader = b'MAGIC 1000 \r\n'
        self.seqheader = 'MAGIC 3002 \r\n'
        # default params if no sequence object is given
        newpulseparams = {'amplitude': 100, 'pulsewidth': 50, 'SB freq': 0.01, 'IQ scale factor': 1.0, 'phase': 0.0,
                     'skew phase': 0.0, 'num pulses': 1}
        delay = [820,10]
        seq = [['S2', '1000', '1400'], ['Wave', '1000', '1400', 'Sech'], ['Green', '1400', '3400']]
        self.timeres = timeres

        if ftype == 'WFM':
            self.sequencelist = None
            if sequence == None:
                self.sequence = Sequence(seq, pulseparams=newpulseparams, timeres=1)
            else:
                self.sequence = sequence
            self.sequence.create_sequence()
        elif ftype == 'SEQ':
            self.sequence = None
            if sequencelist == None:
                newscanparams = {'type': 'amplitude', 'start': 0, 'stepsize': 10, 'steps': 1}
                self.sequences = SequenceList(sequence=seq,delay=delay,scanparams = newscanparams,
                    pulseparams=newpulseparams,timeres=1)
            else:
                self.sequences = sequencelist
            self.sequences.create_sequence_list()
        else:
            self.logger.error('AWG File type has to be either WFM or SEQ')
            raise ValueError('AWG File type has to be either WFM or SEQ')

        self.logger.info("Initializing AWG File instance of type:{0}".format(ftype))


    def maketrailer(self):
        #trailer = 'CLOCK 1.0000000000E+07\r\n' # default clock value is 100 ns
        if self.timeres == 1:
          trailer = b'CLOCK 1.0000000000E+9\r\n'
        elif self.timeres == 5:
            trailer = b'CLOCK 2.0000000000E+08\r\n'
        elif self.timeres == 10:
            trailer = b'CLOCK 1.0000000000E+08\r\n'
        elif self.timeres == 25:
            trailer = b'CLOCK 4.0000000000E+07\r\n'
        elif self.timeres == 100:
            trailer = b'CLOCK 1.0000000000E+07\r\n'
        else:
            raise ValueError
        return trailer

    def binarymaker(self,iqdata,marker):
        '''This function makes binary strings to write to the wfm file from the I/Q data and marker data'''
        try:
            wfmlen = len(iqdata)
            if wfmlen >= _WFM_MEMORY_LIMIT:
                raise ValueError('Waveform memory limit exceeded')
            elif wfmlen == len(marker):
                # analog I/Q data converted to 4 byte float, marker to 1 byte , both little-endian
                record = struct.pack('<fb', iqdata[0], marker[0])
                i = 1
                recordsize = struct.calcsize('<fb')
                numbytes = wfmlen * recordsize
                t = time.process_time()
                while (i < wfmlen):
                    record += struct.pack('<fb', iqdata[i], marker[i])
                    i += 1
                elapsed_time = time.process_time() - t
                self.logger.info("Elapsed time in creating binary record is {0:6f} secs".format(elapsed_time))
                return (numbytes, recordsize, record)
            else:
                raise ValueError('length of marker and analog data must be same')
        except ValueError as err:
            self.logger.error("Value Error {0}:".format(err))
            self.logger.error(sys.exc_info())
            return (None,None,None)


    def write_waveform(self, wavename, channelnum, wavedata,markerdata):
        '''This function writes a new waveform file. the args are:
            wavename: str describing the type of wfm, usually just a number
            channelnum: which channel to use for I/Q and the marker
            wavedata: the I/Q data, a single array of floats
            markerdata: the marker data, a single array of ints
        '''
        try:
            wfmfilename =  str(wavename)+'_'+str(channelnum)+str('.wfm')
            with open(self.dirpath/wfmfilename,'wb') as wfile:
                wfile.write(self.wfmheader)
                nbytes, rsize, record = self.binarymaker(wavedata, markerdata)
                # next line converts nbytes to a str, and then finds number of digits in str and writes it to file as a str
                nbytestr = '#' + str(len(str(nbytes))) + str(nbytes)
                wfile.write(nbytestr.encode())
                wfile.write(record)
                wfile.write(self.maketrailer())
        except (IOError,ValueError) as error:
            # sys.stderr.write(sys.exc_info())
            # sys.stderr.write(error.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("Error occurred in either file I/O or data provided:{0}".format(error))
            raise

    def write_sequence(self, seqfilename = 'scan.seq', repeat=50000):
        '''This function takes in a list of sequences generated by the class SequenceList
        The args are:
        seqfilename: str with seq file name to be written
        repeat: number of repetitions of each waveform
        timeres: clock rate
        '''
        # first create an empty waveform so that measurements can start after a trigger is received.
        slist = self.sequences.sequencelist
        wfmlen = len(slist[0].c1markerdata)
        scanlen = len(slist)
        c1m1 = np.zeros(wfmlen,dtype=_MARKTYPE)
        c2m1 = np.zeros(wfmlen,dtype=_MARKTYPE)
        wave = np.zeros((2,wfmlen),dtype = _IQTYPE)
        self.write_waveform('0', 1, wave[0,:], c1m1)
        self.write_waveform('0', 2, wave[1,:], c2m1)
        # create scan.seq file
        try:
            with open(self.dirpath / seqfilename, 'w') as sfile:
                sfile.write(self.seqheader)
                sfile.write('LINES ' + str(scanlen + 1) + '\r\n')
                sfile.write('"0_1.wfm","0_2.wfm",0,1,0,0\r\n')
                for i in list(range(scanlen)):
                    self.write_waveform('' + str(i + 1), 1, slist[i].wavedata[0, :], slist[i].c1markerdata)
                    self.write_waveform('' + str(i + 1), 2, slist[i].wavedata[1, :], \
                        slist[i].c2markerdata)
                    linestr = '"' + str(i + 1) + '_1.wfm"' + ',' + '"' + str(i + 1) + '_2.wfm"' + ',' + str(repeat) \
                              + ',1,0,0\r\n'
                    sfile.write(linestr)
                sfile.write('JUMP_MODE SOFTWARE\r\n')
        except (IOError, ValueError) as error:
            # sys.stderr.write(sys.exc_info())
            # sys.stderr.write(error.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("Error occurred in either file I/O or data conversion:{0}".format(error))
            raise

    def setwaveform(self, wavenum, wavedata,markerdata):
        pass

    def addwaveform(self, elementnum, channelnum, wavename):
        pass

    def waittrigger(self, elementnum, trigger):
        pass

    def jump(self, elementnum, jumpindex=0):
        pass

    def repeat(self, elementnum, repeatnum):
        pass

    def goto_state(self, elementnum, gotonum):
        pass







    