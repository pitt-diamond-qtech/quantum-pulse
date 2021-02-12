# Created by Gurudev Dutt <gdutt@pitt.edu> on 12/24/19
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

# this code is heavily based on Kai Zhang's code for other experiments in our group
# and is still being worked on to make it complete with the new pulse sequences introduced by Gurudev Dutt

from PyQt5 import QtCore
from source.Hardware.AWG520 import AWG520
from source.Hardware.AWG520.AWG520 import AWGFile
from source.Hardware.AWG520.Sequence import Sequence,SequenceList
from source.Hardware.PTS3200.PTS import PTS
from source.Hardware.MCL.NanoDrive import MCL_NanoDrive
from source.common.utils import log_with, create_logger,get_project_root
import time,sys,multiprocessing
import logging
_PTS_PORT = 'COM3'   #---2021-02-09: new PTS com port

import ADwin,os

from pathlib import Path

# hwdir  = Path('.')
# dirPath = hwdir / 'AWG520/sequencefiles/'
sourcedir = get_project_root()
#print(sourcedir)
dirPath = Path(sourcedir / 'Hardware/AWG520/sequencefiles/') # remove the tests part of the string later

modlogger = create_logger('threadlogger')
# modlogger.setLevel(logging.DEBUG)
# # create a file handler that logs even debug messages
# fh = logging.FileHandler('./logs/threadlog.log')
# fh.setLevel(logging.DEBUG)
# # create a console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.ERROR)
# # create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# fh.setFormatter(formatter)
# ch.setFormatter(formatter)
# # add the handlers to the logger
# modlogger.addHandler(fh)
# modlogger.addHandler(ch)

_GHZ = 1000000000
_MHZ = 1000000

@log_with(modlogger)
class UploadThread(QtCore.QThread):
    """this is the upload thread to send all the files to teh AWG. it has following variables:
    1. seq = the sequence list of strings
    2. scan = scan parameters dictionary
    3. params = misc. params list such as count time etc
    4. awgparams = awg params dict
    5. pulseparams = pulseparams dict
    6. mwparams = mw params dict
    7. timeRes = awg clock rate in ns

    This class emits one Pyqtsignal
    1. done  - when the upload is finished
    """
    # this method only has one PyQt signal done which is emitted once the upload is finished
    done=QtCore.pyqtSignal()
    def __init__(self,parent=None, dirPath=dirPath):
        #super().__init__(self)
        QtCore.QThread.__init__(self,parent)
       # self.timeRes = timeRes
        self.logger = logging.getLogger('threadlogger.uploadThread')
        self.dirPath = dirPath
        # 2020-07-21: due to random crashes with QT when upload button is pressed , we are now writing the files in
        # the main app, and only using this thread to upload the files to the AWG.
        # -------------------------- uncomment this block if you want to go back ----------------------------
        # if scan == None:
        #     self.scan = dict([('type', 'amplitude'), ('start', '0'), ('stepsize', '50'), ('steps', '20')])
        # else:
        #     self.scan = scan
        # if seq == None:
        #     self.seq = [['Green','0','1000'],['Measure','10','400']] # minimal measurement sequence
        # else:
        #     self.seq = seq
        # if mwparams == None:
        #     self.mw = {'PTS': [True, '2.870', False, '2.840', '0.001', '100', '2.940'], \
        #                'SRS': [False, '2.870', False, '2.840','0.001', '100', '2.940']}
        # else:
        #     self.mw = mwparams
        # if awgparams == None:
        #     self.awgparams = {'awg device': 'awg520', 'time resolution': 1, \
        #                     'pulseshape': 'Square', 'enable IQ': False, 'iterate pulses': False, 'num pulses': 1}
        # if pulseparams == None:
        #     self.pulseparams = {'amplitude': 0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
        #                         'phase': 0.0, 'skew phase': 0.0}
        # if params == None:
        #     self.parameters = [50000, 300, 1000, 10, 50, 820, 10]
                                # should make into dictionary with keys 'sample', 'count time',
                                # 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay'

    def run(self):
        # ----------------- lines below commented out on 2021-02-07 to avoid writing to disk
        # create files
        samples = self.parameters[0]
        delay = self.parameters[-2:]

        # enable_scan_pts = self.mw['PTS'][2]
        scan_carrier_freq = (self.scan['type'] == 'frequency')
        # do_enable_iq = self.awgparams['enable IQ']
        # npulses = self.pulseparams['num pulses']
        if scan_carrier_freq:
            # we can scan frequency either using PTS or using the SB freq
            #self.scan['type'] = 'frequency'
            self.scan['type'] = 'no scan' # this tells the SeqList class to simply put one sequence as the PTS will
            # scan the frequency
        # now create teh sequences
        self.sequences = SequenceList(sequence=self.seq, delay=delay,pulseparams = self.pulseparams,scanparams = self.scan, timeres=self.timeRes)
        # write the files to the AWG520/sequencefiles directory
        self.awgfile = AWGFile(ftype='SEQ',timeres = self.timeRes)
        self.awgfile.write_sequence(sequences=self.sequences,seqfilename="scan.seq",repeat= samples)
        # -----------------------------------------------------------------------------------------------
        # now upload the files
        # self.done.emit()
        # uncomment these lines when you are ready to connect to the AWG --------------------------------------------
        try:
            if self.awgparams['awg device'] == 'awg520':
                # print("Upload OK!")
                self.awgcomm = AWG520()
                # transfer all files to AWG
                t = time.process_time()
                for filename in os.listdir(self.dirPath):
                    self.awgcomm.sendfile(filename, self.dirPath / filename)
                transfer_time = time.process_time() - t
                time.sleep(1)
                self.logger.info('time elapsed for all files to be transferred is:{0:.3f} seconds'.format(
                    transfer_time))
                self.awgcomm.cleanup()
                self.done.emit()
            else:
                raise ValueError('AWG520 is the only AWG supported')
        except ValueError as err:
            self.logger.error('Value Error {0}'.format(err))
        except RuntimeError as err:
            self.logger.error('Run time error {0}'.format(err))
        #--------------------------------------------------------------------------------------------------------



