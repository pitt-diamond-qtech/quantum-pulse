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
import socket,sys, struct,os
import numpy as np
from pathlib import Path
import logging
# from Pulse import Gaussian,Sech,Square,Marker
from .Sequence import Sequence, SequenceList
import time
from source.common.utils import log_with, create_logger,get_project_root



_DAC_BITS = 10
_IP_ADDRESS = '172.17.39.2' # comment out for testing
#_IP_ADDRESS = '127.0.0.1'# use loopback for testing
_PORT = 4000 # comment out for testing
#_PORT = 65432 #switch ports for loopback
_FTP_PORT = 21 # 63217 use this for teting
#_FTP_PORT = 63217
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
# unit conversion factors
_GHz = 1.0e9  # Gigahertz
_MHz = 1.0e6  # Megahertz
_us = 1.0e-6  # Microseconds
_ns = 1.0e-9  # Nanoseconds
sourcedir = get_project_root()
saveawgfilepath = sourcedir /'Hardware/AWG520/sequencefiles/'
# ensure that the awg files can be saved
if not saveawgfilepath.exists():
    os.mkdir(saveawgfilepath)
    print('Creating directory for AWG files at:'.format(saveawgfilepath.resolve()))


# create the logger
privatelogger = create_logger('awg520private')
# privatelogger = logging.getLogger('awg520private')
# privatelogger.setLevel(logging.DEBUG)
# fh = logging.FileHandler((logfilepath / 'qpulse-app.log').resolve())
# fh.setLevel(logging.DEBUG)
# # create a console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.ERROR)
# # create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# fh.setFormatter(formatter)
# ch.setFormatter(formatter)
# # add the handlers to the logger
# privatelogger.addHandler(fh)
# privatelogger.addHandler(ch)



