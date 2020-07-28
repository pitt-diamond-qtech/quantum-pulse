# Created by Gurudev Dutt <gdutt@pitt.edu> on 12/24/19
# This code is adapted from Kai Zhang's code and extended to enable arbitrary pulseshapes
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
import numpy as np
import logging
import matplotlib.pyplot as plt
# from collections import deque
from pathlib import Path

from .Pulse import Gaussian, Square, Marker, Sech, Lorentzian, LoadWave
from source.common.utils import get_project_root
import copy

maindir = get_project_root()
seqfiledir = Path('.') / 'sequencefiles/'
logfiledir = maindir / 'logs/'
# print('the sequence file directory is {0} and log file directory is {1}'.format(seqfiledir.resolve(),logfiledir.resolve()))

_GHZ = 1.0  # we assume the time units is in ns for the AWG
_MW_S1 = 'S1'  # disconnected for now
_MW_S2 = 'S2'  # channel 1, marker 1
_GREEN_AOM = 'Green'  # ch1, marker 2
_ADWIN_TRIG = 'Measure'  # ch2, marker 2
_WAVE = 'Wave'  # channel 1 and 2, analog I/Q data
_BLANK = 'Blank' # new keyword which turns off all channels, to be implemented
_FULL = 'Full' # new keyword which turns on all channels high, to be implemented
# dictionary of connections from marker channels to devices,
_CONN_DICT = {_MW_S1: None, _MW_S2: 1, _GREEN_AOM: 2, _ADWIN_TRIG: 4}

_DAC_UPPER = 1024.0  # DAC has only 1024 levels
_DAC_MID = 512
_IQTYPE = np.dtype('<f4')  # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1')  # AWG520 stores marker values as 1 byte

modlogger = logging.getLogger('seqlogger')
modlogger.setLevel(logging.DEBUG)
# create a file handler that logs even debug messages
fh = logging.FileHandler((logfiledir / 'seqlog.log').resolve())
fh.setLevel(logging.DEBUG)
# create a console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
modlogger.addHandler(fh)
modlogger.addHandler(ch)


def to_int(iterable):
    return [int(x) for x in iterable]


class Event(object):
    """Recently added this class because I have a feeling all the sequence objects should be redefined in terms of this."""

    def __init__(self, sequence):
        self.event_dict = create_event_dictionary(sequence)

    def add_pulse(self, pulse):
        pass


''''This entire section of methods essentially helps the Sequence class that is defined below and I think 
it would be best if they were all made into part of the Event class. '''


def find_start_stop(pulse, t):
    """Helper method processes a pulse in the form [name,start,stop,type,optional params] and returns the start stop
    times and if needed adds t to the pulse events"""
    if '+' in pulse[1]:
        t1, t2 = pulse[1].split('+')
        if t2 == 't':
            start = int(t1) + t
        else:
            start = int(t1) + int(t2[:-1]) * t
    else:
        start = int(pulse[1])
    if '+' in pulse[2]:
        t1, t2 = pulse[2].split('+')
        if t2 == 't':
            stop = int(t1) + t
        else:
            stop = int(t1) + int(t2[:-1]) * t
    else:
        stop = int(pulse[2])
    return (start, stop)


def increment_sequence_by_dt(seq, dt=0):
    """This method increments the start and stop times by dt and returns the updated sequence for processing"""
    temp_seq = copy.deepcopy(seq)
    for (idx, pulse) in enumerate(seq):
        if '+' in pulse[1]:
            t1, t2 = pulse[1].split('+')
            if t2 == 't':
                start = int(t1) + dt
            else:
                start = int(t1) + int(t2[:-1]) * dt
        else:
            start = int(pulse[1])
        if '+' in pulse[2]:
            t1, t2 = pulse[2].split('+')
            if t2 == 't':
                stop = int(t1) + dt
            else:
                stop = int(t1) + int(t2[:-1]) * dt
        else:
            stop = int(pulse[2])
        temp_seq[idx][1] = str(start)
        temp_seq[idx][2] = str(stop)
    return temp_seq


