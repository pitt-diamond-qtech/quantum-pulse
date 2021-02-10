# Created by Gurudev Dutt <gdutt@pitt.edu> on 12/01/2020
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

from pathlib import Path
from source.Hardware.AWG520.AWG520 import AWG520,AWGFile
from source.Hardware.AWG520.Sequence import Sequence,SequenceList
from source.common.utils import get_project_root
import numpy as np
import matplotlib.pyplot as plt
import time,sys,os
import ADwin #ADwin python module
import pyvisa as visa #Virt. Instr. Soft. Arch. to control the Arduino

# time constants
_ns = 1.0e-9 # ns
_us = 1.0e-6 # micro-sec
_ms = 1.0e-3 # ms
_ARDUINO_PORT = 'COM7'

d_time = 10 * _ms # change as needed, but max is 1048512*100 ns ~ 100 ms
nsteps = 1 # we will send out this many triggers to arduino for one scan
sampclk = 100 # we will use 100 ns time resolution on the AWG, the assumption is that the dwell time is quite long.
navgs = 1 # we will repeat the measurement this many times
avg=0

sourcedir = get_project_root()
#print(sourcedir)
dirPath = sourcedir / 'Hardware/AWG520/tests/sequencefiles/' # remove the tests part of the string later
#print(dirPath)

def write_trigger_sequence(dwell_time,numsteps,tres):
    # the strings needed to make the sequence
    tstartstr = str(int(100/tres))
    tstopstr = str(int(0.5 * dwell_time / (tres * _ns)))
    greenstopstr = str(int(dwell_time / (tres * _ns)))
    seqfilename = dirPath/'odmr_trigger.seq' # filename for sequences
    # create a sequence where measure is on for 1/2 dwell time, and then turns off, but green remains on throughout
    # the adwin will measure till it receives the next positive edge and then latch
    seq = [['Measure', tstartstr, tstopstr], ['Green', tstartstr, greenstopstr]]
    # params = {'type':'number','start': 1, 'stepsize': 1, 'steps': steps-1}
    s = Sequence(seq, timeres=tres)
    s.create_sequence()
    # this part here is not necessary in the actual program, I am just using it to check that the above sequence will do
    # what I want it to do
    # tt = np.linspace(0, s.maxend, len(s.c1markerdata))
    # plt.plot(tt, s.wavedata[0, :], 'r-', tt, s.wavedata[1, :], 'b-', tt, s.c1markerdata, 'g--', tt, s.c2markerdata,
    #          'y-')
    # plt.show()
    # this is the section where I actually write the waveform to a file,  to repeat it for numsteps,
    # and then wait to receive a software trigger from the Pc before doing it again
    awgfile = AWGFile(s,timeres=tres,dirpath=dirPath)

    awgfile.write_waveform(s,'trig',1)
    awgfile.write_waveform(s,'trig',2)
    wfmlen = len(s.c2markerdata)

    # first create an empty waveform in channel 1 and 2 but turn on the green laser
    # so that measurements can start after a trigger is received.
    arm_sequence = Sequence([['Green', '0', str(wfmlen)]], timeres=tres)
    arm_sequence.create_sequence()
    awgfile.write_waveform(arm_sequence,'arm', 1)
    awgfile.write_waveform(arm_sequence,'arm', 2)

    # now we create a sequence file that will be loaded to the AWG
    try:
        with open(seqfilename,'wb') as sfile:
            sfile.write(awgfile.seqheader)
            temp_str = 'LINES ' + str(2) + '\r\n' # there are only 2 lines in this file
            sfile.write(temp_str.encode()) # have to convert to binary format
            temp_str = '"arm_1.wfm","arm_2.wfm",0,1,0,0\r\n' # the arm sequence will be loaded and will keep
            # repeating and wait for the software trigger from the PC
            sfile.write(temp_str.encode())
            # the trig wfm is repeated numsteps
            # 2020-01-04: after lot of experimenting with Arduino code it appears that interrupt of the arduino is
            # unable to accept fast triggers, i.e. it does not work if the triggers have 1 ms spacing, but works if
            # they have 10 ms spacing. So we have decided not to mess with it, and instead simply to use the old
            # arduino code where all timing comes from the arduino itself but require that it takes one trigger from
            # the  AWG to start a scan
            linestr= '"trig_1.wfm","trig_2.wfm",' + str(1) +',1,0,0\r\n'
            sfile.write(linestr.encode())
            sfile.write(b'JUMP_MODE SOFTWARE\r\n') # tells awg to wait for a software trigger
    except (IOError,ValueError) as error:
        # replace these with logger writes, but for now just send any errors to stderr
        sys.stderr.write(sys.exc_info())
        sys.stderr.write(error.message+'\n')

