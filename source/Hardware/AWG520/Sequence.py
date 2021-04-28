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
from typing import List

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
    def __init__(self, event_type= 'Wave', start=1.0*_us, stop=1.1 *_us, start_increment=0, stop_increment=0,
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

    @property
    def event_type(self):
        return self.__event_type

    @event_type.setter
    def event_type(self, var):
        if type(var) == str:
            self.__event_type = var
        else:
            ValueError('Event type must be a string')

    @property
    def start(self):
        return self.__start

    @start.setter
    def start(self, var):
        if type(var) == float:
            self.__start = var / self.sampletime
        else:
            ValueError('start time must be a floating point number')

    @property
    def stop(self):
        return self.__stop

    @stop.setter
    def stop(self, var):
        if type(var) == float:
            self.__stop = var / self.sampletime
        else:
            ValueError('stop time must be a floating point number')

    @property
    def start_increment(self):
        return self.__start_increment

    @start_increment.setter
    def start_increment(self, var):
        if type(var) == int:
            self.__start_increment = var
        else:
            ValueError('start increment must be integer')

    @property
    def stop_increment(self):
        return self.__stop_increment

    @stop_increment.setter
    def stop_increment(self, var):
        if type(var) == int:
            self.__stop_increment = var
        else:
            ValueError('stop increment must be integer')

    @property
    def duration(self):
        return self.__duration

    @duration.setter
    def duration(self, var):
        if type(var) == float:
            self.__duration = var
        else:
            ValueError('duration must be a floating point number')

    @property
    def sampletime(self):
        return self.__sampletime

    @sampletime.setter
    def sampletime(self, var):
        if type(var) == float:
            self.__sampletime = var
        else:
            ValueError('sample time must be a floating point number')

    def increment_time(self, dt=0):
        """Increments the start and stop times by dt.
        :param dt: The time increment.
        """
        dt = dt / self.sampletime
        self.start += dt * self.start_increment
        self.stop += dt * self.stop_increment

class WaveEvent(SequenceEvent):
    """ Provides functionality for events that are analog in nature. Inherits from :class:`sequence event <SequenceEvent>`
    :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param pulse_type: type of pulse desired, eg Gauss, Sech etc
    :param waveidx: a number that keeps track of the event index
    """
    # these 2 class variables keep track of the class type and the number of instances
    EVENT_KEYWORD = "Wave"
    _wavecounter = 0
    def __init__(self, start=1e-6, stop=1.1e-7, pulse_params=None, pulse_type='Gauss'):
        super().__init__()
        WaveEvent._wavecounter += 1 # increment the wave counter
        self.waveidx = _wavecounter # publicly accessible id for the wave event
        self.event_type = self.EVENT_KEYWORD
        if pulse_params==None:
            self.pulse_params = _PULSE_PARAMS
        self.start = start
        self.stop = stop

        self.pulse_type = pulse_type
        self.waveidx = waveidx
        self.__extract_pulse_params_from_dict()
        zerosdata = np.zeros(self.duration, dtype=_IQTYPE)
        pulse = Pulse(self.waveidx, self.duration, self.__ssb_freq, self.__iqscale,
                      self.__phase, self.__skew_phase)
        pulse.iq_generator(zerosdata)
        self.data = np.array((pulse.I_data, pulse.Q_data))

    @property
    def pulse_params(self):
        return self.__iq_params
    @pulse_params.setter
    def pulse_params(self, iqdic):
        if type(iqdic) == dict:
            self.__iq_params = iqdic
        else:
            ValueError('IQ params must be a dictionary')

    @property
    def pulse_type(self):
        return self.__pulse_type
    @pulse_type.setter
    def pulse_type(self, var:str):
        if type(var) == str:
            if var in _PULSE_TYPES:
                self.__pulse_type = var
            else:
                ValueError(f'Pulse type must be of type {_PULSE_TYPES}')
        else:
            ValueError('wave type must be a string')

    def __extract_pulse_params_from_dict(self):
        """This helper method simply extracts the relevant params from the iq dictionary"""
        self.__ssb_freq = float(self.pulse_params['SB freq']) * _MHz  # SB freq is in units of Mhz
        self.__iqscale = float(self.pulse_params['IQ scale factor'])
        self.__phase = float(self.pulse_params['phase'])
        self.__deviation = int(self.pulse_params['pulsewidth']) / self.sampletime
        self.__amp = int(self.pulse_params['amplitude'])  # needs to be a number between 0 and 100
        self.__skew_phase = float(self.pulse_params['skew phase'])
        self.__npulses = self.pulse_params['num pulses'] # not needed for a single WaveEvent

    @property
    def data(self):
        return self.__data
    @data.setter
    def data(self,datarr):
        self.__data = datarr

#TODO: looks to me like we can probably get rid of the Pulse module and move all the data generation here. will make
# it more self-contained.
class GaussPulse(WaveEvent):
    """Generates a Wave event with a Gaussian shape"""
    PULSE_KEYWORD = "Gauss"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD

        pulse = Gaussian(self.waveidx, self.duration, self.__ssb_freq, self.__iqscale, self.__phase,
                         self.__deviation, self.__amp, self.__skew_phase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class SechPulse(WaveEvent):
    """Generates a Wave event with a Sech shape"""
    PULSE_KEYWORD = "Sech"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Sech(self.waveidx, self.duration, self.__ssb_freq, self.__iqscale, self.__phase,
                     self.__deviation, self.__amp, self.__skew_phase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class SquarePulse(WaveEvent):
    """Generates a Wave event with a Square shape"""
    PULSE_KEYWORD = "Square"

    def __init__(self, start=1e-6, stop=1.1e-7,pulse_params):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Square(self.waveidx, self.duration, self.__ssb_freq, self.__iqscale, self.__phase, self.__amp,
                           self.__skew_phase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class LorentzPulse(WaveEvent):
    """Generates a Wave event with a Lorentzian shape"""
    PULSE_KEYWORD = "Lorentz"

    def __init__(self, start=1e-6, stop=1.1e-7,pulse_params):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Lorentzian(self.waveidx, self.duration, self.__ssb_freq, self.__iqscale, self.__phase,
                               self.__deviation, self.__amp, self.__skew_phase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class ArbitraryPulse(WaveEvent):
    """Generates a Wave event with any shape given by numerically generated data read from text file"""
    PULSE_KEYWORD = "Load Wfm"
    def __init__(self,start=1e-6, stop=1.1e-7,pulse_params,filename=''):
        super().__init__(start=start, stop=stop,pulse_params=pulse_params)
        self.pulse_type = self.PULSE_KEYWORD
        self.__filename = filename
        pulse = LoadWave(self.__filename, self.waveidx, self.duration, self.__ssb_freq, self.__iqscale,
                             self.__phase, self.__deviation, self.__amp, self.__skew_phase)
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
        pulse = Marker(num=self.markeridx,width=self.duration,markernum=0,marker_on=self.start,marker_off=self.stop)
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
        pulse = Marker(num=self.markeridx, width=self.duration, markernum=self.markernum, marker_on=self.start,
                       marker_off=self.stop)
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
        pulse = Marker(num=self.markeridx, width=self.duration, markernum=self.markernum, marker_on=self.start,
                       marker_off=self.stop)
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
        pulse = Marker(num=self.markeridx, width=self.duration, markernum=self.markernum, marker_on=self.start,
                       marker_off=self.stop)
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
        pulse = Marker(num=self.markeridx, width=self.duration, markernum=self.markernum, marker_on=self.start,
                       marker_off=self.stop)
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

    def __init__(self, event_train: List[SequenceEvent] = None, delay=None, pulse_params=None, connection_dict=None):
        if delay is None:
            delay = [0, 0]
        if pulse_params is None:
            pulse_params = _PULSE_PARAMS
        if connection_dict is None:
            connection_dict = _CONN_DICT
        if event_train is None:
            event_train = [Green(connection_dict),Measure(connection_dict)]
        self.logger = logging.getLogger('seqlogger.channel')
        self.event_train = event_train
        self.delay = delay
        self.pulse_params = pulse_params
        self.connection_dict = connection_dict

        # init the arrays
        self.wavedata = None
        self.c1markerdata = None
        self.c2markerdata = None

        # set the maximum length to be zero for now
        self.maxend = 0
        # set various object variables
        self.num_of_events = len(event_train) # number of events in the channel
        self.event_channel_index = 0 # index of event in channel
        self.latest_channel_event = 0 # channel event with latest time
        self.first_channel_event = 0 # channel event with earliest time
        self.event_type = event_train[0].event_type # type of channel events

        if self.num_of_events == 1 or self.num_of_events == 0:
            self.separation = 0.0

        # array storing all the start and stop times in this channel
        self.event_start_times = []
        self.event_stop_times = []
        for idx, evt in self.event_train:
            self.event_start_times.append(round(evt.start))
            self.event_stop_times.append(round(evt.stop))

        self.latest_channel_event = np.amax(np.array(self.event_stop_times))
        self.first_channel_event = np.amin(np.array(self.event_start_times))

    def add_event(self,time_on=1e-6,time_off=1.1e-6,evt_type='Wave',pulse_type="Gauss"):
        self.num_of_events += 1
        self.event_channel_index += 1
        event = SequenceEvent()
        if evt_type == "Wave":
            if pulse_type == _PULSE_TYPES[0]:
                event = GaussPulse(self.pulse_params)
            elif pulse_type == _PULSE_TYPES[1]:
                event = SechPulse(self.pulse_params)
            elif pulse_type == _PULSE_TYPES[2]:
                event = SquarePulse(self.pulse_params)
            elif pulse_type == _PULSE_TYPES[3]:
                event = LorentzPulse(self.pulse_params)
            elif pulse_type == _PULSE_TYPES[4]:
                event = ArbitraryPulse(self.pulse_params)
        elif evt_type == "Marker":
            if pulse_type == _GREEN_AOM:
                event = Green(self.connection_dict)
            elif pulse_type == _ADWIN_TRIG:
                event = Measure(self.connection_dict)
            elif pulse_type == _MW_S1:
                event = S1(self.connection_dict)
            elif pulse_type == _MW_S2:
                event = S2(self.connection_dict)
        else:
            event = SequenceEvent(start=time_on,stop=time_off)

        event.start = time_on
        event.stop = time_off
        self.event_train.append(event)

    def add_event_train(self, time_on=1e-6, time_off=1.1e-6, separation=0.0, events_in_train=1, evt_type="Wave",
                        pulse_type='Gauss'):
        # add this pulse to the current pulse channel
        self.num_of_events += events_in_train
        evt = SequenceEvent()

        if self.num_of_events != 1:
            for nn in range(events_in_train):
                self.add_event()
                self.event_train.start = time_on + round(nn * (self.event_train[nn].duration + separation),10)
        else:
            pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation,
                                     pulses_in_train=pulses_in_train)
        self.num_pulses += int(pulse_train.pulses_in_train)
        self.setLatestChannelEvent()
        self.setFirstChannelEvent()

    def deletePulseTrain(self, index):
        if self.num_of_pulse_trains > 0:
            pulse_train = self.pulse_trains.pop(index)
            self.num_of_pulse_trains -= 1
            self.setLatestChannelEvent()
            self.setFirstChannelEvent()
            return True
        else:
            return False

    def has_coincident_events(self):
        found_coincident_event = False
        pulse_on_times = []
        pulse_off_times = []
        for pulse_train in self.pulse_trains:
            pulse_on_times.extend(pulse_train.pulse_on_times)
        if len(pulse_on_times) > len(set(pulse_on_times)):
            found_coincident_event = True
        return found_coincident_event

    def setFirstChannelEvent(self):
        if self.num_of_pulse_trains > 1:
            self.first_channel_event = sorted(self.pulse_trains, key=lambda x: x.first_pulse_train_event)[
                0].first_pulse_train_event
        elif self.num_of_pulse_trains == 1:
            self.first_channel_event = self.pulse_trains[0].first_pulse_train_event
        else:
            self.first_channel_event = 0

    def setLatestChannelEvent(self):
        self.latest_channel_event = 0
        for i in range(self.num_of_pulse_trains):
            if self.pulse_trains[i].latest_pulse_train_event > self.latest_channel_event:
                self.latest_channel_event = self.pulse_trains[i].latest_pulse_train_event

    # TODO : Possibly make more self-explanatory function names
    def extract_pulse_params_from_dict(self):
        ssb_freq = float(self.pulse_params['SB freq']) * _MHz  # SB freq is in units of Mhz
        iqscale = float(self.pulse_params['IQ scale factor'])
        phase = float(self.pulse_params['phase'])
        deviation = int(self.pulse_params['pulsewidth']) // self.timeres
        amp = int(self.pulse_params['amplitude'])  # needs to be a number between 0 and 100
        skew_phase = float(self.pulse_params['skew phase'])
        npulses = self.pulse_params['num pulses']
        return ssb_freq, iqscale, phase, deviation, amp, skew_phase, npulses

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

        # get all the pulse params
        ssb_freq, iqscale, phase, deviation, amp, skew_phase, npulses = self.convert_pulse_params_from_dict()

        # first increment the sequence by dt if needed
        for seq_event in self.seq:
            seq_event.increment_time(dt)

        # TODO : Start working here

class Sequence:
    pass

class SequenceList:
    pass