def sort_event_dictionary(evt_dict):
    """This function sorts each channel using the start time of the pulses in each channel"""
    tmp_dict = copy.deepcopy(evt_dict)
    # sort the new dictionary
    for k, v in tmp_dict.items():
        # print('the key {} has value {}'.format(k, v))
        new_val = sorted(v, key=lambda x: x[0])
        tmp_dict[k] = new_val
        # print('sorted! the key {} now has value {}'.format(k, new_val))
    return dict(tmp_dict)


def create_event_dictionary(seq):
    """this function creates a dictionary with each key representing a channelname, and the values being a tuple of the
    (start,stop,duration,pulsetype) times. This function handles multiple pulses on the same channel, and returns tuples that
    are sorted by the start time of each event on that channel."""
    from collections import defaultdict
    event_dict = defaultdict(list)
    c_list = [seq[i][0] for i in range(len(seq))]
    start_list = to_int([seq[i][1] for i in range(len(seq))])
    stop_list = to_int([seq[i][2] for i in range(len(seq))])
    dur_list = to_int([stop_list[i] - start_list[i] for i in range(len(start_list))])
    pulse_list=[]
    # The code below checks if pulse has more parameters than the start, stop time, if it does
    # not then a blank string is inserted otherwise the name of the function e.g. Gauss,sech etc
    # is inserted
    # TODO:possible future issue if we add more parameters to pulse, this is really crying out for a class def
    for i in range(len(seq)):
        if len(seq[i]) > 3:
            pulse_list.append(seq[i][3])
        else:
            pulse_list.append('')
    # create the event dictionary
    m_list = [c_list,start_list,stop_list,dur_list,pulse_list]
    for z in zip(*m_list):
        event_dict[z[0]].append(z[1:])
    # # sort each channel in the event dictionary by the start times
    # for key, val in event_dict.items():
    #     new_val = sorted(val, key=lambda x:x[0])
    #     event_dict[key] = new_val

    # also using another way which doesn't rely on defaultdict
    # dict_1 = {}
    # m_list = [c_list, start_list, stop_list, dur_list]
    # for z in zip(*m_list):
    #     if z[0] not in dict_1:
    #         dict_1[z[0]] = [z[1:]]
    #     else:
    #         dict_1[z[0]].append(z[1:])

    return sort_event_dictionary(event_dict)


def insert_multiple_pulses_into_event_dictionary(evt_dict, pulse, n=0):
    """This function will insert a pulse multiple times (n) into the event dictionary for the channel denoted by
    pulse, and then push all the start times that come after this pulse by the necessary amount"""
    temp_dict = copy.deepcopy(evt_dict)
    push_time = 0
    p_channel = str(pulse[0])
    p_start = int(pulse[1])
    p_stop = int(pulse[2])
    p_duration = p_stop - p_start
    for key, val in evt_dict.items():
        start_times = [val[j][0] for j in range(len(val))]  # create a list of all the start times in that
        # channel
        stop_times = [val[j][1] for j in range(len(val))]  # create a list of all the stop times in that
        # channel
        dur_times = [val[j][2] for j in range(len(val))]  # create a list of all the duration times in that
        # channel
        pulse_types = [val[j][3] for j in range(len(val))]  # create a list of all the pulse types in that
        # channel
        # print('start times for pulse {:} are {}'.format(key,start_times))
        # print('stop times for pulse {:} are {}'.format(key,stop_times))
        if p_channel == key:  # if the channelname of pulse matches a particular channel in the dict
            for i in range(n):  # insert the pulse into the dictionary while moving the start and stop times
                new_start = [start_times[j] + (i + 1) * p_duration for j in range(len(start_times))]
                # print('Match found! new starting times for pulse {} are {}'.format(key,new_start))
                # new_start = start_times + i * p_duration
                new_stop = [stop_times[j] + (i + 1) * p_duration for j in range(len(stop_times))]
                # print('Match found! new stopping times for pulse {} are {}'.format(key,new_stop))
                # new_stop = stop_times + i * p_duration
                push_time += p_duration
                # print("Push time is {}".format(push_time))
                m_list = [new_start,new_stop,dur_times,pulse_types]
                for z in zip(*m_list):
                    temp_dict[key].append(z[0:])
            # print('max new start time is {} and new stop time is {}'.format(max(new_start),max(new_stop)))
            # print('lenght of new start is {}'.format(len(new_start)))
        else:
            pass

    # now we have to check the other pulses in sequence and if any of them are now conflicting with the newly
    # added pulses in the dictionary we have to move them by the push time
    temp_dict = push_later_pulses(temp_dict, p_channel)
    # print("the event dictionary with inserted pulses is {}".format(temp_dict))

    return dict(temp_dict)


