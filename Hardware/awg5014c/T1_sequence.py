# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 17:21:34 2016

@author: HatLab_Xi Cao
"""

# T1 test pulse for new fast code of AWG 
# Oh great Pinlei!
import numpy as np
from pulse import Gaussian, Square, Marker
from sequence import Sequence
from timeit import default_timer
import AWGFile
import qt

AWGInst = qt.instruments['AWG']
#AWGInst.set_AWGmode('SEQ')
#heardfile = 'a'
### Decide if one wants to change the setting, like DC offset, channel voltage.

###





### Define the file name and instrument
name = 'T1FastCodeTest.Awg'
filename = 'C:\\Users\\Public\\' + name
awgname = '\\\HATLAB_XICAO-PC\\Users\\Public\\' + name

###

time1 = default_timer()



### Parameters of Gaussian wave
sigma = 8
gaussian_width = 6*sigma
amp = 3998#2832#1906#1761#1848#2000.0
###

### Parameters of Square wave
square_width = 1000#300
square_height = 6250
###

### Parameters of Markers
marker1_delay = 10
marker1_width = gaussian_width + 2*marker1_delay
marker1_on = 5
marker1_off = marker1_width - 5

marker2_delay = 10
marker2_width = square_width + 2*marker2_delay
marker2_on = 5
marker2_off = marker2_width - 5

alazar_marker_width = 100
alazar_marker_on = 5
alazar_marker_off = 95
###

### Pulse init 

# Parameters
ssb_freq = -0.1#0.0#0.1
iqscale = 1/0.847#1
phase = 0
skewphase = (-4.812)*0.1*2*np.pi
#


###############################################################################

# This following block is to create all the pulses that we are going to use 
# in the measurement. 
# Note that two pulse with same pulse type but different pulse parameters should 
# be considered as differet pulses. (e.g Two Gaussian with different amp is two pulses)

pulsenum = 5
pulse = np.empty(pulsenum, dtype = object)
i = 0
while i < pulsenum:
    pulse[i] = Gaussian(i, gaussian_width, ssb_freq, iqscale, phase, sigma, amp, skew_phase = skewphase)
    pulse[i].data_generator()
    i = i + 1
    pulse[i] = Square(i, square_width, 0, 1, 0, square_height)
    pulse[i].data_generator()    
    i = i + 1
    pulse[i] = Marker(i, marker1_width, 1, marker1_on, marker1_off)
    pulse[i].data_generator() 
    i = i + 1
    pulse[i] = Marker(i, marker2_width, 5, marker2_on, marker2_off)
    pulse[i].data_generator() 
    i = i + 1
    pulse[i] = Marker(i, alazar_marker_width, 6, alazar_marker_on, alazar_marker_off)
    pulse[i].data_generator() 
    i = i + 1

###############################################################################


###############################################################################
### Parameters for the sequence
start = 0
wait_time = 1500
###


### Sequence 
shotsnum = 81 # This is how many shots we will do in this experiment, i.e how many wait trigger
shotsnum = shotsnum + 1 # TODO: there is something wrong with the code, the shots number always have one shift...
totwavenum = 5*shotsnum # This is how many waves are going to be used in the whole sequence
sequence = Sequence(shotsnum, totwavenum, pulse)

# The following while loop is where you create you sequence. 
# Tell the sequence where you want a certain pulse to start at which channel

i = 0
while i < shotsnum:
    sequence.get_block(pulse[2].name, start, channel = 1, wait_trigger = True)
    start = start + marker1_delay
    sequence.get_block(pulse[0].name, start, channel = 1)
    start = start + pulse[0].width + wait_time*(i) + 5

    sequence.get_block(pulse[3].name, start - marker2_delay, channel = 3)
    sequence.get_block(pulse[4].name, start - marker2_delay, channel = 3)
    sequence.get_block(pulse[1].name, start, channel = 3)
    start = start + pulse[1].width + marker2_delay
    
    i = i + 1
#    print i
###

### Call difference method from Sequence to do the calculation to find where to put the waveforms
i = 0 
while i < shotsnum-1:
    sequence.sequence_block[i].make_block()
    i = i + 1
#    print 'Hello'
#    print i
    

AWG = AWGFile.AWGFile(filename)
sequence.sequence_upload(AWG)
###

AWGInst.restore(awgname)
print 'Confucius says it takes the following seconds to finish the code'
print default_timer() - time1

AWGInst.channel_on(1)
AWGInst.channel_on(2)
AWGInst.channel_on(3)
AWGInst.channel_on(4)

change_setting = True
if change_setting:
    # Set the DC offset
    ch1_offset = -0.045#-0.183
    ch2_offset = -0.033#-0.148
    ch3_offset = 0.157
    ch4_offset = 0.029
    
    AWGInst.set_ch1offset(ch1_offset)
    AWGInst.set_ch2offset(ch2_offset)
    AWGInst.set_ch3offset(ch3_offset)
    AWGInst.set_ch4offset(ch4_offset)
    
    # Set the channel voltage
    ch1_amp = 0.438
    ch2_amp = 0.438
    ch3_amp = 1.0
    ch4_amp = 1.0
    
    AWGInst.set_ch1amp(ch1_amp)
    AWGInst.set_ch2amp(ch2_amp)
    AWGInst.set_ch3amp(ch3_amp)
    AWGInst.set_ch4amp(ch4_amp)

AWGInst.run()