@log_with(privatelogger)
class AWG520(object):
    '''This is the class def for the AWG520. The IP Address and Port default to the ones setup on the AWG.
    Example of how to call and setup the AWG:
        awgcomm = AWG520()
        awgcomm.setup()  -- use this if you want to put the AWG into enhanced run mode to execute sequences from file
        awgcomm.mw_on() - use this if you just want to turn on the MW
        awgcomm.green_on() - or green laser

    '''
    def __init__(self,ip_address=_IP_ADDRESS,port=_PORT):
        self.addr=(ip_address,port)
        self.logger = logging.getLogger('awg520private.awg520cls')
        #logging.basicConfig(format='%(asctime)s %(message)s')
        self.logger.info("Initializing AWG instance...")
        self.logger.debug('AWG model = {}'.format(self.sendcommand('*IDN?')))  # =='SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0
        #print('AWG model = ', self.sendcommand('*IDN?'))
        # USR:4.0\n'
        if self.login_ftp():
           self.awgfiles = self.list_awg_files()
        else:
            raise(IOError("Unable to login via FTP to the device"))

    def sendcommand(self,command):
        query='?' in command
        if not command.endswith('\n'):
            command+='\n'
        try:
            self.logger.info('Sending AWG command: {}'.format(command))
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as self.mysocket:
                self.mysocket.connect(self.addr)
                self.mysocket.sendall(command.encode()) # check if this works with real AWG later
                # TODO: AWG status checking should go here in future
                if query:
                    reply=b''
                    while not reply.endswith(b'\n'):
                        reply+=self.mysocket.recv(1024)
                        self.logger.info('waiting for AWG reply')
                    self.logger.info("Received AWG reply: {}".format(reply.decode()))
                    return reply.decode()
                else:
                    return None
        except IOError as error:
            #sys.stderr.write(sys.exc_info())
            #sys.stderr.write(error.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("OS Error:{0}".format(error))
            return None

    def login_ftp(self):
        try:
            self.myftp = FTP('')
            self.myftp.connect(self.addr[0], port=_FTP_PORT)  # TODO: will need to check FTP port on AWG
            self.myftp.login('usr', 'pw')  # user name and password, these can be anything; no real login
            self.logger.info('FTP login successful')
            return True
        except IOError as err:
            # sys.stderr.write(str(sys.exc_info()[0]))
            # sys.stderr.write(str(sys.exc_info()[1]))
            # sys.stderr.write(e.message+'\n')
            self.logger.error(sys.exc_info())
            self.logger.error("OS Error:{0}".format(err))
            return False

    def sendfile(self,fileRemote,fileLocal):
        try:
            # self.myftp = FTP('')
            # self.myftp.connect(self.addr[0], port=_FTP_PORT)  # TODO: will need to check FTP port on AWG
            # self.myftp.login('usr', 'pw')  # user name and password, these can be anything; no real login
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

    def setup(self,enable_iq=False,seqfilename="scan.seq"):
        '''Sets up the AWG into enhanced run mode. Param to be passed is whether IQ modulator is connected to both
        channels. '''
        self.logger.info('Setting up AWG...')

        self.set_ref_clock_external() # setup the ref to be the Rubidium lab clock
        # self.set_ref_clock_internal() # use the ref to be the internal clock when Rb clock is broken
        time.sleep(0.1)
        self.set_enhanced_run_mode() # put AWG into enhanced run mode when the run command is received
        time.sleep(0.1)
        #self.set_clock_internal() # use the internal clock which is now derived from ext clock
        # load seq to both channels -- I think it may be enough to just load one but will do both
        self.sendcommand('SOUR1:FUNC:USER '+ '"' + str(seqfilename) + '"' +',"MAIN"\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:FUNC:USER '+ '"' + str(seqfilename) + '"' +',"MAIN"\n')
        time.sleep(0.1)

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
        self.sendcommand('SOUR1:VOLT:AMPL 1000mV\n')
        time.sleep(0.1)
        self.sendcommand('SOUR1:VOLT:OFFS 0mV\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:VOLT:AMPL 1000mV\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:VOLT:OFFS 0mV\n')
        time.sleep(0.1)
        '''edited on 8/6/2019 for use w/ IQ modulator: max Vpp = 1.0'''
        self.sendcommand('SOUR1:MARK1:VOLT:LOW 0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR1:MARK1:VOLT:HIGH 2.0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR1:MARK2:VOLT:LOW 0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR1:MARK2:VOLT:HIGH 2.0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:MARK1:VOLT:LOW 0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:MARK1:VOLT:HIGH 2.0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:MARK2:VOLT:LOW 0\n')
        time.sleep(0.1)
        self.sendcommand('SOUR2:MARK2:VOLT:HIGH 2.0\n')
        time.sleep(0.1)

        # turn on channels
        if enable_iq:
            self.sendcommand('OUTP1:STAT ON\n')
            time.sleep(0.1)
            self.sendcommand('OUTP2:STAT ON\n')
            time.sleep(0.1)
        else:
            self.sendcommand('OUTP1:STAT ON\n')
            time.sleep(0.1)
        time.sleep(0.1)

    def run(self):
        self.sendcommand('AWGC:RUN\n')  # runs a sequence in enhanced mode

    def stop(self):
        self.sendcommand('AWGC:STOP\n')

    def set_enhanced_run_mode(self):
        # setup the AWG in enhanced run mode
        self.sendcommand('AWGC:RMOD ENH\n')


    #TODO: these 3 funcs needs to be altered if our connections change
    def green_on(self):
        self.logger.info('turning on green')
        self.sendcommand('SOUR1:MARK2:VOLT:LOW 2.0\n')

    def green_off(self):
        self.logger.info('turning off green')
        self.sendcommand('SOUR1:MARK2:VOLT:HIGH 0.0\n')

    def mw_on_sb10MHz(self,enable_iq = False):
        '''Turns the MW on, param to be passed is whether IQ modulator is connected '''
        self.set_ref_clock_external()  # setup the ref to be the Rubidium lab clock
        # self.set_clock_internal()  # use the internal clock which is now derived from ext clock
        self.sendcommand('SOUR1:MARK1:VOLT:LOW 2.0\n') # doesn't really turn on MW right now since we are using the
        # IQ modulator, so we now use the FG mode to send out sine and cosine waves at 10MHz
        if enable_iq:
            self.sendcommand('AWGC:FG1:FUNC SIN')
            self.sendcommand('AWGC:FG2:FUNC SIN')
            self.sendcommand('AWGC:FG1:FREQ 10MHz')
            self.sendcommand('AWGC:FG2:FREQ 10MHz')
            self.sendcommand('AWGC:FG2:PHAS 90DEG') # channel 2 will output a cosine wave
            self.sendcommand('AWGC:FG1:VOLT 2.0')
            self.sendcommand('AWGC:FG2:VOLT 2.0')
        else:
            self.sendcommand('AWGC:FG1:FUNC SIN')
            self.sendcommand('AWGC:FG1:FREQ 10MHz')
            self.sendcommand('AWGC:FG1:VOLT 2.0')

    def mw_off_sb10MHz(self,enable_iq = False):
        """We assume that we will always call this after a call to mw_on"""
        self.sendcommand('SOUR1:MARK1:VOLT:HIGH 0.0\n') # doesn't really turn off MW right now since we are using the
        # IQ modulator, so we now use the FG mode to send out sine and cosine waves at 10MHz
        if enable_iq:
            self.sendcommand('AWGC:FG1:VOLT 0.0')
            self.sendcommand('AWGC:FG2:VOLT 0.0')
        else:
            self.sendcommand('AWGC:FG1:VOLT 0.0')

    # functions that can help with error checking and remote file manipulation
    def status(self):
        # TODO: this needs to be written referring to section 3-1 of the AWG520 programmer manual
        pass

    def error_check(self):
        pass
    # functions that carry out ftp operations
    def list_awg_files(self):
        return self.myftp.nlst()

    def get_awg_file(self,filename):
        sfile = saveawgfilepath.resolve() + filename
        try:
            self.myftp.retrbinary('RETR '+ filename, open(sfile,'wb').write)
        except IOError as err:
            self.logger.error('IO Error {0}'.format(err))


    def get_select_awg_files(self,pattern):
        awgfiles = self.myftp.nlst()
        patternfiles = []
        t1 = time.process_time()
        try:
            for file in awgfiles:
                if file.count(pattern):
                    patternfiles.append(file)
                    sfile = saveawgfilepath.resolve() + file
                    myftp.retrbinary('RETR ' + file, open(sfile, 'wb').write)
            download_t = time.process_time() - t1
            self.logger.info('time for downloading files is {:.3f}'.format(download_t))
        except IOError as err:
            self.logger.error('IO Error {0}'.format(err))
        return patternfiles

    def remove_awg_file(self,filename):
        """Use with caution : DO NOT delete parameter.dat and leave clocktest wfms on the AWG"""
        try:
            if filename == 'parameter.dat':
                raise ValueError('Cannot delete this file!')
            else:
                self.logger.warning('Deleting AWG file:',filename)
                try:
                    self.myftp.delete(filename)
                except IOError as err:
                    self.logger.error('IO Error {0}'.format(err))
        except ValueError as err:
            self.logger.error('Value Error {0}'.format(err))


    def remove_selected_awg_files(self, pattern):
        awgfiles = self.myftp.nlst()
        patternfiles = []
        t1 = time.process_time()
        try:
            for file in awgfiles:
                if file.count(pattern):
                    patternfiles.append(file)
                    self.remove_awg_file(file)
            delete_t = time.process_time() - t1
            self.logger.warning('Deleted following AWG files:', patternfiles)
            self.logger.info('time for deleting files is {:.3f}'.format(delete_t))
        except IOError as err:
            self.logger.error('IO Error {0}'.format(err))
        return patternfiles

    def get_awg_ftp_status(self):
        pass

    # cleanup the connections
    def cleanup(self):
        self.stop()
        if self.mysocket:
            self.mysocket.close()
        if self.myftp:
            self.myftp.quit()
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
@log_with(privatelogger)
class AWGFile(object):
    def __init__(self,ftype='WFM',timeres=1,dirpath=saveawgfilepath):
        """This class will create and write files of sequences and sequencelists to the default sequencfiles
        directory specified. Args are:
        1. ftype: can be either WFM or SEQ indicating which one you want to write
        2. timeres: clock rate in ns.
        3. dirpath: directory to write the files
         """
        # first we clear out the directory
        self.dirpath = dirpath  # will normally write to sequencefiles directory, change this after initialization if
        # you want the files stored elsewhere.
        for filename in os.listdir(self.dirpath):
            if (filename.endswith('.wfm') or filename.endswith('.seq')):
                #print(filename)  # used this to test that it works correctly
                os.unlink(self.dirpath / filename)

       # now initalize the other variables
        self.logger = logging.getLogger('awg520private.awg520_file')
        self.wfmheader = b'MAGIC 1000 \r\n'
        self.seqheader = b'MAGIC 3002 \r\n'
        self.ftype = ftype
        self.timeres = timeres

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
            #### Major issue discovered on 2021-02-10: wfmlen needs to be divisible by 4
            while wfmlen%4 != 0:
                iqdata = np.append(iqdata,0.0)
                marker = np.append(marker,int(0))
                wfmlen+=1
            #print('wfm length is {0:d} and marker len is {1:d}'.format(len(iqdata),len(marker)))
            if wfmlen >= _WFM_MEMORY_LIMIT:
                raise ValueError('Waveform memory limit exceeded')
                #TODO: perhaps i should implement rewrite the data using a smaller clock rate
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


    def write_waveform(self, sequence:Sequence=None, wavename='0', channelnum=1):
        '''This function writes a new waveform file. the args are:
            sequence: an object of type sequence which has already been created with the data
            wavename: str describing the type of wfm, usually just a number
            channelnum: which channel to use for I/Q and the marker
        '''

        try:
            if not sequence:
                self.logger.error("Invalid sequence or no sequence object given")
                raise ValueError("Invalid sequence or no sequence object given")
            else:
                #sequence.create_sequence() # removed this since we assume data has already been created in sequence obj
                if channelnum == 1:
                    markerdata = sequence.c1markerdata
                    wavedata = sequence.wavedata[0]
                elif channelnum == 2:
                    markerdata = sequence.c2markerdata
                    wavedata = sequence.wavedata[1]
                else:
                    raise ValueError("channel number can only be 1 or 2")
                fname = str(wavename)+'_'+str(channelnum)+str('.wfm')
                wfmfilename =  Path(self.dirpath / fname)
                #print(str(wfmfilename))
                with open(wfmfilename,'wb') as wfile:
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

    def write_sequence(self, sequences:SequenceList=None,seqfilename = 'scan.seq', repeat=50000):
        '''This function takes in a list of sequences generated by the class SequenceList
        The args are:
        sequencelist: list of sequences generated by the object of type SequenceList
        seqfilename: str with seq file name to be written
        repeat: number of repetitions of each waveform
        timeres: clock rate

        It first creates an arm_sequence which is the laser being on and then writes the rest of the sequences that
        are in the sequences object to files.
        '''
        try:
            if not sequences:
                self.logger.error("Invalid sequence or no sequence object given")
                raise ValueError("Invalid sequencelist  or no sequencelist object given")
            else:
                sequences.create_sequence_list()
                slist = sequences.sequencelist # list of sequences
                wfmlen = len(slist[0].c1markerdata) # get the length of the waveform in the first sequence
                scanlen = len(slist)

                # first create an empty waveform in channel 1 and 2 but turn on the green laser
                # so that measurements can start after a trigger is received.
                # ---2021-05-10: modified the arm sequence string because the new Sequence module can directly read
                # the string , but do have to be careful about units again since old code assumed everything in ns
                arm_sequence = Sequence('Green,0,'+str(wfmlen*self.timeres*_ns),timeres=self.timeres)
               # arm_sequence = Sequence([['Wave', '0', str(wfmlen), 'SquareI'], ['Green','0',str(wfmlen)]], timeres=self.timeres)
                arm_sequence.create_sequence()
                self.write_waveform(arm_sequence,'arm', 1)
                self.write_waveform(arm_sequence,'arm', 2)
                # create scan.seq file
                try:
                    fname  = Path(self.dirpath / seqfilename)
                    with open(fname, 'wb') as sfile:
                        sfile.write(self.seqheader)
                        temp_str = 'LINES ' + str(scanlen + 1) + '\r\n'
                        sfile.write(temp_str.encode()) # have to convert to binary format
                        temp_str = '"arm_1.wfm","arm_2.wfm",0,1,0,0\r\n' # the arm sequence will be loaded and will
                        # wait
                        # for trigger
                        sfile.write(temp_str.encode())
                        for i in list(range(scanlen)):
                            # now we take each sequence in the slist arry and write it to a wfm file with the name given by
                            # "i+1_1.wfm and i+1_2.wfm
                            self.write_waveform(slist[i],''+str(i + 1), 1)
                            self.write_waveform(slist[i],''+str(i + 1), 2)
                            # the scan.seq file is now updated to execute those 2 wfms for repeat number of times and wait
                            # for a trigger to move to the next point.
                            linestr = '"'+str(i + 1)+'_1.wfm"'+','+'"'+str(i + 1)+'_2.wfm"'+','+str(repeat)+',1,0,0\r\n'
                            sfile.write(linestr.encode())
                        sfile.write(b'JUMP_MODE SOFTWARE\r\n') # tells the AWG that jump trigger is controlled by the computer.
                except (IOError, ValueError) as error:
                    # sys.stderr.write(sys.exc_info())
                    # sys.stderr.write(error.message+'\n')
                    self.logger.error(sys.exc_info())
                    self.logger.error("Error occurred in either file I/O or data conversion:{0}".format(error))
                    raise
        except (ValueError) as error:
            self.logger.error(sys.exc_info())
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







    