def push_later_pulses(evt_dict, insert_channel):
    """this function pushes the pulses that do not belong to the insert channel to later times if their original start
    times are now less than the latest start time of the insert channel"""
    temp_dict = copy.deepcopy(evt_dict)
    earliest_start_time = 0
    earliest_stop_time = 0
    latest_start_time = 0
    latest_stop_time = 0
    push_time = 0
    earliest_start_time = evt_dict[insert_channel][0][0]
    earliest_stop_time = evt_dict[insert_channel][0][1]
    latest_start_time = evt_dict[insert_channel][-1][0]
    latest_stop_time = evt_dict[insert_channel][-1][1]
    push_time = latest_start_time - earliest_start_time
    # print("the oldest and latest start times for the inserted channel are {} and {}".format(earliest_start_time,latest_start_time))
    # print('push time is {}'.format(push_time))
    for channel, val in evt_dict.items():
        if (channel != insert_channel):
            # print('pulse {:s} is not matched with {}'.format(channel,insert_channel))
            start_times = [val[j][0] for j in range(len(val))]  # create a list of all the start times in that
            # channel
            stop_times = [val[j][1] for j in range(len(val))]  # create a list of all the stop times in that
            # channel
            dur_times = [val[j][2] for j in range(len(val))]  # create a list of all the duration times in that
            pulse_types = [val[j][3] for j in range(len(val))]  # create a list of all the pulse types in that
            # channel
            for (idx, start) in enumerate(start_times):
                if (start > earliest_start_time) and (start < latest_stop_time):
                    # start_times[idx] = start + push_time
                    # stop_times[idx] = stop_times[idx] + push_time
                    #print('Had to move this block! new starting times for pulse {} are {}'.format(channel,start+push_time))
                    # m_list = [start_times, stop_times, dur_times,pulse_types]
                    # for z in zip(*m_list):
                    #     # print('the new start,stop, duration times are {0},{1},{2}'.format(z[0],z[1],z[2]))
                    #     temp_dict[channel] = z
                    temp_dict[channel][idx] = (start + push_time,stop_times[idx]+push_time,dur_times[idx],pulse_types[idx])
                else:
                    pass

    return sort_event_dictionary(temp_dict)


def find_max_event(evt_dict):
    """Helper method finds the data length of the event dictionary of pulses, returns the data length"""
    events = list(evt_dict.values())
    stop_times = [events[j][-1][1] for j in range(len(events))]
    return int(max(stop_times))