def write_list_sequence(dwell_time,numsteps,tres):
    # the strings needed to make the sequence
    tstartstr = str(int(100/tres))
    tstopstr = str(int(0.5 * dwell_time / (tres * _ns)))
    greenstopstr = str(int(dwell_time / (tres * _ns)))
    seqfilename = dirPath/'odmr_trigger.seq' # filename for sequences
    # create a sequence where measure is on for 1/2 dwell time, and then turns off, but green remains on throughout
    # the adwin will measure till it receives the next positive edge and then latch
    seq = [['Measure', tstartstr, tstopstr], ['Green', tstartstr, greenstopstr]]
    # params = {'type':'number','start': 1, 'stepsize': 1, 'steps': steps-1}
    s = Sequence(seq, timeres=tres)
    s.create_sequence()
    # this part here is not necessary in the actual program, I am just using it to check that the above sequence will do
    # what I want it to do
    # tt = np.linspace(0, s.maxend, len(s.c1markerdata))
    # plt.plot(tt, s.wavedata[0, :], 'r-', tt, s.wavedata[1, :], 'b-', tt, s.c1markerdata, 'g--', tt, s.c2markerdata,
    #          'y-')
    # plt.show()
    # this is the section where I actually write the waveform to a file,  to repeat it for numsteps,
    # and then wait to receive a software trigger from the Pc before doing it again
    awgfile = AWGFile(s,timeres=tres,dirpath=dirPath)

    awgfile.write_waveform(s,'trig',1)
    awgfile.write_waveform(s,'trig',2)
    wfmlen = len(s.c2markerdata)

    # first create an empty waveform in channel 1 and 2 but turn on the green laser
    # so that measurements can start after a trigger is received.
    arm_sequence = Sequence([['Green', '0', str(wfmlen)]], timeres=tres)
    arm_sequence.create_sequence()
    awgfile.write_waveform(arm_sequence,'arm', 1)
    awgfile.write_waveform(arm_sequence,'arm', 2)

    # now we create a sequence file that will be loaded to the AWG
    try:
        with open(seqfilename,'wb') as sfile:
            sfile.write(awgfile.seqheader)
            temp_str = 'LINES ' + str(2) + '\r\n' # there are only 2 lines in this file
            sfile.write(temp_str.encode()) # have to convert to binary format
            temp_str = '"arm_1.wfm","arm_2.wfm",0,1,0,0\r\n' # the arm sequence will be loaded and will keep
            # repeating and wait for the software trigger from the PC
            sfile.write(temp_str.encode())
            # the trig wfm is repeated numsteps
            # 2020-01-04: after lot of experimenting with Arduino code it appears that interrupt of the arduino is
            # unable to accept fast triggers, i.e. it does not work if the triggers have 1 ms spacing, but works if
            # they have 10 ms spacing. So we have decided not to mess with it, and instead simply to use the old
            # arduino code where all timing comes from the arduino itself but require that it takes one trigger from
            # the  AWG to start a scan
            linestr= '"trig_1.wfm","trig_2.wfm",' + str(1) +',1,0,0\r\n'
            sfile.write(linestr.encode())
            sfile.write(b'JUMP_MODE SOFTWARE\r\n') # tells awg to wait for a software trigger
    except (IOError,ValueError) as error:
        # replace these with logger writes, but for now just send any errors to stderr
        sys.stderr.write(sys.exc_info())
        sys.stderr.write(error.message+'\n')


def upload_trigger_seq(seqdir):
    # here comes the section where I actually communicate to the AWG and upload the files
    try:
        awg = AWG520()
        #  transfer all files to AWG
        t = time.process_time()
        for filename in os.listdir(seqdir):
            awg.sendfile(filename, seqdir / filename)
        transfer_time = time.process_time() - t
        time.sleep(0.1)
        sys.stdout.write('time elapsed for all files to be transferred is:{0:.3f}'.format(transfer_time))
        awg.cleanup()
    except RuntimeError as error:
        # replace these with logger writes, but for now just send any errors to stderr
        sys.stderr.write(sys.exc_info())
        sys.stderr.write(error.message+'\n')

