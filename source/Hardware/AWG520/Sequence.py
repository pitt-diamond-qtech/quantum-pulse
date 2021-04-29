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
from pathlib import Path
# from typing import List
from decimal import Decimal, getcontext
from .Pulse import Gaussian, Square, Marker, Sech, Lorentzian, LoadWave,Pulse
from source.common.utils import log_with, create_logger, get_project_root
import copy

maindir = get_project_root()
seqfiledir = maindir / 'Hardware/sequencefiles/'
pulseshapedir = maindir / 'arbpulseshape/'
# logfiledir = maindir / 'logs/'
# print('the sequence file directory is {0} and log file directory is {1}'.format(seqfiledir.resolve(),logfiledir.resolve()))
modlogger = create_logger('seqlogger')

# unit conversion factors
_GHz = 1.0e9  # Gigahertz
_MHz = 1.0e6  # Megahertz
_us = 1.0e-6  # Microseconds
_ns = 1.0e-9  # Nanoseconds
getcontext().prec = 14 # precision with which values are stored

# keywords used by sequence parser
_MW_S1 = 'S1'  # disconnected for now
_MW_S2 = 'S2'  # channel 1, marker 1
_GREEN_AOM = 'Green'  # ch1, marker 2
_ADWIN_TRIG = 'Measure'  # ch2, marker 2
_WAVE = 'Wave'  # channel 1 and 2, analog I/Q data
_BLANK = 'Blank'  # new keyword which turns off all channels, to be implemented
_FULL = 'Full'  # new keyword which turns on all channels high, to be implemented
_MARKER = 'Marker' # new keyword for any marker
_ANALOG1 = 'Analog1' # new keyword for channel 1
_ANALOG2 = 'Analog2' # new keyword for channel 2
# dictionary of connections from marker channels to devices,
_CONN_DICT = {_MW_S1: None, _MW_S2: 1, _GREEN_AOM: 2, _ADWIN_TRIG: 4}
# dictionary of IQ parameters that will be used as default if none is supplied
_PULSE_PARAMS = {'amplitude': 0.0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
              'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
# allowed values of the Waveform types
_PULSE_TYPES = ['Gauss','Sech','Square', 'Lorentz', 'Load Wfm']

_IQTYPE = np.dtype('<f4') # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1') # AWG520 stores marker values as 1 byte

def to_int(iterable):
    return [int(x) for x in iterable]


class SequenceEvent:
    """A single sequence event.
    :param event_type: The type of event, e.g. Marker or Wave etc
    :param start: The start time of the event.
    :param stop: The stop time of the event.
    :param start_increment: The multiplier for incrementing the start time.
    :param stop_increment: The multiplier for incrementing the stop time.
    :param sampletime: the sampling time (clock rate) used for this event
    """
    _counter = 0 # class variable keeps track of how many sequence events are there
    def __init__(self, event_type= '', start=1.0*_us, stop=1.1 *_us, start_increment=0, stop_increment=0,
                 sampletime=1.0 * _ns):
        SequenceEvent._counter +=1 # increment whenever a new event is created
        self.eventidx = SequenceEvent._counter # publicly accessible value of the event id
        self.event_type = event_type
        self.start = start
        self.stop = stop
        self.duration = self.stop - self.start
        self.start_increment = start_increment
        self.stop_increment = stop_increment
        self.sampletime = sampletime

        self.__t1_idx = round(Decimal(self.start / self.sampletime))
        self.__t2_idx = round(Decimal(self.stop / self.sampletime))
        self.__dur_idx = round(Decimal(self.duration / self.sampletime))

    @property
    def event_type(self):
        return self.__event_type

    @event_type.setter
    def event_type(self, var):
        try:
            if type(var) == str:
                self.__event_type = var
            else:
                raise TypeError("Event type must be string")
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def start(self):
        return self.__start

    @start.setter
    def start(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__start = Decimal(var)
            else:
                raise TypeError('start time must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))
    @property
    def stop(self):
        return self.__stop

    @stop.setter
    def stop(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__stop = Decimal(var)
            else:
                raise TypeError('stop time must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def start_increment(self):
        return self.__start_increment

    @start_increment.setter
    def start_increment(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__start_increment = Decimal(var)
            else:
                raise TypeError('start increment must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def stop_increment(self):
        return self.__stop_increment

    @stop_increment.setter
    def stop_increment(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__stop_increment = Decimal(var)
            else:
                raise TypeError('stop increment must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def duration(self):
        return self.__duration

    @duration.setter
    def duration(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__duration = Decimal(var) # duration is kept as a floating point number for easy manipulation
            else:
                raise TypeError('duration must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def sampletime(self):
        return self.__sampletime

    @sampletime.setter
    def sampletime(self, var):
        try:
            if type(var) == float or type(var) == int:
                self.__sampletime = Decimal(var)
            else:
                raise TypeError('sample time must be a floating point number or integer')
        except TypeError as err:
            modlogger.error("Type error {0}".format(err))

    @property
    def t1_idx(self): # this variable stores the start time in integer format suitable for indexing arrays
        self.__t1_idx = round(Decimal(self.start / self.sampletime))
        return self.__t1_idx

    @property
    def t2_idx(self):# this variable stores the stop time in integer format suitable for indexing arrays
        self.__t2_idx = round(Decimal(self.stop / self.sampletime))
        return self.__t2_idx

    @property
    def dur_idx(self):  # this variable stores the start time in integer format suitable for indexing arrays
        self.__dur_idx = round(Decimal(self.duration / self.sampletime))
        return self.__dur_idx

    def increment_time(self, dt=0):
        """Increments the start and stop times by dt.
        :param dt: The time increment.
        """
        #dt = round(Decimal(dt / self.sampletime))
        dt = Decimal(dt)
        self.start += dt * self.start_increment
        self.stop += dt * self.stop_increment

class WaveEvent(SequenceEvent):
    """ Provides functionality for events that are analog in nature. Inherits from :class:`sequence event <SequenceEvent>`
    :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param pulse_type: type of pulse desired, eg Gauss, Sech etc
    """
    # these 2 class variables keep track of the class type and the number of instances
    EVENT_KEYWORD = "Wave"
    _wavecounter = 0
    def __init__(self, start=1e-6, stop=1.1e-7, pulse_params=None, pulse_type='Gauss'):
        super().__init__()
        WaveEvent._wavecounter += 1 # increment the wave counter
        self.waveidx = WaveEvent._wavecounter # publicly accessible id for the wave event
        self.event_type = self.EVENT_KEYWORD
        if pulse_params==None:
            self.pulse_params = _PULSE_PARAMS
        self.start = start
        self.stop = stop
        self.duration = self.stop - self.start
        self.pulse_type = pulse_type
        self.extract_pulse_params_from_dict() # unpack the dictionary of pulse params
        zerosdata = np.zeros(round(Decimal(self.duration)), dtype=_IQTYPE) # create an array of zeros of the right size
        pulse = Pulse(self.waveidx, self.duration, self.ssb_freq, self.iqscale,
                      self.phase, self.skewphase)  # create a blank Pulse object
        pulse.iq_generator(zerosdata)
        self.data = np.array((pulse.I_data, pulse.Q_data)) # initialize the data to be zero

    @property
    def pulse_params(self):
        return self.__iq_params
    @pulse_params.setter
    def pulse_params(self, iqdic):
        try:
            if type(iqdic) == dict:
                self.__iq_params = iqdic
            else:
                raise TypeError('IQ params must be a dictionary')
        except TypeError as err:
            modlogger.error('Type error: {0}'.format(err))

    @property
    def pulse_type(self):
        return self.__pulse_type
    @pulse_type.setter
    def pulse_type(self, var:str):
        try:
            if type(var) == str:
                if var in _PULSE_TYPES:
                    self.__pulse_type = var
                else:
                    raise TypeError(f'Pulse type must be in list of pulse types allowed:{_PULSE_TYPES}')
            else:
                raise TypeError('pulse type must be of type string')
        except TypeError as err:
            modlogger.error('Type error: {0}'.format(err))

    def extract_pulse_params_from_dict(self):
        """This helper method simply extracts the relevant params from the iq dictionary"""
        self.__ssb_freq = float(self.pulse_params['SB freq']) * _MHz  # SB freq is in units of Mhz
        self.__iqscale = float(self.pulse_params['IQ scale factor'])
        self.__phase = float(self.pulse_params['phase'])
        # TODO: should i divide by sampletime ?
        self.__pulsewidth = int(self.pulse_params['pulsewidth'])
        self.__amp = int(self.pulse_params['amplitude'])  # needs to be a number between 0 and 100
        self.__skew_phase = float(self.pulse_params['skew phase'])
        self.__npulses = self.pulse_params['num pulses'] # not needed for a single WaveEvent

    @property
    def data(self):
        return self.__data
    @data.setter
    def data(self,datarr):
        self.__data = datarr

    @property
    def pulsewidth(self):
        return self.__pulsewidth
    @property
    def ssb_freq(self):
        return self.__ssb_freq
    @property
    def amplitude(self):
        return self.__amp
    @property
    def iqscale(self):
        return self.__iqscale
    @property
    def phase(self):
        return self.__phase
    @property
    def skewphase(self):
        return self.__skew_phase


#TODO: looks to me like we can probably get rid of the Pulse module and move all the data generation here. will make
# it more self-contained.
class GaussPulse(WaveEvent):
    """Generates a Wave event with a Gaussian shape"""
    PULSE_KEYWORD = "Gauss"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params=None):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        # if duration < 6 * pulsewidth, set it equal to at least that much
        if self.duration < 6*self.pulsewidth:
            self.duration = 6*self.pulsewidth
            self.stop = self.start + self.duration
        pulse = Gaussian(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         self.pulsewidth, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class SechPulse(WaveEvent):
    """Generates a Wave event with a Sech shape"""
    PULSE_KEYWORD = "Sech"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params=None):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        if self.duration < 6*self.pulsewidth:
            self.duration = 6*self.pulsewidth
            self.stop = self.start + self.duration
        pulse = Sech(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         self.pulsewidth, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class SquarePulse(WaveEvent):
    """Generates a Wave event with a Square shape"""
    PULSE_KEYWORD = "Square"

    def __init__(self, start=1e-6, stop=1.1e-7,pulse_params=None):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        if self.duration < 6*self.pulsewidth:
            self.duration = 6*self.pulsewidth
            self.stop = self.start + self.duration
        pulse = Square(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, self.amplitude,
                       self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class LorentzPulse(WaveEvent):
    """Generates a Wave event with a Lorentzian shape"""
    PULSE_KEYWORD = "Lorentz"

    def __init__(self, start=1e-6, stop=1.1e-7,pulse_params=None):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        if self.duration < 6*self.pulsewidth:
            self.duration = 6*self.pulsewidth
            self.stop = self.start + Decimal(self.duration)
        pulse = Lorentzian(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, self.pulsewidth,
                           self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class ArbitraryPulse(WaveEvent):
    """Generates a Wave event with any shape given by numerically generated data read from text file"""
    PULSE_KEYWORD = "Load Wfm"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params=None,filename=''):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        self.filename = filename
        if self.duration < 6*self.pulsewidth:
            self.duration = 6*self.pulsewidth
            self.stop = self.start + Decimal(self.duration)
        pulse = LoadWave(self.filename, self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         self.pulsewidth, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class MarkerEvent(SequenceEvent):
    """ Provides functionality for events that are digital in nature using marker output of AWG
    :param markernum: integer that specifies the marker output number (e.g. 1-4 for AWG520)
    :param connection_dict: dictionary that specifies which markers are connected to which hardware
        """
    # these 2 class variables define the event type and track the number of marker events
    EVENT_KEYWORD = "Marker"
    _markercounter = 0
    def __init__(self, start=1e-6, stop=1.1e-7, connection_dict=None):
        super().__init__(start=start, stop=stop,event_type=self.EVENT_KEYWORD)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        MarkerEvent._markercounter += 1
        self.markeridx = MarkerEvent._markercounter # public id of the marker event
        self.connection_dict = connection_dict
        self.pulse_type = self.EVENT_KEYWORD
        self.duration = self.stop - self.start
        pulse = Marker(num=self.markeridx,width=self.dur_idx,markernum=0,marker_on=self.t1_idx,marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, datarr):
        self.__data = datarr

class Green(MarkerEvent):
    """Turns on the green AOM"""
    PULSE_KEYWORD = "Green"
    def __init__(self, start=1e-6, stop=1.1e-7, connection_dict=None):
        super().__init__(start=start, stop=stop,connection_dict=connection_dict)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_GREEN_AOM]
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data


class Measure(MarkerEvent):
    """Turns on the Adwin trigger for measurement"""
    PULSE_KEYWORD = "Measure"
    def __init__(self, start=1e-6, stop=1.1e-7, connection_dict=None):
        super().__init__(start=start, stop=stop,connection_dict=connection_dict)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_ADWIN_TRIG]
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data

class S1(MarkerEvent):
    """Turns on the MW switch S1"""
    PULSE_KEYWORD = "S1"
    def __init__(self, start=1e-6, stop=1.1e-7, connection_dict=None):
        super().__init__(start=start, stop=stop,connection_dict=connection_dict)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_MW_S1]
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data

class S2(MarkerEvent):
    """Turns on the MW switch S2"""
    PULSE_KEYWORD = "S2"
    def __init__(self, start=1e-6, stop=1.1e-7, connection_dict=None):
        super().__init__(start=start, stop=stop,connection_dict=connection_dict)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_MW_S2]
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data

class Channel:
    """Provides functionality for a sequence of :class:`sequence events <SequenceEvent>`.
    :param event_train: A collection of :class:`sequence events <SequenceEvent>`.
    :param delay: Delay in the format [AOM delay, MW delay].
    :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param connection_dict: A dictionary of the connections between AWG channels and switches/IQ modulators.
    """

    def __init__(self, event_train=None, delay=None, pulse_params=None, connection_dict=None):
        if delay is None:
            delay = [0, 0]
        if pulse_params is None:
            pulse_params = _PULSE_PARAMS
        if connection_dict is None:
            connection_dict = _CONN_DICT
        if event_train is None:
            event_train = [] # add empty event
        self.logger = logging.getLogger('seqlogger.channel')
        self.event_train = event_train
        self.delay = delay
        self.pulse_params = pulse_params
        self.connection_dict = connection_dict
        # set various object variables
        self.num_of_events = len(self.event_train) # number of events in the channel
        self.event_channel_index = 0 # index of event in channel
        self.latest_channel_event = 0 # channel event with latest time
        self.first_channel_event = 0 # channel event with earliest time
        self.channel_type = self.event_train[0].event_type # type of channel events
        #
        if self.num_of_events == 1 or self.num_of_events == 0:
            self.separation = 0.0
        # array storing all the start and stop times in this channel
        self.event_start_times = []
        self.event_stop_times = []
        for idx, evt in self.event_train:
            self.event_start_times.append(evt.start)
            self.event_stop_times.append(evt.stop)

        self.latest_channel_event = np.amax(np.array(self.event_stop_times))
        self.first_channel_event = np.amin(np.array(self.event_start_times))

        # init the arrays
        self.wavedata = None
        self.markerdata = None

        # set the maximum length to be zero for now
        self.maxend = 0

    def add_event(self,time_on=1e-6,time_off=1.1e-6,evt_type='Wave',pulse_type="Gauss"):
        """This method adds one event of a given type to the channel
        :param time_on: starting time of the event
        :param time_off: ending time of the event
        :param evt_type: type of event
        :param pulse_type: type of pulse
        """
        self.num_of_events += 1
        self.event_channel_index += 1
        event = SequenceEvent() # no need for this statement, but pycharm complains event may be assigned before ref?
        if evt_type == "Wave":
            if pulse_type == _PULSE_TYPES[0]:
                event = GaussPulse(start=time_on,stop=time_off,pulse_params=self.pulse_params)
            elif pulse_type == _PULSE_TYPES[1]:
                event = SechPulse(start=time_on,stop=time_off,pulse_params=self.pulse_params)
            elif pulse_type == _PULSE_TYPES[2]:
                event = SquarePulse(start=time_on,stop=time_off,pulse_params=self.pulse_params)
            elif pulse_type == _PULSE_TYPES[3]:
                event = LorentzPulse(start=time_on,stop=time_off,pulse_params=self.pulse_params)
            elif pulse_type == _PULSE_TYPES[4]:
                event = ArbitraryPulse(start=time_on,stop=time_off,pulse_params=self.pulse_params)
        elif evt_type == "Marker":
            if pulse_type == _GREEN_AOM:
                event = Green(start=time_on,stop=time_off,connection_dict=self.connection_dict)
            elif pulse_type == _ADWIN_TRIG:
                event = Measure(start=time_on,stop=time_off,connection_dict=self.connection_dict)
            elif pulse_type == _MW_S1:
                event = S1(start=time_on,stop=time_off,connection_dict=self.connection_dict)
            elif pulse_type == _MW_S2:
                event = S2(start=time_on,stop=time_off,connection_dict=self.connection_dict)
        else:
            event = SequenceEvent(start=time_on,stop=time_off)
        self.event_train.append(event)

    def add_event_train(self, time_on=1e-6, time_off=1.1e-6, separation=0.0, events_in_train=1, evt_type="Wave",
                        pulse_type='Gauss'):
        """This method adds multiple events to the channel
        :param time_on: starting time of the event
        :param time_off: ending time of the event
        :param separation: optional separation between the events
        :param events_in_train: number of events to add to the train
        :param evt_type: type of event
        :param pulse_type: type of pulse
        """
        # add this pulse to the current pulse channel
        self.add_event(time_on=time_on,time_off=time_off,evt_type=evt_type,pulse_type=pulse_type)
        width = self.event_train[0].duration
        sep = Decimal(separation)
        if events_in_train > 1:
            for nn in range(events_in_train-1):
                t_on = time_on + (nn+1)*(width + sep)
                t_off = time_off + (nn+1)*(width + sep)
                self.add_event(time_on=t_on,time_off=t_off,evt_type=evt_type,pulse_type=pulse_type)
        self.set_latest_channel_event()
        self.set_first_channel_event()

    def delete_event(self, index):
        if self.num_of_events > 0:
            evt = self.event_train.pop(index)
            self.num_of_events -= 1
            self.event_channel_index -= 1
            self.set_latest_channel_event()
            self.set_first_channel_event()
            return True
        else:
            return False

    def has_coincident_events(self):
        found_coincident_event = False
        evt_on_times = []
        #evt_off_times = []
        for evt in self.event_train:
            evt_on_times.extend(evt.t1_idx)
        if len(evt_on_times) > len(set(evt_on_times)):
            found_coincident_event = True
        return found_coincident_event


    def set_first_channel_event(self):
        if self.num_of_events > 1:
            self.first_channel_event = sorted(self.event_train, key=lambda x: x.start)[0].t1_idx
        elif self.num_of_events == 1:
            self.first_channel_event = self.event_train[0].t1_idx
        else:
            self.first_channel_event = 0

    def set_latest_channel_event(self):
        self.latest_channel_event = 0
        for i in range(self.num_of_events):
            if self.event_train[i].t2_idx > self.latest_channel_event:
                self.latest_channel_event = self.event_train[i].t2_idx
    # @property
    # def first_channel_event(self):
    #     self.__first_channel_event = np.amin(np.array(self.event_start_times))
    #     return self.__first_channel_event
    #
    # @first_channel_event.setter
    # def first_channel_event(self,var):
    #     self.__first_channel_event = var

class Sequence:
    def __init__(self, sequence, delay=[0, 0], pulseparams=None, connectiondict=None, timeres=1):
        """Class that implements a sequence, with args:
            :param sequence: list specifying sequence in the form [type,start,stop, optionalparams],eg. here is
            Rabi sequence
                [['S1', ' 1000', ' 1000+t'],
                ['Green', '2000+t', '5000+t'],
                ['Measure', '2000+t', '2100+t']]

                Another sequence for a gaussian pulse would be
                [['Wave','1000','2000','Gauss'],
                ['Green', '2000+t', '5000+t'],
                ['Measure', '2000+t', '2100+t']]
            :param delay: list with [AOM delay, MW delay] , possibly other delays to be added.
            :param pulseparams: a dictionary containing the amplitude, pulsewidth,SB frequency,IQ scale factor,
                        phase, skewphase
            :param connectiondict: a dictionary of the connections between AWG channels and switches/IQ modulators
            :param timeres: clock rate in ns

            After creating the instance, call the method create_sequence with an optional increment of time ,
            and then the arrays created will be: wavedata (analag I and Q data), c1markerdata, c2markerdata
                """
        # start the class logger
        self.logger = logging.getLogger('seqlogger.seq_class')
        self.seq = sequence
        self.timeres = timeres

        if pulseparams == None:
            self.pulseparams = _PULSE_PARAMS
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

    def create_sequence(self, dt=0):
        """Creates the data for the sequence.
        :param dt: Increment in time.
        """

        # get the AOM delay
        aomdelay = int((self.delay[0] + self.timeres / 2) / self.timeres)  # proper way of rounding delay[0]/timeres
        self.logger.info("AOM delay is found to be %d", aomdelay)
        # get the MW delay
        mwdelay = int((self.delay[1] + self.timeres / 2) // self.timeres)
        self.logger.info("MW delay is found to be %d", mwdelay)

        # first increment the sequence by dt if needed
        for seq_event in self.seq:
            seq_event.increment_time(dt)

        # TODO : Start working here


class SequenceList(object):
    def __init__(self, sequence, delay=[0, 0], scanparams=None, pulseparams=None, connectiondict=None, timeres=1):
        """This class creates a list of sequence objects that each have the waveforms for one step in the scanlist.
        Currently the only real new argument is
        :param scanparams : a dictionary that specifies the type, start, stepsize, number of steps
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
        self.scanlist = np.arange(self.scanparams['start'], self.scanparams['start'] + self.scanparams['stepsize'] *
                                  self.scanparams['steps'],  self.scanparams['stepsize'])
        self.delay = delay
        self.pulseparams = pulseparams
        self.connectiondict = connectiondict
        self.timeres = timeres
        self.sequence = sequence
        self.sequencelist = []

    def create_sequence_list(self):
        # dt = float(self.scanparams['stepsize'])
        if self.scanparams['type'] == 'no scan':
            s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
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
                    self.pulseparams['num pulses'] = int(x) + 1
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'Carrier frequency':
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