def find_data_length(seq, dt=0, timeres=1):
    """Helper method finds the data length of the sequence of pulses, returns the data length and the dictionary
    of durations, start and stop times."""
    maxend = 0
    for pulse in seq:
        start, stop = find_start_stop(pulse, dt)
        start = int(start // timeres)
        stop = int(stop // timeres)
        duration = stop - start
        if stop > maxend:
            maxend = stop
    maxend = maxend // timeres
    while maxend % 4 != 0:
        maxend += 1
    # print (duration_list,start_list,stop_list)
    return maxend


def fix_minimum_duration(event_dict, channel, deviation=20):
    # this method goes through the dictionary and ensures that any channel that is specified has minimum duration of
    # 6 standard deviations
    tmp_dict = copy.deepcopy(event_dict)
    for k, v in event_dict.items():
        # we will go out at least 6 standard deviations
        start_list = [v[j][0] for j in range(len(v))]
        stop_list = [v[j][1] for j in range(len(v))]
        dur_list = [v[j][2] for j in range(len(v))]  # the duration is assumed to be in the 3rd element of this tuple
        pulse_l = [v[j][3] for j in range(len(v))]
        if (k == channel):
            for j in range(len(start_list)):
                if dur_list[j] < 6 * deviation:
                    dur_list[j] = 6 * deviation
                    stop_list[j] = start_list[j] + dur_list[j]  # if duration was longer than specified initially update the stop time
                    tmp_dict[k][j] = (start_list[j], stop_list[j], dur_list[j],pulse_l[j])
    return dict(tmp_dict)


""""End helper methods section"""


class Sequence(object):
    def __init__(self, sequence, delay=[0, 0], pulseparams=None, connectiondict=None, timeres=1):
        """Class that implements a sequence, with args:
                1. sequence: list specifying sequence in the form [type,start,stop, optionalparams],eg. here is Rabi sequence
                [['S1', ' 1000', ' 1000+t'],
                ['Green', '2000+t', '5000+t'],
                ['Measure', '2000+t', '2100+t']]

                Another sequence for a gaussian pulse would be
                [['Wave','1000','2000','Gauss'],
                ['Green', '2000+t', '5000+t'],
                ['Measure', '2000+t', '2100+t']]
                2. delay: list with [AOM delay, MW delay] , possibly other delays to be added.
                3. pulseparams: a dictionary containing the amplitude, pulsewidth,SB frequency,IQ scale factor,
                phase, skewphase
                4. connectiondict: a dictionary of the connections between AWG channels and switches/IQ modulators
                5. timeres: clock rate in ns

                After creating the instance, call the method create_sequence with an optional increment of time ,
                and then the arrays created will be: wavedata (analag I and Q data), c1markerdata, c2markerdata
                """
        # start the class logger
        self.logger = logging.getLogger('seqlogger.seq_class')
        self.seq = sequence
        self.timeres = timeres

        if pulseparams == None:
            self.pulseparams = {'amplitude': 100, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
                                'phase': 0.0, 'skew phase':
                                    0.0, 'num pulses': 1}
        else:
            self.pulseparams = pulseparams
        if connectiondict == None:
            self.connectiondict = _CONN_DICT
        else:
            self.connectiondict = connectiondict
        self.delay = delay
        # init the arrays
        self.wavedata = None
        self.c1markerdata = None
        self.c2markerdata = None
        # set the maximum length to be zero for now
        self.maxend = 0

    def convert_pulse_params_from_dict(self):
        ssb_freq = float(self.pulseparams['SB freq']) * _GHZ  # SB freq is in units of GHZ
        iqscale = float(self.pulseparams['IQ scale factor'])
        phase = float(self.pulseparams['phase'])
        deviation = int(self.pulseparams['pulsewidth']) // self.timeres
        amp = int(self.pulseparams['amplitude'])  # needs to be a number between 0 and 100
        skew_phase = float(self.pulseparams['skew phase'])
        npulses = self.pulseparams['num pulses']
        return (ssb_freq, iqscale, phase, deviation, amp, skew_phase, npulses)

    def create_sequence(self, dt=0):
        """Creates the data for the sequence, with args:
        1. dt: increment in time
        """
        # get the AOM delay
        aomdelay = int((self.delay[0] + self.timeres / 2) / self.timeres)  # proper way of rounding delay[0]/timeres
        self.logger.info("AOM delay is found to be %d", aomdelay)
        # get the MW delay
        mwdelay = int((self.delay[1] + self.timeres / 2) // self.timeres)
        self.logger.info("MW delay is found to be %d", mwdelay)
        # get all the pulse params
        ssb_freq, iqscale, phase, deviation, amp, skew_phase, npulses = self.convert_pulse_params_from_dict()
        # self.logger.info("The SB freq is %f GHz", ssb_freq)
        # first increment the sequence by dt if needed
        self.seq = increment_sequence_by_dt(seq=self.seq, dt=dt)
        #print('the new sequence after increment is',self.seq)
        # then create the event dictionary using the sequence
        self.event_dict = create_event_dictionary(self.seq)
        #print("The original event dictionary is {}".format(self.event_dict))
        # fix any pulses that are not long enough for the given deviation
        self.event_dict = fix_minimum_duration(event_dict=self.event_dict, channel=_WAVE, deviation=deviation)
        #print("The new event dictionary with after fixing min duration is {}".format(self.event_dict))
        # get the maximum duration of the pulse that has to be inserted, if the Wave keyword is present
        if _WAVE in self.event_dict.keys():
            max_duration = max([self.event_dict[_WAVE][j][2] for j in range(len(self.event_dict[_WAVE]))])
            #print('max duration of the pulse to be inserted is {}'.format(max_duration))
            self.event_dict = insert_multiple_pulses_into_event_dictionary(evt_dict=self.event_dict,
                                                                           pulse=[_WAVE, 0, max_duration], n=(npulses-1))
        #print("The event dictionary after inserting {} pulses is {}".format(npulses,self.event_dict))
        # now we need to find the data length i.e. the largest stop time in the list of stop times
        self.maxend = find_max_event(self.event_dict)
        #print("the max. event value is {}".format(self.maxend))
        # now we can init the arrays
        c1m1 = np.zeros(self.maxend, dtype=_MARKTYPE)
        c1m2 = c1m1.copy()
        c2m1 = c1m1.copy()
        c2m2 = c1m1.copy()
        waveI = np.zeros(self.maxend, dtype=_IQTYPE)
        waveQ = waveI.copy()
        num = 0
        for pulse in self.seq:
            # channel = channeldic[pulse[0]]
            num = num + 1
            cname = pulse[0]
            # get all the start,stop,duration point lists
            start_list = [self.event_dict[cname][j][0] for j in range(len(self.event_dict[cname]))]
            stop_list = [self.event_dict[cname][j][1] for j in range(len(self.event_dict[cname]))]
            dur_list = [self.event_dict[cname][j][2] for j in range(len(self.event_dict[cname]))]
            for j in range(len(start_list)):
                if cname == _WAVE:
                    num = num + j
                    if pulse[3] == 'Gauss':
                        channel = Gaussian(num, dur_list[j], ssb_freq, iqscale, phase, deviation, amp, skew_phase)
                    elif pulse[3] == 'Sech':
                        channel = Sech(num, dur_list[j], ssb_freq, iqscale, phase, deviation, amp, skew_phase)
                    elif pulse[3] == 'Square':
                        channel = Square(num, dur_list[j], ssb_freq, iqscale, phase, amp, skew_phase)
                    elif pulse[3] == 'Lorentz':
                        channel = Lorentzian(num, dur_list[j], ssb_freq, iqscale, phase, deviation, amp, skew_phase)
                    elif pulse[3] == 'Load Wfm':
                        # TODO: Must also figure out how to send that filename to this point
                        filename = pulse[4]  # i will pass the filename in the last element of the list
                        channel = LoadWave(filename, num, dur_list[j], ssb_freq, iqscale, phase, deviation, amp,
                                           skew_phase)
                    else:
                        self.logger.error('Pulse type has to be either Gauss, Sech, Square, Lorentz, or Load Wfm')
                        raise ValueError('Pulse type has to be either Gauss, Sech, Square, Lorentz, or Load Wfm')
                    channel.data_generator()
                    # update teh waveI and waveQ arrays
                    waveI[start_list[j]:stop_list[j]] = channel.I_data
                    waveQ[start_list[j]:stop_list[j]] = channel.Q_data
                    self.logger.info("The pulse type is %s, number is %d, center is %d", pulse[3], channel.num,
                                     start_list[j] + channel.mean)
                elif (cname == _MW_S2 or cname == _MW_S1):
                    num = num + j
                    if cname == _MW_S2:
                        # print("The marker start is %d stop is %d and type is %s", start, stop, channelname)
                        self.logger.info("The marker start is %d stop is %d and type is %s", start_list[j],
                                         stop_list[j], cname)
                        # this is the only microwave switch connected right now
                        channel = Marker(num, width=self.maxend, markernum=self.connectiondict[_MW_S2],
                                         marker_on=start_list[j],
                                         marker_off=stop_list[j])
                        channel.data_generator()
                        # handle the mw delay
                        c1m1 = c1m1 + np.roll(channel.data, -mwdelay)
                    elif cname == _MW_S1:
                        # markernum = 2  # uncomment this line if you want MW S1
                        self.logger.error('Value error: only MW switch connected is S2 using Ch1, M1')
                        raise ValueError
                elif (cname == _GREEN_AOM):
                    num = num + j
                    self.logger.info("The marker start is %d stop is %d and type is %s", start_list[j], stop_list[j],
                                     cname)
                    channel = Marker(num, width=self.maxend, markernum=self.connectiondict[_GREEN_AOM], marker_on=
                    start_list[j], marker_off=stop_list[j])
                    channel.data_generator()
                    # handle AOM delay
                    c1m2 = c1m2 + np.roll(channel.data, -aomdelay)
                elif (cname == _ADWIN_TRIG):
                    num = num + j
                    self.logger.info("The marker start is %d stop is %d and type is %s", start_list[j], stop_list[j],
                                     cname)
                    channel = Marker(num, width=self.maxend, markernum=self.connectiondict[_ADWIN_TRIG], marker_on=
                    start_list[j], marker_off=stop_list[j])
                    channel.data_generator()
                    c2m2 = c2m2 + channel.data
        # the marker data is simply the sum of the 2 markers since 1st bit represents m1 and 2nd bit represents m2
        # for each channel, and that's how we coded the Marker pulse class
        self.c1markerdata = c1m1 + c1m2
        self.c2markerdata = c2m1 + c2m2
        # the wavedata will store the data for the I and Q channels in a 2D array
        self.wavedata = np.array((waveI, waveQ))


class SequenceList(object):
    def __init__(self, sequence, delay=[0, 0], scanparams=None, pulseparams=None, connectiondict=None, timeres=1):
        """This class creates a list of sequence objects that each have the waveforms for one step in the scanlist.
        Currently the only real new argument is
        1. scanparams : a dictionary that specifies the type, start, stepsize, number of steps
        so perhaps this entire class could be removed and just the function create_sequence_list could be put inside
        Sequence.
        However the main issue I encountered is that the function would have to create more instances of the
        sequence objects, especially for scans that change the pulsewidth or other aspects of the pulse like
        frequency etc. For now I will stay with this approach and later we can rewrite if needed.
        """
        if scanparams == None:
            self.scanparams = {'type': 'amplitude', 'start': 0, 'stepsize': 10, 'steps': 10}
        else:
            self.scanparams = scanparams
        if pulseparams == None:
            self.pulseparams = {'amplitude': 0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
                                'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
        else:
            self.pulseparams = pulseparams
        if connectiondict == None:
            self.connectiondict = _CONN_DICT
        else:
            self.connectiondict = connectiondict
        #2/7/20 this if else statement was commented out on 2/6/20 because from now on, we will use the scan params
        # dictionary for all the scans and just choose the type of scan. Strict type checking will be enforced by the
        # main app
        # if self.scanparams['type'] == 'number':
        #     # self.scanlist = np.arange(1,self.pulseparams['num pulses']+1,1,dtype=np.dtype('i1'))
        #     self.scanlist = list(range(1, self.pulseparams['num pulses'] + 1))
        # else:
        #     self.scanlist = np.arange(self.scanparams['start'], self.scanparams['start'] + self.scanparams[
        #         'stepsize'] * self.scanparams['steps'], self.scanparams['stepsize'])
        self.scanlist = np.arange(self.scanparams['start'], self.scanparams['start'] + self.scanparams[
            'stepsize'] * self.scanparams['steps'], self.scanparams['stepsize'])
        self.delay = delay
        self.pulseparams = pulseparams
        self.connectiondict = connectiondict
        self.timeres = timeres
        self.sequence = sequence
        self.sequencelist = []

    def create_sequence_list(self):
        #dt = float(self.scanparams['stepsize'])
        if self.scanparams['type'] == 'no scan':
            s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams, \
                         connectiondict=self.connectiondict, timeres=self.timeres)
            s.create_sequence(dt=0)
            self.sequencelist.append(s)
        else:
            for x in self.scanlist:
                if self.scanparams['type'] == 'time':
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(int(x))
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'amplitude':
                    self.pulseparams['amplitude'] = x
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'SB freq':
                    self.pulseparams['SB freq'] = x
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'pulsewidth':
                    self.pulseparams['pulsewidth'] = x
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'number':
                    self.pulseparams['num pulses'] = int(x)+1
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams, \
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