def getdata(numavgs):

    #initialize arduino
    rm = visa.ResourceManager()
    arduino = rm.open_resource(_ARDUINO_PORT)
    print((arduino.read()))

    #initialize adwin
    adw = ADwin.ADwin()
    adw.Boot(adw.ADwindir + 'ADwin11.btl')
    count_proc = 'D:\PyCharmProjects\qcomp-qapps\ESRWorking\ESRWorkingProgram\CW_ESR\Hardware\AdWIN\Trigger_Count_test_1.TB1'
    adw.Load_Process(count_proc)
    print("Adwin was successfully initialized")

    # here is the section where I setup the AWG into enhanced run mode and execute the sequence and get data from ADWIn
    # this does not allow for NV tracking during the exec of the scan, we can build that in using a similar function as
    # in source/Hardware/Threads > getData function
    try:
        awg = AWG520()
        awg.setup(enable_iq=True,seqfilename="odmr_trigger.seq")
        time.sleep(0.2)
        #awg.sendcommand('SOUR2:MARK2:VOLT:HIGH 0.0\n')
        awg.run()  # places AWG into enhanced run mode
        time.sleep(0.2)  # delay needed to exec the previous 2 commands
        for ascan in list(range(numavgs)):
            #awg.jump(1)
            #time.sleep(0.005)

            awg.trigger() # first trigger the arm sequence
            time.sleep(0.2) # needed for trigger to execute
            awg.jump(2) # jump to the 2nd line i.e. the actual trigger to arduino
            time.sleep(0.005) # needed for the jump

            # read_adwin(awg=awg, adw=adw, rm=rm, arduino=arduino, nor=5, dwell=5)

            awg.trigger() # now output that line
            time.sleep(0.2) # delay for trigger to exec

            print('this is {0:d} avg out of {1:d} averages'.format(ascan,numavgs))
            # here is where you would put code for reading the adwin data

        awg.cleanup()
        adw.Clear_Process(1)
        arduino.close()
        rm.close()
    except RuntimeError as error:
        # replace these with logger writes, but for now just send any errors to stderr
        sys.stderr.write(sys.exc_info())
        sys.stderr.write(error.message+'\n')

def read_adwin(awg, adw, rm, arduino, nor,dwell):

    adw.Set_Par(1, nor)
    adw.Start_Process(1) #Start Counter 1 of the ADWin

    # String sent to the Arduino (This string is controlled by the arduino sketch External_Trigger)
    arduino.write('2870000000#2880000000#' + str(nor) + '#' + str(dwell) + '#')

    print('Serial COMM Initialized')
    t1 = time.perf_counter() #Elapsed time up to this point
    #time.sleep(3)
    print("Putting out the pulse...")
    awg.trigger()  # first trigger the arm sequence
    time.sleep(0.2)  # needed for trigger to execute
    awg.jump(2)  # jump to the 2nd line i.e. the actual trigger to arduino
    time.sleep(0.005)  # needed for the jump
    awg.trigger()
    time.sleep(0.2)

    t2 = time.perf_counter()
    print("It takes {0: 3f} sec to exec AWG".format(t2 - t1))
    t1 = time.perf_counter()  # Elapsed time up to this point
    while adw.Process_Status(1) == 1: #While the ADwin is already running, delay the process
       time.sleep(0.001)

    dataList = adw.GetData_Long(1, 1, nor) # Get the data collected from the ADwin Counter 1

    print((len(dataList), ' points done.'))

    t2 = time.perf_counter() #Elapsed time up to this point

    print(("It takes: ", t2 - t1, 'for ', nor, " steps"))
    print(list(dataList))

    #avg += 1
    print("Average ", avg, " is done")
    time.sleep(1)

    #close ADwin and Arduino
    # adw.Clear_Process(1)
    # arduino.close()
    # rm.close()

if __name__ == '__main__':
    write_trigger_sequence(dwell_time=d_time,numsteps=nsteps,tres=sampclk)
    upload_trigger_seq(seqdir=dirPath)
    # getdata(10)