@log_with(modlogger)
class ScanThread(QtCore.QThread):
    """this is the Scan thread. it has following variables:
        1. seq = the sequence list of strings
        2. scan = scan parameters dictionary
        3. params = misc. params list such as count time etc
        4. awgparams = awg params dict
        5. pulseparams = pulseparams dict
        6. mwparams = mw params dict
        7. timeRes = awg clock rate in ns
        8. maxcounts = observed max. counts

        This has 2 pyqtsignals
        1. data = a tuple of 2 integers which contain sig and ref counts
        2. tracking - integer with tracking counts
        """
    # declare the pyqtsignals (i) data which emits signal and ref counts , (ii) tracking which emits the tracking
    # counts
    data=QtCore.pyqtSignal(int,int)
    tracking=QtCore.pyqtSignal(int)

    def __init__(self,parent=None,scan = None,params = None,awgparams = None,pulseparams = None,mwparams = None, \
                 timeRes = 1,maxcounts=100):
        #QtCore.QThread.__init__(self,parent)
        super().__init__(parent)
        self.timeRes = timeRes
        self.maxcounts = maxcounts
        self.logger = logging.getLogger('threadlogger.scanThread')
        if scan == None:
            self.scan = dict([('type', 'amplitude'), ('start', '0'), ('stepsize', '50'), ('steps', '20')])
        else:
            self.scan = scan
        if mwparams == None:
            self.mw = {'PTS': [True, '2.870', False, '2.840', '0.001', '100', '2.940'], \
                       'SRS': [False, '2.870', False, '2.840', '0.001', '100', '2.940']}
        else:
            self.mw = mwparams
        if awgparams == None:
            self.awgparams = {'awg device': 'awg520', 'time resolution': 1, \
                              'pulseshape': 'Square', 'enable IQ': False}
        if pulseparams == None:
            self.pulseparams = {'amplitude': 0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
                                'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
        if params == None:
            self.parameters = [50000, 300, 1000, 10, 50, 820, 10]
            # should make into dictionary with keys 'sample', 'count time',
            # 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay'


    def run(self):
        import pydevd
        pydevd.settrace(suspend=False, trace_only_current_thread=True)
        self.scanning=True
        self.proc_running=True

        self.p_conn,c_conn=multiprocessing.Pipe() # create parent and child connectors
        # give the process the child connector and all the params
        #self.proc = ScanProcess(conn = c_conn,parameters= self.parameters,mwparams=self.mw,scan=self.scan,
                                # awgparams=self.awgparams,maxcounts=self.maxcounts,timeRes=self.timeRes)
        self.proc = ScanProcess()
        self.proc.get_conn(c_conn)
        # pass the parameters to the process
        self.proc.parameters=self.parameters
        # # pass the mw info
        self.proc.mw=self.mw
        # # pass the scan info
        self.proc.scan=self.scan
        # # pass the awg info
        self.proc.awgparams = self.awgparams
        # # keep track of the maxcounts
        # self.maxcounts = maxcounts
        self.proc.maxcounts=self.maxcounts
        # start the scan process
        self.proc.start()
        # TODO: verify whether proc.join() is needed here

        threshold = self.parameters[4]
        while self.scanning:
            if self.p_conn.poll(1): # check if there is data
                reply=self.p_conn.recv() # get the data
                self.logger.info('reply is {} '.format(reply))
                # 3/6/20 - I noticed this next line sends the proc_running parameter which is never really altered
                # by the main thread, whereas the param scanning is altered depending on the reply from the process,
                # therefore I believe this line was a mistake and the new line I have added should be correct
                # self.p_conn.send((threshold,self.proc_running))
                # send the scan process the threshold and whether to keep running
                self.p_conn.send((threshold,self.scanning))
                if reply=='Abort!':
                    self.scanning = False
                    self.logger.debug('reply is {}'.format(reply))
                    break
                elif type(reply) is int: # if the reply is tracking counts, send that signal to main app
                    self.tracking.emit(reply)
                    self.logger.debug('reply emitted from tracking is {}'.format(reply))
                elif len(reply)==2:
                    self.data.emit(reply[0],reply[1]) # if the reply is a tuple with signal and ref,send that signal to main app
                    self.logger.debug('signal and ref emitted is {0:d} and {1:d}'.format(reply[0],reply[1]))


class Abort(Exception):
    pass


class ScanProcess(multiprocessing.Process):
    """This is where teh scanning actually happens. It inherits nearly all the same params as the ScanThread, except for
    one more parameter: conn which is the child connector of the Pipe used to communicate to ScanThread."""
    # def __init__(self,parent=None, conn = None,scan = None,parameters = None,awgparams = None,pulseparams = None,
    #              mwparams =None, timeRes = 1,maxcounts=100):
    #     super().__init__(parent)
    #     self.timeRes = timeRes
    #     self.maxcounts = maxcounts
    #     self.logger = logging.getLogger('threadlogger.scanThread.scanproc')
    #     if scan == None:
    #         self.scan = dict([('type', 'amplitude'), ('start', '0'), ('stepsize', '50'), ('steps', '20')])
    #     else:
    #         self.scan = scan
    #     if mwparams == None:
    #         self.mw = {'PTS': [True, '2.870', False, '2.840', '0.001', '100', '2.940'], \
    #                    'SRS': [False, '2.870', False, '2.840', '0.001', '100', '2.940']}
    #     else:
    #         self.mw = mwparams
    #     if awgparams == None:
    #         self.awgparams = {'awg device': 'awg520', 'time resolution': 1, \
    #                           'pulseshape': 'Square', 'enable IQ': False}
    #     else:
    #         self.awgparams = awgparams
    #     if pulseparams == None:
    #         self.pulseparams = {'amplitude': 0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
    #                             'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
    #     else:
    #         self.pulseparams = pulseparams
    #     if parameters == None:
    #         self.parameters = [50000, 300, 1000, 10, 50, 820, 10]
    #     else:
    #         self.parameters = parameters
    #
    #         # should make into dictionary with keys 'sample', 'count time',
    #         # 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay'
    #     self.conn = conn
    #     self.scanning = False
    #     self.initialize()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger('threadlogger.scanproc')

    def get_conn(self, conn):
        self.conn = conn
        self.scanning = False

    #@log_with(modlogger)
    def initialize(self):
        # for some reason the initialization was not previously carried out in an __Init__ , at first i didnt't want to change this at the moment
        # since it was working with the hardware. But will give it a try
        count_time = self.parameters[1]
        reset_time = self.parameters[2]
        samples = self.parameters[0]
        threshold = self.parameters[4]
        numavgs = self.parameters[3]
        start = float(self.scan['start'])
        step = float(self.scan['stepsize'])
        numsteps = int(self.scan['steps'])
        use_pts = self.mw['PTS'][0]
        enable_scan_pts = self.mw['PTS'][2]
        current_freq = float(self.mw['PTS'][1])
        start_freq = float(self.mw['PTS'][3])
        step_freq = float(self.mw['PTS'][4])
        num_freq_steps = float(self.mw['PTS'][5])
        stop_freq = float(self.mw['PTS'][6])
        do_enable_iq = self.awgparams['enable IQ']
        self.adw = ADwin.ADwin()
        try:
            # boot the adwin with the bootloader
            self.adw.Boot(self.adw.ADwindir + 'ADwin11.btl')
            # Measurement protocol is configured as process 2, external triggered
            measure_proc = os.path.join(os.path.dirname(__file__), 'AdWIN',
                                        'Measure_Protocol.TB2')
            self.adw.Load_Process(measure_proc)
            # TrialCounter is configured as process 1
            count_proc = os.path.join(os.path.dirname(__file__),
                                      'ADWIN\\TrialCounter.TB1')
            self.adw.Load_Process(count_proc)
            # TODO: set the parameters in the ADWIN -- check the .BAS files
            # from what I could tell of Adbasic, these values seem to be ignored in the Measure protocol
            # double check with Elijah and maybe correct the .bas file
            self.adw.Set_Par(3, count_time)
            self.adw.Set_Par(4, reset_time)
            self.adw.Set_Par(5, samples)
            # start the Measure protocol
            self.adw.Start_Process(2)
            self.logger.info('Adwin parameter 5 is {:d}'.format(self.adw.Get_Par(5))) # seem to be printing the samples
            # value
            # again?

        except ADwin.ADwinError as e:
            sys.stderr.write(e.errorText)
            self.conn.send('Abort!')
            self.scanning = False


        # initialize the PTS and output the current frequency
        if use_pts:
            self.pts = PTS(_PTS_PORT)
            self.pts.write(int(current_freq * _MHZ))
        else:
            self.logger.error('No microwave synthesizer selected')
        self.awgcomm = AWG520()
        self.awgcomm.setup(enable_iq=True, seqfilename="scan.seq")  #removed the setup of AWG in Upload thread,
        # so do it now.
        time.sleep(0.2)
        self.awgcomm.run()  # places the AWG into enhanced run mode.
        time.sleep(0.2)

    #@log_with(modlogger)
    def run(self):
        self.scanning=True
        self.initialize() # why is initialize called in run? it would seem best to initialize hardware first

        numavgs = self.parameters[3]
        start = float(self.scan['start'])
        step = float(self.scan['stepsize'])
        numsteps = int(self.scan['steps'])
        use_pts = self.mw['PTS'][0]
        scan_carrier_freq = (self.scan['type'] == 'frequency')
        current_freq = float(self.mw['PTS'][1])
        # start_freq = float(self.mw['PTS'][3])
        # step_freq = float(self.mw['PTS'][4])
        # num_freq_steps = float(self.mw['PTS'][5])
        # stop_freq = float(self.mw['PTS'][6])
        # do_enable_iq = self.awgparams['enable IQ']
        # TODO: this is still a bit ugly but because I moved the number of pulses to be scanned into pulseparams
        # TODO: I need to check if the iterate pulses is on.
        # TODO: maybe simples if in the main GUI i simply replace the scan line edits and do strict type checking in the app
        # TODO: above todo is now nearly implemented but keeping it here jic i forgot something.
        # npulses = self.pulseparams['numpulses']
        # if self.scan['type'] == 'frequency':
        #     # we can scan frequency either using PTS or using the SB freq, but if we are scanning a wide range using
        #     # the PTS we must simply output the sequence specified by user on the AWG.
        #     # self.scan['type'] = 'frequency'
        #     num_scan_points = num_freq_steps
        # else:
        #     num_scan_points = numsteps

        try:
            for avg in list(range(numavgs)): # we will keep scanning for this many averages
                self.awgcomm.trigger() # trigger the awg for the arm sequence which turns on the laser.
                time.sleep(0.2) # Not sure why but shorter wait time causes problem.
                for x in list(range(numsteps)):
                    self.logger.info('The current avg. is No.{:d}/{:d} and the the current point is {:d}/{:d}'.format(
                        avg,numavgs,x,numsteps))
                    if not self.scanning:
                        raise Abort()
                    if use_pts and scan_carrier_freq: # this part implements frequency scanning
                        freq=int((start+ step * x)* _MHZ)
                        temp=1
                        # try to communicate with PTS and make sure it has put out the right frequency
                        while not (self.pts.write(freq)):
                            time.sleep(temp)
                            temp*=2
                            if temp>10:
                                self.pts.__init__()
                                temp=1
                    # get the signal and reference data
                    sig,ref=self.getData(x)
                    #print('id and value are',id(self.parameters[4]),self.parameters[4])
                    threshold = self.parameters[4]
                    # track the NV position if the reference counts is too low
                    while ref< threshold:
                        if not self.scanning:
                            raise Abort()
                        self.finetrack()
                        sig,ref=self.getData(x,'jump') # we have to execute the sequence again.
                        if sig==0:
                            self.logger.warning('sig is 0 ,executing again')
                            sig,ref=self.getData(x,'jump')
                        
                    self.conn.send([sig,ref])
                    self.logger.info('signal {0:d} and reference {1:d} sent from ScanProc to ScanThread'.format(sig,
                        ref))
                    self.conn.poll(None)
                    self.parameters[4],self.scanning = self.conn.recv() # receive the threshold and scanning status
        except Abort:
            self.conn.send('Abort!')
            
        self.cleanup()

    #@log_with(modlogger)
    def getData(self,x,*args):
        '''This is the main function that gets the data from teh Adwin.
        to understand the code, it helps to know that the AWGFile class that was used to upload the sequences first
        creates an arm_sequence which is the 1st line in the scan.seq file. The 2md line of the scan.seq file will
        therefore be the 1st point in the scan list and so on. The arm_sequence is executed during the
        finetrack function when the counts from NV are low. There are 3 possible ways getData function is called:
            getData(0) = 1st time getData is called it will jump to the 2nd line of the scan.seq file which
            corresponds to the first actual point in the scan. it will then trigger to output that wfm on the AWG
            getData(x) = not the 1st time, will direct trigger to output the current line of the scan.seq file and
            move to the next
            getData(x,'jump') = including the case x = 0, this is called when we finished tracking and maximizing
            counts using fine_track func. If we have taken x points of data and now want to move to the (x+1)th
            point, then the scan index is x (because python indexing starts at 0 for lists). So again when we come
            back from finetrack, we need to jump the (x+2) line of the scan.seq function and output that wfm by
            triggering. For some reason the trigger has to be done twice here according to Kai Zhang.
            Thus the params to be sent are:
            1. x : data point number
            2. args : only one arg 'jump' is supported at this time
        '''
        modlogger.info('entering getData with arguments data point {0:d}, and {1:}'.format(x,args))
        flag=self.adw.Get_Par(10)
        self.logger.info('Adwin Par_10 is {0:d}'.format(flag))
        
        if x==0 or args!=(): # if this is the first point we need to jump over the arm_sequence to the 2nd line of
            # scan.seq. If not first point, we still need to add 2 again to get to the right line number
            self.awgcomm.jump(x+2)
            time.sleep(0.005)  # This delay is necessary. Otherwise neither jump nor trigger would be recognized by awg.

        self.awgcomm.trigger() # now we output the line number in the scan.seq file
        
        if args!=():
            time.sleep(0.1)
            self.awgcomm.trigger() # if the arg is 'jump' we have to trigger again for some reason.
            
        # wait until data updates
        while flag==self.adw.Get_Par(10):
            time.sleep(0.1)
            self.logger.info(f'Adwin Par_20 is {self.adw.Get_Par(20):d}')
            
        sig=self.adw.Get_Par(1)
        ref=self.adw.Get_Par(2)

        return sig,ref
    
    def track(self):
        self.axis='z'
        position = self.nd.SingleReadN(self.axis, self.handle)
    
    def finetrack(self):
        modlogger.info('entering tracking from ScanProc')
        self.adw.Stop_Process(2)
        
        self.awgcomm.jump(1) # jumping to line 1 which turns the green light on
        time.sleep(0.005)  # This delay is necessary. Otherwise neither jump nor trigger would be recognized by awg.
        self.awgcomm.trigger()

        self.nd=MCL_NanoDrive()
        self.handle=self.nd.InitHandles()['L']
        self.accuracy=0.025
        self.axis='x'
        self.scan_track()
        self.axis='y'
        self.scan_track()
        self.axis='z'
        self.scan_track(ran=0.5) # increase range for z
        self.nd.ReleaseAllHandles()
        
        self.adw.Start_Process(2)
        time.sleep(0.3)
        
    def go(self,command):
        # we need to check if the position has really gone to the command position
        position = self.nd.SingleReadN(self.axis, self.handle)
        i=0
        while abs(position-command)>self.accuracy:
            #print 'moving to',command,'from',position
            self.logger.info(f'moving to {command} from {position}')
            position=self.nd.MonitorN(command, self.axis, self.handle)
            time.sleep(0.1)
            i+=1
            if i==20:
                break

    def count(self):
        # this function uses the Adwin process 1 to simply record the counts
        self.adw.Start_Process(1)
        time.sleep(1.01) # feels like an excessive delay, check by decreasing if it can be made smaller
        counts=self.adw.Get_Par(1)
        self.adw.Stop_Process(1)
        return counts
    
    def scan_track(self,ran=0.25,step=0.05):
        '''This is the function that maximizes the counts by scanning a small range around the current position.
        Params are
         1. ran : range to scan in microns ie 250 nm is default
         2. step = step size in microns, 50 nm is default'''
        positionList=[]
        position = self.nd.SingleReadN(self.axis, self.handle)
        counts_data=[]
        p=position-ran/2
        while p<=position+ran/2:
            positionList.append(p)
            p+=step
        for each_position in positionList:
            self.go(each_position)
            data=self.count()
            self.conn.send(data)
            self.conn.poll(None)
            r=self.conn.recv()
            self.parameters[4]=r[0]
            counts_data.append(data)
        
        self.go(positionList[counts_data.index(max(counts_data))])
        
    def cleanup(self):
        self.awgcomm.stop()
        self.awgcomm.cleanup()
        self.adw.Stop_Process(2)
        #self.amp.switch(False)
        self.pts.cleanup()
        
@log_with(modlogger)
class KeepThread(QtCore.QThread):
    """This thread should be run automatically after the scan thread is done, so as to keep the NV in focus even when the user
    is not scanning. It works on a very similar basis as the scan thread. It has one signal:
        1. status = string which updates the main app with the counts"""

    status=QtCore.pyqtSignal(str)
    
    def __init__(self,parent=None):
        super().__init__(parent)
        self.running=False
        self.logger = logging.getLogger('threadlogger.KeepThread')

    def run(self):
        self.running=True
        # create the keep process in a separate process and pass it a child connector
        self.p_conn,c_conn=multiprocessing.Pipe()
        self.proc = KeepProcess(conn=c_conn)
        self.proc.start() # start the keep process
        while self.running:
            self.logger.info('keep process still running')
            if self.p_conn.poll(1):
                reply=self.p_conn.recv()
                if reply=='t': # if the reply from Keep process is t, then it is tracking
                    self.status.emit('Tracking...')
                    self.logger.debug('signal emitted by KeepThread is Tracking..')
                elif reply[0]=='c': # if the reply starts with c, then we can get the counts
                    self.status.emit('Monitoring counts...'+reply[1:])
                    self.logger.debug('signal emitted by KeepThread is Monitoring counts...{0}'.format(reply[1:]))
        #self.logger.info('keep thread stopping')
        self.p_conn.send(False)
        while self.proc.is_alive():
            self.logger.info('keep proc still alive {0}'.format(id(self.proc.running)))
            time.sleep(1)
        self.status.emit('Ready!') # we finished the keep process and can now go back to main program
        
class KeepProcess(multiprocessing.Process):
    def __init__(self,parent,conn):
        super().__init__(parent)
        self.conn = conn
        self.running = False
        self.logger = logging.getLogger('threadlogger.KeepThread.keepproc')
        self.initialize()
        self.accuracy = 0.025 # accuracy for moves of nanostage is 25 nm
        self.count_threshold_percent = 0.7

    def run(self):
        self.logger.info('keep process starts')
        self.running=True
        time.sleep(5) # wait 5 seconds before counting again
        
        maxcount=self.count()
        self.conn.send('c'+str(maxcount))
        time.sleep(5) # wait 5 seconds before counting again
        
        
        while not self.conn.poll(0.01):
            # self.logger.info('keep process did not receive anything.')
            c=self.count()
            if float(c)/maxcount<self.count_threshold_percent: # if the counts fall below threshold
                self.conn.send('t') # tell Keep thread that we are now tracking
                self.track()
                maxcount=self.count()
                self.conn.send('c'+str(maxcount))
            time.sleep(5)
        
        self.cleanup()
        
    def initialize(self):
        self.nd=MCL_NanoDrive()
        self.adw=ADwin.ADwin()
        self.awgcomm = AWG520()

        try:
            self.adw.Boot(self.adw.ADwindir + 'ADwin11.btl')
            count_proc = os.path.join(os.path.dirname(__file__),'ADWIN\\TrialCounter.TB1') # TrialCounter is configured as process 1
            self.adw.Load_Process(count_proc)
        except ADwin.ADwinError as e:
            sys.stderr.write(e.errorText)
            self.conn.send('Abort!')
            self.running=False
            
            
    def track(self):
        self.logger.info('entered track function')
        
        self.handle=self.nd.InitHandles()['L']
        # track each axis one by one
        self.axis='x'
        self.scan_track()
        self.axis='y'
        self.scan_track()
        self.axis='z'
        self.scan_track()
        
        
    def go(self,command):
        ''' this function moves nanostage to the position given by param:
        1. command'''
        position = self.nd.SingleReadN(self.axis, self.handle)
        while abs(position-command)>self.accuracy:
            #print 'moving to',command,'from',position
            position=self.nd.MonitorN(command, self.axis, self.handle)
            time.sleep(0.1)

    def count(self):
        '''this function uses the Adwin process 1 to simply record the counts '''
        self.awgcomm.green_on()
        self.adw.Start_Process(1)
        time.sleep(1.01) # very long delay, check if truly needed
        counts=self.adw.Get_Par(1)
        self.adw.Stop_Process(1)
        self.awgcomm.green_off()
        return counts
    
    def scan_track(self,ran=0.5,step=0.05):
        '''This is the function that maximizes the counts by scanning a small range around the current position.
        Params are
         1. ran : range to scan in microns ie 500 nm is default
         2. step = step size in microns, 50 nm is default'''
        positionList=[]
        position = self.nd.SingleReadN(self.axis, self.handle)
        counts_data=[]
        p=position-ran/2
        while p<=position+ran/2:
            positionList.append(p)
            p+=step
        for each_position in positionList:
            self.go(each_position)
            data=self.count()
            
            counts_data.append(data)
        
        self.go(positionList[counts_data.index(max(counts_data))])
        
    def cleanup(self):
        self.nd.ReleaseAllHandles()
        self.awgcomm.cleanup()


