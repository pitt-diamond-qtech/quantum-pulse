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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA import sys

import numpy as np
import logging
from decimal import Decimal, getcontext
from source.Hardware.AWG520.Pulse import Gaussian, Square, SquareI, SquareQ, Marker, Sech, Lorentzian, Gerono,LoadWave, Pulse, \
    DataIQ
from source.common.utils import log_with, create_logger, get_project_root
import re, sys, os, random

maindir = get_project_root()
# seqfiledir = maindir / 'Hardware/sequencefiles/'
pulseshapedir = maindir / 'arbpulseshape/'
# logfiledir = maindir / 'logs/'
# print('the sequence file directory is {0} and log file directory is {1}'.format(seqfiledir.resolve(),logfiledir.resolve()))
modlogger = create_logger('seqlogger')

# unit conversion factors
_GHz = 1.0e9  # Gigahertz
_MHz = 1.0e6  # Megahertz
_us = 1.0e-6  # Microseconds
_ns = 1.0e-9  # Nanoseconds
getcontext().prec = 14  # precision with which values are stored

# keywords used by sequence parser
_MW_S1 = 'S1'  # disconnected for now
_MW_S2 = 'S2'  # channel 1, marker 1
_GREEN_AOM = 'Green'  # ch1, marker 2
_ADWIN_TRIG = 'Measure'  # ch2, marker 2
_WAVE = 'Wave'  # channel 1 and 2, analog I/Q data
_BLANK = 'Blank'  # new keyword which turns off all channels, to be implemented
_FULL = 'Full'  # new keyword which turns on all channels high, to be implemented
_MARKER = 'Marker'  # new keyword for any marker
_ANALOG1 = 'Analog1'  # new keyword for channel 1
_ANALOG2 = 'Analog2'  # new keyword for channel 2
_RANDBENCH = "RandBench"  # new keyword for randomized benchmarking
# dictionary of connections from marker channels to devices,
_CONN_DICT = {_MW_S1: None, _MW_S2: 1, _GREEN_AOM: 2, _ADWIN_TRIG: 4}
# dictionary of IQ parameters that will be used as default if none is supplied
_PULSE_PARAMS = {'amplitude': 1000.0, 'pulsewidth': 20e-9, 'SB freq': 0.00, 'IQ scale factor': 1.0,
                 'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
# allowed values of the Waveform types
_PULSE_TYPES = ['Gauss', 'Sech', 'Square', 'Lorentz', 'SquareI', 'SquareQ', 'Gerono', 'Load Wfm']

_IQTYPE = np.dtype('<f4')  # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1')  # AWG520 stores marker values as 1 byte


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
    _counter = 0  # class variable keeps track of how many sequence events are there

    def __init__(self, event_type='', start=1.0 * _us, stop=1.1 * _us, start_increment=0.0, stop_increment=0.0,
                 sampletime=1.0 * _ns):
        SequenceEvent._counter += 1  # increment whenever a new event is created
        self.eventidx = SequenceEvent._counter  # publicly accessible value of the event id
        self.__event_type = event_type
        self.__start = start
        self.__stop = stop
        self.__start_increment = start_increment
        self.__stop_increment = stop_increment
        self.increment_time(dt=0.0)
        self.__duration = self.__stop - self.__start
        self.__sampletime = sampletime
        # these variables store the start, stop, and duration in units of the sampletime, useful for indexing arrays
        # and writing data to the AWG
        self.__t1_idx = round(Decimal(self.start / self.sampletime))
        self.__t2_idx = round(Decimal(self.stop / self.sampletime))
        self.__dur_idx = round(Decimal(self.duration / self.sampletime))
        # data for the event
        self.data = None

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
        self.__start = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__start = float(var)
        #     else:
        #         raise TypeError('start time must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def stop(self):
        return self.__stop

    @stop.setter
    def stop(self, var):
        self.__stop = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__stop = float(var)
        #     else:
        #         raise TypeError('stop time must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def start_increment(self):
        return self.__start_increment

    @start_increment.setter
    def start_increment(self, var):
        self.__start_increment = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__start_increment = float(var)
        #     else:
        #         raise TypeError('start increment must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def stop_increment(self):
        return self.__stop_increment

    @stop_increment.setter
    def stop_increment(self, var):
        self.__stop_increment = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__stop_increment = float(var)
        #     else:
        #         raise TypeError('stop increment must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def duration(self):
        return self.__duration

    @duration.setter
    def duration(self, var):
        self.__duration = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__duration = float(var)  # duration is kept as a floating point number for easy manipulation
        #     else:
        #         raise TypeError('duration must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def sampletime(self):
        return self.__sampletime

    @sampletime.setter
    def sampletime(self, var):
        self.__sampletime = float(var)
        # try:
        #     if type(var) == float or type(var) == int:
        #         self.__sampletime = float(var)
        #     else:
        #         raise TypeError('sample time must be a floating point number or integer')
        # except TypeError as err:
        #     modlogger.error("Type error {0}".format(err))

    @property
    def t1_idx(self):  # this variable stores the start time in integer format suitable for indexing arrays
        self.__t1_idx = round(Decimal(self.start / self.sampletime))
        return self.__t1_idx

    @property
    def t2_idx(self):  # this variable stores the stop time in integer format suitable for indexing arrays
        self.__t2_idx = round(Decimal(self.stop / self.sampletime))
        return self.__t2_idx

    @property
    def dur_idx(self):  # this variable stores the start time in integer format suitable for indexing arrays
        self.__dur_idx = round(Decimal(self.duration / self.sampletime))
        return self.__dur_idx

    def increment_time(self, dt: float = 0):
        """Increments the start and stop times by dt.
        :param dt: The time increment.
        """
        # dt = round(Decimal(dt / self.sampletime))
        dt = float(dt)  # convert to decimal to allow arithmetic
        self.start += dt * self.start_increment
        self.stop += dt * self.stop_increment


class WaveEvent(SequenceEvent):
    """Provides functionality for events that are analog in nature. Inherits from :class:`sequence event <SequenceEvent>`
    :param start: start time for event
    :param stop: stop time for event
    :param start_inc: increment for start time
    :param stop_inc: increment for stop time
    :param dt: increment value
    :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param pulse_type: type of pulse desired, eg Gauss, Sech etc
    :param sampletime: the sampling time (clock rate) used for this event
    """
    # these 2 class variables keep track of the class type and the number of instances
    EVENT_KEYWORD = "Wave"
    _wavecounter = 0

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, pulse_type='Gauss', start_inc=0.0, stop_inc=0.0,
                 dt=0.0, sampletime=1.0 * _ns):
        super().__init__(start=1e-6, stop=1.1e-6, start_increment=start_inc, stop_increment=stop_inc,
                         sampletime=sampletime)
        WaveEvent._wavecounter += 1  # increment the wave counter
        self.waveidx = WaveEvent._wavecounter  # publicly accessible id for the wave event
        self.event_type = self.EVENT_KEYWORD
        if pulse_params is None:
            pulse_params = _PULSE_PARAMS
        self.pulse_params = pulse_params
        self.start = start
        self.stop = stop
        self.increment_time(dt)
        self.duration = self.stop - self.start
        self.__pulse_type = pulse_type
        self.extract_pulse_params_from_dict()  # unpack the dictionary of pulse params
        zerosdata = np.zeros(self.dur_idx, dtype=_IQTYPE)  # create an array ofcc zeros of the right size
        pulse = Pulse(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale,
                      self.phase, self.skewphase)  # create a blank Pulse object
        pulse.iq_generator(zerosdata)
        self.data = np.array((pulse.I_data, pulse.Q_data))  # initialize the data to be zero

    @property
    def pulse_params(self):
        return self.__pulse_params

    @pulse_params.setter
    def pulse_params(self, iqdic):
        try:
            if type(iqdic) == dict:
                self.__pulse_params = iqdic
            else:
                raise TypeError('IQ params must be a dictionary')
        except TypeError as err:
            modlogger.error('Type error: {0}'.format(err))

    @property
    def pulse_type(self):
        return self.__pulse_type

    @pulse_type.setter
    def pulse_type(self, var: str):
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
        self.__ssb_freq = float(self.pulse_params['SB freq'])  # SB freq is in units of Mhz
        self.__iqscale = float(self.pulse_params['IQ scale factor'])
        self.__phase = float(self.pulse_params['phase'])
        # TODO: should i divide by sampletime ?
        self.__pulsewidth = float(self.pulse_params['pulsewidth'])
        self.__amp = float(self.pulse_params['amplitude'])  # needs to be a number between 0 and 100
        self.__skew_phase = float(self.pulse_params['skew phase'])
        self.__npulses = int(self.pulse_params['num pulses'])  # not needed for a single WaveEvent

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, datarr):
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


# TODO: looks to me like we can probably get rid of the Pulse module and move all the data generation here. will make
# it more self-contained.
class GaussPulse(WaveEvent):
    """Generates a Wave event with a Gaussian shape"""
    PULSE_KEYWORD = "Gauss"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        pwidth_idx = int(self.pulsewidth / self.sampletime)
        # if duration < 6 * pulsewidth, set it equal to at least that much
        if self.duration < 8 * self.pulsewidth:
            self.duration = 8 * self.pulsewidth
            self.stop = self.start + self.duration
        pulse = Gaussian(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         pwidth_idx, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class SechPulse(WaveEvent):
    """Generates a Wave event with a Sech shape"""
    PULSE_KEYWORD = "Sech"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        pwidth_idx = int(self.pulsewidth / self.sampletime)
        if self.duration < 8 * self.pulsewidth:
            self.duration = 8 * self.pulsewidth
            self.stop = self.start + self.duration

        # print(f'original pulsewidth {self.pulsewidth} converted pulsewidth {pwidth_idx}')
        # data = np.arange(self.duration * 1.0)
        pulse = Sech(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                     pwidth_idx, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class SquarePulse(WaveEvent):
    """Generates a Wave event with a Square shape"""
    PULSE_KEYWORD = "Square"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        # for square pulses, the pulsewidth and the duration are the same, so we comment out the next few lines
        # pwidth_idx = int(self.pulsewidth / self.sampletime)
        # if self.duration < 6 * self.pulsewidth:
        #     self.duration = 6 * self.pulsewidth
        #     self.stop = self.start + self.duration
        pulse = Square(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, self.amplitude,
                       self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class LorentzPulse(WaveEvent):
    """Generates a Wave event with a Lorentzian shape"""
    PULSE_KEYWORD = "Lorentz"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        pwidth_idx = int(self.pulsewidth / self.sampletime)
        if self.duration < 8 * self.pulsewidth:
            self.duration = 8 * self.pulsewidth
            self.stop = self.start + float(self.duration)
        pulse = Lorentzian(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, pwidth_idx,
                           self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class GeronoPulse(WaveEvent):
    """Generates a Wave event with a Gerono shape"""
    PULSE_KEYWORD = "Gerono"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        pwidth_idx = int(self.pulsewidth / self.sampletime)
        # if duration < 6 * pulsewidth, set it equal to at least that much
        if self.duration < 8 * self.pulsewidth:
            self.duration = 8 * self.pulsewidth
            self.stop = self.start + self.duration
        pulse = Gerono(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         pwidth_idx, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))

class SquarePulseI(WaveEvent):
    """Generates a Wave event with a Square shape, only outputs on I channel"""
    PULSE_KEYWORD = "SquareI"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        # for square pulses, the pulsewidth and the duration are the same, so we comment out the next few lines
        # pwidth_idx = int(self.pulsewidth / self.sampletime)
        # if self.duration < 6 * self.pulsewidth:
        #     self.duration = 6 * self.pulsewidth
        #     self.stop = self.start + self.duration
        pulse = SquareI(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, self.amplitude,
                        self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class SquarePulseQ(WaveEvent):
    """Generates a Wave event with a Square shape, only outputs on Q channel"""
    PULSE_KEYWORD = "SquareQ"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, start_inc=0, stop_inc=0, dt=0, sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        self.pulse_type = self.PULSE_KEYWORD
        self.extract_pulse_params_from_dict()
        # for square pulses, the pulsewidth and the duration are the same, so we comment out the next few lines
        # pwidth_idx = int(self.pulsewidth / self.sampletime)
        # if self.duration < 6 * self.pulsewidth:
        #     self.duration = 6 * self.pulsewidth
        #     self.stop = self.start + self.duration
        pulse = SquareQ(self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase, self.amplitude,
                        self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class ArbitraryPulse(WaveEvent):
    """Generates a Wave event with any shape given by numerically generated data read from text file"""
    PULSE_KEYWORD = "Load Wfm"

    def __init__(self, start=1e-6, stop=1.1e-6, pulse_params=None, filename=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, pulse_params=pulse_params, start_inc=start_inc, stop_inc=stop_inc,
                         dt=dt, sampletime=sampletime)
        if filename is None:
            filename = 'test4.txt'
        self.pulse_type = self.PULSE_KEYWORD
        self.filename = pulseshapedir / filename
        self.extract_pulse_params_from_dict()
        pwidth_idx = int(self.pulsewidth / self.sampletime)
        if self.duration < 8 * self.pulsewidth:
            self.duration = 8 * self.pulsewidth
            self.stop = self.start + float(self.duration)
        pulse = LoadWave(self.filename, self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                         pwidth_idx, self.amplitude, self.skewphase)
        if 'IQdata.txt' in filename:
            pulse = DataIQ(self.filename, self.waveidx, self.dur_idx, self.ssb_freq, self.iqscale, self.phase,
                           pwidth_idx, self.amplitude, self.skewphase)
        pulse.data_generator()  # generate the data
        self.data = np.array((pulse.I_data, pulse.Q_data))


class MarkerEvent(SequenceEvent):
    """ Provides functionality for events that are digital in nature using marker output of AWG
    :param start: start time for marker event
    :param stop: stop time for marker event
    :param start_inc: increment for start time
    :param stop_inc: increment for stop time
    :param dt: increment value
    :param connection_dict: dictionary that specifies which markers are connected to which hardware
   :param sampletime: the sampling time (clock rate) used for this event
        """
    # these 2 class variables define the event type and track the number of marker events
    EVENT_KEYWORD = "Marker"
    _markercounter = 0

    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0.0, stop_inc=0.0, dt=0.0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, event_type=self.EVENT_KEYWORD, start_increment=start_inc,
                         stop_increment=stop_inc, sampletime=sampletime)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        MarkerEvent._markercounter += 1
        self.markeridx = MarkerEvent._markercounter  # public id of the marker event
        self.connection_dict = connection_dict
        self.pulse_type = self.EVENT_KEYWORD
        self.increment_time(dt)
        self.duration = self.stop - self.start
        self.markernum = 0  # default marker num , also ensures zero output
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=0, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
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

    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, connection_dict=connection_dict, start_inc=start_inc,
                         stop_inc=stop_inc, dt=dt, sampletime=sampletime)
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

    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, connection_dict=connection_dict, start_inc=start_inc,
                         stop_inc=stop_inc, dt=dt, sampletime=sampletime)
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

    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, connection_dict=connection_dict, start_inc=start_inc,
                         stop_inc=stop_inc, dt=dt, sampletime=sampletime)
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

    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(start=start, stop=stop, connection_dict=connection_dict, start_inc=start_inc,
                         stop_inc=stop_inc, dt=dt, sampletime=sampletime)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_MW_S2]
        self.pulse_type = self.PULSE_KEYWORD
        pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
                       marker_off=self.t2_idx)
        pulse.data_generator()
        self.data = pulse.data


class Blank(SequenceEvent):
    PULSE_KEYWORD = "Blank"
    """STILL NOT IMPLEMENTED FULLY"""
    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(event_type=_BLANK, start=1.0 * _us, stop=1.1 * _us, start_increment=0.0, stop_increment=0.0,
                 sampletime=1.0 * _ns)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_MW_S1]
        self.pulse_type = self.PULSE_KEYWORD
        # pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
        #                marker_off=self.t2_idx)
        #pulse.data_generator()
        #self.data = pulse.data

class Full(SequenceEvent):
    PULSE_KEYWORD = "Blank"
    """STILL NOT IMPLEMENTED FULLY"""
    def __init__(self, start=1e-6, stop=1.1e-6, connection_dict=None, start_inc=0, stop_inc=0, dt=0,
                 sampletime=1.0 * _ns):
        super().__init__(event_type=_BLANK, start=1.0 * _us, stop=1.1 * _us, start_increment=0.0, stop_increment=0.0,
                 sampletime=1.0 * _ns)
        if connection_dict is None:
            connection_dict = _CONN_DICT
        self.connection_dict = connection_dict
        self.markernum = self.connection_dict[_MW_S1]
        self.pulse_type = self.PULSE_KEYWORD
        # pulse = Marker(num=self.markeridx, width=self.dur_idx, markernum=self.markernum, marker_on=self.t1_idx,
        #                marker_off=self.t2_idx)
        #pulse.data_generator()

class Channel:
    """Provides functionality for a sequence of :class:`sequence events <SequenceEvent>`.
    :param ch_type: type of channel, e.g. Marker, Wave, RBenchMark
    :param event_train: A collection of :class:`sequence events <SequenceEvent>`.
    :param delay: Delay in the format [AOM delay, MW delay].
    :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param connection_dict: A dictionary of the connections between AWG channels and switches/IQ modulators.
    :param event_channel_idx: index of event in channel where event train is added
    :param sampletime: the sampling time (clock rate) used for this channel
    """

    def __init__(self, ch_type=None, event_train=None, delay=None, pulse_params=None, connection_dict=None,
                 event_channel_idx=0, sampletime=1.0 * _ns,**kwargs):

        if ch_type is None:
            ch_type = _MARKER
        if delay is None:
            delay = [0, 0]
        if pulse_params is None:
            pulse_params = _PULSE_PARAMS
        if connection_dict is None:
            connection_dict = _CONN_DICT
        if event_train is None:
            event_train = []  # add empty event
        # super().__init__(**kwargs)
        self.logger = logging.getLogger('seqlogger.channel')
        self.event_train = event_train
        self.delay = delay
        self.pulse_params = pulse_params
        self.connection_dict = connection_dict
        self.sampletime = sampletime
        # set various object variables
        self.num_of_events = len(self.event_train)  # number of events in the channel
        self.event_channel_index = event_channel_idx  # index of event in channel
        self.latest_channel_event = 0  # channel event with latest time
        self.first_channel_event = 0  # channel event with earliest time
        self.ch_type = ch_type  # type of channel events
        #
        if self.num_of_events == 1 or self.num_of_events == 0:
            self.separation = 0.0
        # array storing all the start and stop times in this channel
        self.event_start_times = []
        self.event_stop_times = []
        self.event_durations = []
        for idx, evt in self.event_train:
            self.event_start_times.append(evt.start)
            self.event_stop_times.append(evt.stop)

        self.set_first_channel_event()
        self.set_latest_channel_event()

    def add_event(self, time_on=1e-6, time_off=1.1e-6, pulse_type="Green", start_inc=0.0, stop_inc=0.0, dt=0.0,
                  fname=None):
        """This method adds one event of a given type to the channel
        :param time_on: starting time of the event
        :param time_off: ending time of the event
        :param pulse_type: type of pulse
        :param start_inc: increment for start time
        :param stop_inc: increment for stop time
        :param dt: increment for start and stop times
        :param fname: filename used for arbitrary pulse shapes
        """
        self.num_of_events += 1
        self.event_channel_index += 1
        temp_pulseparams = self.pulse_params.copy()
        event = SequenceEvent()  # no need for this statement, but pycharm complains event may be assigned before ref?
        # TODO: simplify this remaining code using a dictionary or other function reference list and a for loop
        if self.ch_type == _WAVE or self.ch_type == _RANDBENCH:
            if pulse_type == _PULSE_TYPES[0]:
                event = GaussPulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                   stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[1]:
                event = SechPulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                  stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[2]:
                event = SquarePulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                    stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[3]:
                event = LorentzPulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                     stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[4]:
                event = SquarePulseI(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                     stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[5]:
                event = SquarePulseQ(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                     stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[6]:
                event = GeronoPulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams, start_inc=start_inc,
                                     stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
            elif pulse_type == _PULSE_TYPES[-1]:
                event = ArbitraryPulse(start=time_on, stop=time_off, pulse_params=temp_pulseparams,
                                       start_inc=start_inc,
                                       stop_inc=stop_inc, filename=fname, dt=dt, sampletime=self.sampletime)
        elif pulse_type == _GREEN_AOM:
            event = Green(start=time_on, stop=time_off, connection_dict=self.connection_dict, start_inc=start_inc,
                              stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
        elif pulse_type == _ADWIN_TRIG:
            event = Measure(start=time_on, stop=time_off, connection_dict=self.connection_dict, start_inc=start_inc,
                                stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
        elif pulse_type == _MW_S1:
            event = S1(start=time_on, stop=time_off, connection_dict=self.connection_dict, start_inc=start_inc,
                           stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
        elif pulse_type == _MW_S2:
            event = S2(start=time_on, stop=time_off, connection_dict=self.connection_dict, start_inc=start_inc,
                           stop_inc=stop_inc, dt=dt, sampletime=self.sampletime)
        else:
            event = SequenceEvent(start=time_on, stop=time_off, start_increment=start_inc,
                                  stop_increment=stop_inc, sampletime=self.sampletime)
            event.increment_time(dt=dt)
        self.event_train.append(event)
        self.event_start_times.append(event.start)
        self.event_stop_times.append(event.stop)

    def add_event_train(self, time_on=1e-6, time_off=1.1e-6, separation=0.0, events_in_train=1, pulse_type='Gauss',
                        start_inc=0.0, stop_inc=0.0, dt=0.0, fname=None):
        """This method adds multiple events to the channel
        :param time_on: starting time of the event
        :param time_off: ending time of the event
        :param separation: optional separation between the events
        :param events_in_train: number of events to add to the train
        :param pulse_type: type of pulse
        :param start_inc: start increment multiplier
        :param stop_inc: stop increment multiplier
        :param dt: amount to increment
        :param fname: filename for arbitrary pulses
        """

        # add this pulse to the current pulse channel
        self.add_event(time_on=time_on, time_off=time_off, pulse_type=pulse_type, start_inc=start_inc,
                       stop_inc=stop_inc, dt=dt, fname=fname)  # make sure we add the increment first
        width = self.event_train[0].duration
        sep = float(separation)
        if events_in_train > 1:
            for nn in range(events_in_train - 1):
                t_on = time_on + (nn + 1) * (width + sep)
                t_off = time_off + (nn + 1) * (width + sep)
                # no need to add any more increments
                self.add_event(time_on=t_on, time_off=t_off, pulse_type=pulse_type, fname=fname)
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

    def insert_channel_events(self, newchan):
        """This method inserts new events from another channel into the channel of the same type"""
        # if the new channel events conflict with the current channel we need to insert it carefully
        earliest_start_time = self.first_channel_event
        latest_stop_time = self.latest_channel_event
        latest_start_time = np.amax(np.array(self.event_start_times, dtype=np.float32))
        push_time = float(latest_start_time - earliest_start_time)

        if self.ch_type == newchan.ch_type:
            events = newchan.event_train  # get all the events in the newchan
            self.num_of_events += len(events)  # update the number of events
            self.event_channel_index += len(events)  # update the event index
            for idx, evt in enumerate(newchan.event_train):
                # store any values of the start_increment and stop intcrement from the event
                temp1 = evt.start_increment
                temp2 = evt.stop_increment
                # check if the inserted channel start time conflicts with previous start times
                if (evt.start > earliest_start_time) and (evt.start < latest_stop_time):
                    evt.start_increment = 1  # set the increments to 1
                    evt.stop_increment = 1
                    evt.increment_time(dt=push_time)  # increment the event
                # restore the old values of increment
                evt.start_increment = temp1
                evt.stop_increment = temp2
            self.event_train.extend(events)  # extend the channel with these events
            self.event_start_times.extend(newchan.event_start_times)  # extend the start times
            self.event_stop_times.extend(newchan.event_stop_times)  # extedn the stop times
            # store the new start and stop times in the arrays
            for idx, evt in enumerate(self.event_train):
                self.event_start_times[idx] = evt.start
                self.event_stop_times[idx] = evt.stop
            # update the first and latest channel events
            self.set_first_channel_event()  # keep track of the new first channel event
            self.set_latest_channel_event()  # and the last channel event

        # # now we check all the other channels to see if we need to change any of their start/stop times
        # self.adjust_channel_times(chantype=newchan.ch_type)
        # self.set_first_sequence_event()
        # self.set_latest_sequence_event()

    def has_coincident_events(self):
        found_coincident_event = False
        evt_on_times = []
        # evt_off_times = []
        for evt in self.event_train:
            evt_on_times.extend(evt.t1_idx)
        if len(evt_on_times) > len(set(evt_on_times)):
            found_coincident_event = True
        return found_coincident_event

    def set_first_channel_event(self):
        if self.num_of_events > 1:
            self.first_channel_event = sorted(self.event_train, key=lambda x: x.start)[0].start
        elif self.num_of_events == 1:
            self.first_channel_event = self.event_train[0].start
        else:
            self.first_channel_event = 0
        self.event_start_times.sort()  # we will also keep this array sorted

    def set_latest_channel_event(self):
        self.latest_channel_event = 0
        for i in range(self.num_of_events):
            if self.event_train[i].stop > self.latest_channel_event:
                self.latest_channel_event = self.event_train[i].stop

        self.event_stop_times.sort()

    # def get_event_start_times(self):
    #     for idx, evt in self.event_train:
    #         self.event_start_times.append(evt.t1_idx)
    #     return self.event_start_times

    # def get_event_stop_times(self):
    #     for idx, evt in self.event_train:
    #         self.event_stop_times.append(evt.t2_idx)
    #     return self.event_stop_times
    #
    # def get_event_durations(self):
    #     for idx, evt in self.event_train:
    #         self.event_durations.append(evt.dur_idx)
    #     return self.event_durations

    # @property
    # def first_channel_event(self):
    #     self.__first_channel_event = np.amin(np.array(self.event_start_times))
    #     return self.__first_channel_event
    #
    # @first_channel_event.setter
    # def first_channel_event(self,var):
    #     self.__first_channel_event = var


class RandomGateChannel(Channel):
    # def __init__(self,ch_type=None, event_train=None, delay=None, pulse_params=None, connection_dict=None,
    #              event_channel_idx=0, sampletime=1.0 * _ns):
    #     super().__init__(ch_type=ch_type, event_train=event_train, delay=delay, pulse_params=pulse_params,
    #                      connection_dict=connection_dict,event_channel_idx=event_channel_idx, sampletime=sampletime)
    """Provides functionality for a random sequence of :class:`sequence events <SequenceEvent>`.
        :param ch_type: type of channel, e.g. Marker, Wave, RBenchMark
        :param event_train: A collection of :class:`sequence events <SequenceEvent>`.
        :param delay: Delay in the format [AOM delay, MW delay].
        :param pulse_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                            SB frequency, IQ scale factor, phase, skewPhase.
        :param connection_dict: A dictionary of the connections between AWG channels and switches/IQ modulators.
        :param event_channel_idx: index of event in channel where event train is added
        :param sampletime: the sampling time (clock rate) used for this channel
        :param lengths_list: list of lengths out of which one will be used to truncate the events
        :param numcompgateseqs: how many computational gate sequences to use
        """
    def __init__(self,ch_type=_RANDBENCH, pulse_params=None, sampletime=1.0 * _ns,**kwargs):
        super().__init__(ch_type=ch_type, pulse_params=pulse_params, sampletime=sampletime, **kwargs)
        kwargdic = dict([])
        for k, v in kwargs.items():
            kwargdic[k] = v
        # if kwargdic['ch_type'] is None:
        #     kwargdic['ch_type'] = _RANDBENCH
        # if kwargdic['pulse_params'] is None:
        #     kwargdic['pulse_params'] = _PULSE_PARAMS
        # if kwargdic['sampletime'] is None:
        #     kwargdic['sampletime'] = 1.0 * _ns
        # if kwargdic['connection_dict'] is None:
        #     kwargdic['connection_dict'] = _CONN_DICT
        # if kwargdic['delay'] is None:
        #     kwargdic['delay'] = [0,0]
        # if kwargdic['change_amp'] is None:
        #     kwargdic['change_amp'] = False
        # if kwargdic['change_width'] is None:
        #     kwargdic['change_width'] = True
        # if kwargdic['paulinum'] is None:
        #     kwargdic['paulinum'] = 0
        # pulse_params = kwargdic['pulse_params']
        # sampletime = kwargdic['sampletime']
        # ch_type = kwargdic['ch_type']
        # delay = kwargdic['delay']
        trunc_lengths = [2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96]  # The list of different truncation lengths
        if 'change_amp' not in kwargdic:
            kwargdic['change_amp'] = False
        if 'change_width' not in kwargdic:
            kwargdic['change_width'] = False
        if 'lengths_list' not in kwargdic:
            kwargdic['lengths_list']= trunc_lengths
        if 'numcompgateseqs' not in kwargdic:
            kwargdic['numcompgateseqs']= 4
        if 'compseqnum' not in kwargdic:
            kwargdic['compseqnum']= 1
        self.lengths_list = kwargdic['lengths_list']
        self.num_comp_gate_seqs = kwargdic['numcompgateseqs']
        self.change_width = kwargdic['change_width']
        self.change_amp = kwargdic['change_amp']
        self.comp_seq_num = kwargdic['compseqnum']


    def set_pauli_num(self,num=0):
        self.num_comp_gate_seqs = num
    def set_lengths_list(self,trunc_lengths:list):
        self.lengths_list = trunc_lengths

    def add_event_train(self,time_on=1e-6, time_off=1.1e-6, separation=0.0, events_in_train=1, pulse_type='Gauss',
                        start_inc=0.0, stop_inc=0.0, dt=0.0, fname=None):
        """This function implements a channel that will randomize the pulse sequence.
        :param events_in_train: length of the computational gate sequence
        :param separation: separation between events
        """
        """we have 3 types of pulses to generate: Pauli Gates (pi_x, pi_y and pi_z), Computational Gates (pi/2_x, 
        pi/2_y, pi/2_z) and the R gate (This is a custom gate to make sure the final measurement is an eigenstate of 
        sigma_z) 

        Parameters:
        Nl Number of different truncation lengths
        Ng = Different computational gate sequences
        Np = Number of Pauli Randomization
        Ne = Number of Total experiments

        """
        sep = float(separation)
        l_max = 100  # Max. Number of Computational gates that will be generated in each of the Ng sequences and then
        # truncated Nl times.
        Ng = self.num_comp_gate_seqs  # Number of Computational gate sequences
        pauli_gates = ['(identity)', '(+pi_x)', '(+pi_y)', '(+pi_z)', '(-pi_x)', '(-pi_y)', '(-pi_z)']  # The Set of Pauli gates
        comp_gates = ['(+pi/2_x)', '(+pi/2_y)', '(-pi/2_x)', '(-pi/2_y)']  # The set of Comp. gates



        """"Pauli operators and their eigenstates"""
        I = np.array([[1, 0], [0, 1]])  # Identity
        X = np.array([[0, 1], [1, 0]])  # Sx
        Y = np.array([[0, -1j], [1j, 0]])  # Sy
        Z = np.array([[1, 0], [0, -1]])  # Sz

        z0 = np.array([[1], [0]])  # |+z>
        z1 = np.array([[0], [1]])  # |-z>
        # x0 = np.round(np.array([[1], [1]]) / np.sqrt(2), 3)  # |+x>
        # x1 = np.round(np.array([[1], [-1]]) / np.sqrt(2), 3)  # |-x>
        # y0 = np.round(np.array([[1], [1j]]) / np.sqrt(2), 3)  # |+y>
        # y1 = np.round(np.array([[1], [-1j]]) / np.sqrt(2), 3)  # |-y>

        def rotation(spin_axis, angle):  # takes a rotation axis and an angle and returns a rotation matrix
            # return round(np.cos(angle/2),3)*I -1j* round(np.sin(angle/2),3)*spin_axis
            return np.cos(angle / 2) * I - 1j * np.sin(angle / 2) * spin_axis

        gate = {'(identity)' : I,
                '(+pi_x)' : rotation(X,np.pi),
                '(-pi_x)' : rotation(-1*X,np.pi),
                '(+pi_y)' : rotation(Y,np.pi),
                '(-pi_y)' : rotation(-1*Y,np.pi),
                '(+pi/2_x)' : rotation(X,np.pi /2),
                '(-pi/2_x)' : rotation(-1*X,np.pi /2),
                '(+pi/2_y)' : rotation(Y,np.pi/2),
                '(-pi/2_y)' : rotation(-1*Y,np.pi/2),
                '(+pi_z)': rotation(Z, np.pi),
                '(-pi_z)': rotation(-1 * Z, np.pi),
                '(+pi/2_z)': rotation(Z, np.pi / 2),
                '(-pi/2_z)': rotation(-1 * Z, np.pi / 2),
                '(Identity)' : I,
                '(+pi_X)' : rotation(X,np.pi),
                '(-pi_X)' : rotation(-1*X,np.pi),
                '(+pi_Y)' : rotation(Y,np.pi),
                '(-pi_Y)' : rotation(-1*Y,np.pi),
                '(+pi/2_X)' : rotation(X,np.pi /2),
                '(-pi/2_X)' : rotation(-1*X,np.pi /2),
                '(+pi/2_Y)' : rotation(Y,np.pi/2),
                '(-pi/2_Y)' : rotation(-1*Y,np.pi/2),
                '(+pi_Z)': rotation(Z, np.pi),
                '(-pi_Z)': rotation(-1 * Z, np.pi),
                '(+pi/2_Z)': rotation(Z, np.pi / 2),
                '(-pi/2_Z)': rotation(-1 * Z, np.pi / 2)
                }
        r_gate = {'(+pi/2_x)': rotation(X, np.pi / 2),
                  '(-pi/2_x)': rotation(-1 * X, np.pi / 2),
                  '(+pi/2_y)': rotation(Y, np.pi / 2),
                  '(-pi/2_y)': rotation(-1 * Y, np.pi / 2),
                  '(+pi/2_z)': rotation(Z, np.pi / 2),
                  '(-pi/2_z)': rotation(-1 * Z, np.pi / 2)
                  }
        replace_z_pi_dictionary = {'(identity)': '(identity)',
                                   '(+pi_x)': '(-pi_X)',
                                   '(-pi_x)': '(+pi_X)',
                                   '(+pi_y)': '(-pi_Y)',
                                   '(-pi_y)': '(+pi_Y)',
                                   '(+pi/2_x)': '(-pi/2_X)',
                                   '(-pi/2_x)': '(+pi/2_X)',
                                   '(+pi/2_y)': '(-pi/2_Y)',
                                   '(-pi/2_y)': '(+pi/2_Y)',
                                   }
        replace_z_cw_dictionary = {'(identity)': '(identity)',
                                   '(+pi_x)': '(+pi_y)',
                                   '(+pi_y)': '(-pi_x)',
                                   '(-pi_x)': '(-pi_y)',
                                   '(-pi_y)': '(+pi_x)',
                                   '(+pi_z)': '(identity)',
                                   '(-pi_z)': '(identity)'
                                   }
        replace_z_ccw_dictionary = {'(identity)': '(identity)',
                                    '(+pi_x)': '(-pi_y)',
                                    '(+pi_y)': '(+pi_x)',
                                    '(-pi_x)': '(+pi_y)',
                                    '(-pi_y)': '(-pi_x)',
                                    '(+pi_z)': '(identity)',
                                    '(-pi_z)': '(identity)'
                                    }
        """
        Generate the Ng computational gate sequences
        """

        def save_comp_seq(Ng, l_max):

            loc = maindir / 'SeqDesigns/RB/'
            file = loc / 'RB_Pauli.txt'
            try:
                os.mkdir(loc)
            except FileExistsError:
                pass

            if os.path.exists(file):
                Comp_seq_list = np.genfromtxt(file, dtype=str, delimiter='\n')
                Comp_seq_list = Comp_seq_list.reshape(int(len(Comp_seq_list) / l_max), l_max)
            else:
                Comp_seq_list = []
                for i in range(Ng):
                    Comp_seq_list.append([])
                for seq in Comp_seq_list:
                    for i in range(l_max):
                        seq.append(random.choice(comp_gates))
                f = open(file, 'w')
                for i in Comp_seq_list:
                    for j in i:
                        f.write(j + '\n')
                f.close()
            return Comp_seq_list

        """
        Choose one of the Ng sequences (j = 0, .. , Ng-1)  truncate it to length l 
        """

        def gen_G_list(Comp_seq_list, l, j):
            G_list = Comp_seq_list[j][:l]
            return G_list

        """Generate a list of l+2 Pauli gates randomly"""

        def gen_P_list(l):
            P_list = []
            for i in range(l + 2):
                P_list.append(random.choice(pauli_gates))
            return P_list

        def find_R(gate_list):
            M = I
            Rlist = []
            final_state = 'z0'
            for i in gate_list:
                M = np.matmul(gate[i], M)
            for i in r_gate:
                M2 = np.matmul(r_gate[i], M)
                if np.allclose(abs(np.inner(np.ndarray.flatten(z0), np.ndarray.flatten(np.matmul(M2, z0)))),
                               1) or np.allclose(
                    abs(np.inner(np.ndarray.flatten(z1), np.ndarray.flatten(np.matmul(M2, z0)))), 1):
                    Rlist.append(i)
            R = random.choice(Rlist)
            M3 = np.matmul(r_gate[R], M)
            if np.isclose(abs(np.inner(np.ndarray.flatten(z0), np.ndarray.flatten(np.matmul(M3, z0)))), 1):
                final_state = 'z0'
            elif np.isclose(abs(np.inner(np.ndarray.flatten(z1), np.ndarray.flatten(np.matmul(M3, z0)))), 1):
                final_state = 'z1'
            else:
                self.logger.error("Unable to find the R operator -- Aborting!!!")
            return R, final_state

        """"Generate the full sequence"""

        def full_sequence(l, j):
            G_list = gen_G_list(Comp_seq_list, l, j)
            P_list = gen_P_list(l)
            R, final_state = find_R(G_list)
            sequence = []
            for i in range(l):
                sequence.append(P_list[i])
                sequence.append(G_list[i])
            sequence.append(P_list[-2])
            sequence.append(R)
            sequence.append(P_list[-1])
            # print("the list of pauli gates is", P_list)
            # print("The list of computational gates is", G_list)
            # print("R = " + R)
            # print("The original sequence is", sequence)
            return sequence

        """"Replace the z gates by Identity followed by a change in the qubit frame"""

        def replace_z(old_sequence):
            flag = 0
            new_sequence = []
            gate = '(identity)'
            for i in old_sequence:
                if ((i in ['(+pi/2_z)']) and flag == 0) or ((i in ['(-pi/2_z)']) and flag == 1):
                    gate = '(identity)'
                    flag = -1
                elif ((i in ['(-pi/2_z)']) and flag == 0) or ((i in ['(+pi/2_z)']) and flag == 1):
                    gate = '(identity)'
                    flag = -2
                elif flag == -1:
                    gate = replace_z_cw_dictionary[i]
                elif flag == -2:
                    gate = replace_z_ccw_dictionary[i]
                elif i not in ['(+pi_z)', '(-pi_z)'] and flag == 0:
                    gate = i
                elif i not in ['(+pi_z)', '(-pi_z)'] and flag == 1:
                    gate = replace_z_pi_dictionary[i]
                elif i in ['(+pi_z)', '(-pi_z)'] and flag == 0:
                    flag = 1
                    gate = '(identity)'
                elif i in ['(+pi_z)', '(-pi_z)'] and flag == 1:
                    flag = 0
                    gate = '(identity)'
                new_sequence.append(gate)
            return new_sequence

        def find_final_state(gate_list):
            M = I
            for i in gate_list:
                M = np.matmul(gate[i], M)

            if np.isclose(abs(np.inner(np.ndarray.flatten(z0), np.ndarray.flatten(np.matmul(M, z0)))), 1):
                final_state_final = 'z0'
            elif np.isclose(abs(np.inner(np.ndarray.flatten(z1), np.ndarray.flatten(np.matmul(M, z0)))), 1):
                final_state_final = 'z1'
            else:
                print("error!!!")
            return final_state_final

        def strings_to_event(gate: str = '(identity)'):
            """We need to convert the list of strings into actual events. we assume that the pulse info given to the
            object is for a pi/2 pulse. if we need other gates such as pi pulse, we could change either the width
            or the amplitude """
            #temp_pulseparams = self.pulse_params.copy()
            #phase = temp_pulseparams['phase']  # it is assumed this phase given is for x-axis
            #amp = temp_pulseparams['amplitude']
            amp = 1.0
            widthfactor = 1.0
            phase = 0
            change_amp = self.change_amp
            change_width = self.change_width
            if gate == '(identity)':
                amp = 0  # we want identity to have 0 amplitude
            elif gate == '(+pi/2_x)' or gate == '(+pi/2_X)':
                pass
            elif gate == '(-pi/2_x)' or gate == '(-pi/2_X)':
                phase = 180
            elif gate == '(+pi/2_y)' or gate == '(+pi/2_Y)':
                phase =  90
            elif gate == '(-pi/2_y)' or gate == '(-pi/2_Y)':
                phase =  270
            elif gate == '(+pi_x)' or gate == '(+pi_X)':
                if change_width:
                    widthfactor = 2.0
                    # widthfactor = 2.0 * (t_off - t_on)
                elif change_amp:
                    amp = 2 * amp
                else:
                    pass
            elif gate == '(-pi_x)' or gate == '(-pi_X)':
                if change_width:
                    widthfactor = 2.0
                    # widthfactor = 2 * (t_off - t_on)
                elif change_amp:
                    amp = 2 * amp
                else:
                    pass
                phase = 180
            elif gate == '(+pi_y)' or gate == '(+pi_Y)':
                if change_width:
                    widthfactor = 2.0
                    # widthfactor = 2 * (t_off - t_on)
                elif change_amp:
                    amp = 2 * amp
                else:
                    pass
                phase = 90
            elif gate == '(-pi_y)' or gate == '(-pi_Y)':
                if change_width:
                    widthfactor = 2.0
                    # widthfactor = 2 * (t_off - t_on)
                elif change_amp:
                    amp = 2 * amp
                else:
                    pass
                phase = 270

            return amp, widthfactor, phase

        def closest(lst, K):
            lst = np.asarray(lst)
            idx = (np.abs(lst - K)).argmin()
            return lst[idx]

        Comp_seq_list = save_comp_seq(Ng, l_max)
        # find the length that is closest to the truncation lengths list
        length = closest(self.lengths_list,events_in_train)
        #length = self.lengths_list[events_in_train]  # Choose the truncation length from the L list (l=0,..,Nl-1).
        # Choose randomly which computational gate sequence to use (k=0,...,Ng-1).
        # pauli_k = random.randint(0,self.num_comp_gate_seqs-1)
        comp_seq_num = self.comp_seq_num - 1  # we substituded this for pauli_k so that the user can input the j (= 1...N_G)
        sequence = full_sequence(length, comp_seq_num)   # find the full sequence

        final_sequence = replace_z(sequence)  # replace Pi_z rotations by identity and frame switching

        # print("the final sequence is", final_sequence)
        # print(f'The final state is: {find_final_state(final_sequence)}')

        ## Now we convert the sequence into a list of events
        temp_pulseparams = self.pulse_params.copy()   # get a copy of pulse params
        num_events = len(final_sequence)
        # find the params for the first event
        amp, widthfactor, phase = strings_to_event(final_sequence[0])
        self.pulse_params['amplitude'] = temp_pulseparams['amplitude']*amp
        self.pulse_params['phase'] = temp_pulseparams['phase']+phase
        self.pulse_params['pulsewidth'] = temp_pulseparams['pulsewidth']*widthfactor
        # create first event with an event width given by multiplying the width factor if needed
        event_width = (time_off - time_on)*widthfactor
        self.add_event(time_on=time_on, time_off=time_on+event_width, pulse_type=pulse_type, start_inc=start_inc,
                       stop_inc=stop_inc, dt=dt, fname=fname)  # make sure we add the increment first
        # if the event width is too small, update it to the correct duration
        # if self.event_train[0].duration > event_width:
        #     event_width = self.event_train[0].duration
        # now do the same for the other events
        cum_event_train_duration = time_on + event_width
        if num_events > 1:
            for nn in range(num_events-1):
                amp, widthfactor, phase = strings_to_event(final_sequence[nn+1])
                self.pulse_params = temp_pulseparams.copy()
                self.pulse_params['amplitude'] *= amp
                self.pulse_params['phase'] += phase
                self.pulse_params['pulsewidth'] *= widthfactor
                event_width = (time_off - time_on) * widthfactor
                # if self.event_train[nn].duration > event_width:
                #     event_width = self.event_train[0].duration*widthfactor
                # t_on = time_on + (nn+1) * (event_width + sep)
                t_on = cum_event_train_duration
                t_off = t_on + event_width
                self.add_event(time_on=t_on, time_off=t_off, pulse_type=pulse_type, fname=fname)
                cum_event_train_duration += event_width
        self.set_first_channel_event()
        self.set_latest_channel_event()
        return find_final_state(final_sequence), final_sequence




def find_start_stop_increment_times(pulse):
    """This method finds the start, stop and increment factors from a list of strings"""
    start, stop, start_increment, stop_increment = (0.0, 0.0, 0.0, 0.0)
    if '+' in pulse[1]:
        t1, t2 = pulse[1].split('+')  # '1000+2t' becomes '1000' and '2t'
        start = float(t1)
        if t2 == 't':
            start_increment = 1.0
        else:
            start_increment = float(t2[:-1])
    else:
        start = float(pulse[1])
    if '+' in pulse[2]:
        t1, t2 = pulse[2].split('+')
        stop = float(t1)
        if t2 == 't':
            stop_increment = 1.0
        else:
            stop_increment = float(t2[:-1])
    else:
        stop = float(pulse[2])
    return start, stop, start_increment, stop_increment


class Sequence:
    def __init__(self, seqtext=None, delay=None, pulseparams=None, connectiondict=None, timeres=1):
        """Class that implements a collection of :class:`channels <Channel>`
            :param seqtext: string that specifies sequence in the form 'type,start,stop, optionalparams'\n,
            eg. here is Rabi sequence 'S1,1e-6,1.01e-6+t\nGreen,1.02e-6+t,4.02e-6+t\nMeasure,1.02e-6+t,1.12e-6+t'
            for a gaussian pulse would use 'Wave,1e-6,1e-6+t,Gauss\nGreen,2e-6+t,5e-6+t\nMeasure,2e-6+t,
            2.1e-6+t'
            :param delay: list with [AOM delay, MW delay] , possibly other delays to be added.
            :param pulseparams: a dictionary containing the amplitude, pulsewidth,SB frequency,IQ scale factor,
                        phase, skewphase
            :param connectiondict: a dictionary of the connections between AWG channels and switches/IQ modulators
            :param timeres: clock rate in ns

            After creating the instance, call the method create_sequence with an optional increment of time ,
            and then the arrays created will be: wavedata (analag I and Q data), c1markerdata, c2markerdata
        """
        if delay is None:
            delay = [0.0, 0.0]
        self.logger = logging.getLogger('seqlogger.seq_class')  # start the class logger
        if seqtext is None:
            seqtext = 'Green,0.6e-6,0.7e-6\nWave,1e-6+t,1.5e-6+t,SquareI,a=0.5,n=2\nMeasure,1.5e-6+t,1.8e-6+t'
        self.seq = []
        self.convert_text_to_seq(seqtext)  # this function creates the seq object, a list of list of strings
        self.timeres = float(timeres) * _ns  # old code was written assuming everything in ns, so fix that
        self.rb_nevents = 1  # this was created to account for the nevents variable when the scan is a random scan
        self.rbinfo_list = []  # a list created to save the random scan info (final states and final sequences)
        if pulseparams is None:
            self.pulseparams = _PULSE_PARAMS
        # if pulseparams == None:
        #    self.pulseparams = {'amplitude': 100, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,'phase': 0.0, 'skew phase':0.0, 'num pulses': 1}
        else:
            self.pulseparams = pulseparams
        if connectiondict is None:
            self.connectiondict = _CONN_DICT
        else:
            self.connectiondict = connectiondict
        self.delay = delay
        #
        self.num_of_channels = 0
        self.num_of_wait_events = 0
        self.channels = []
        self.channel_sampletimes = []
        self.seq_channel_indices = []
        self.wait_events = []  # handling waiting events separately since we simply turn everything off,
        # latest_sequence_event is the last time that a channel is turned off
        self.latest_sequence_event = 0
        self.first_sequence_event = 0
        # when doing random benchmarking we need to know whether to change amplitude or the width to create pi pulses
        # right now these are boolean variables, perhaps later we may want to allow for these to be numbers specified by user
        self.change_amp = False
        self.change_width = False
        self.paulinum = 4 # this variable is used in random benchmarking to pick one of the pauli random sequences
        # this variable is used in RB to fix the truncation lengths
        self.trunc_lengths = [2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96]
        # init the arrays
        self.wavedata = None
        self.c1markerdata = None
        self.c2markerdata = None


    def set_first_sequence_event(self):
        if self.num_of_channels > 1:
            temp_channels = []
            for channel in self.channels:
                channel.set_first_channel_event()
                if channel.num_of_events > 0:
                    temp_channels.append(channel)
            if len(temp_channels) > 0:
                self.first_sequence_event = sorted(temp_channels, key=lambda x: x.first_channel_event)[
                    0].first_channel_event
            else:
                self.first_sequence_event = 0
        if self.num_of_wait_events > 0:
            if float(self.wait_events[0]) < self.first_sequence_event:
                self.first_sequence_event = float(self.wait_events[0])

    def set_latest_sequence_event(self):
        self.latest_sequence_event = 0
        for idx, chan in enumerate(self.channels):
            if chan.latest_channel_event > self.latest_sequence_event:
                self.latest_sequence_event = chan.latest_channel_event
        if self.num_of_wait_events > 0:
            if float(self.wait_events[-1]) > self.latest_sequence_event:
                self.latest_sequence_event = float(self.wait_events[-1])

    def add_channel(self, ch_type):
        """Adds a channel of specified channel type, but does not yet add the events data"""
        self.num_of_channels += 1
        temp_pulseparams = self.pulseparams.copy()
        if self.num_of_channels > 1:
            evt_ch_idx = self.channels[-1].event_channel_index + 1
        else:
            evt_ch_idx = 0

        if ch_type == _RANDBENCH:
            channel = RandomGateChannel(ch_type=ch_type,delay=self.delay, pulse_params=temp_pulseparams,
                                            connection_dict=self.connectiondict, sampletime=self.timeres,
                                            event_channel_idx=evt_ch_idx,change_amp=self.change_amp,change_width=self.change_width, compseqnum = self.comp_seq_num)
        else:
            channel = Channel(ch_type=ch_type, delay=self.delay, pulse_params=temp_pulseparams,
                                  connection_dict=self.connectiondict, sampletime=self.timeres, event_channel_idx=
                                  evt_ch_idx)

        self.channels.append(channel)
        self.channel_sampletimes.append(self.timeres)
        self.seq_channel_indices.append(channel.event_channel_index)
        self.set_latest_sequence_event()
        self.set_first_sequence_event()

    def delete_channel(self, index):
        """deletes the channel object"""
        if self.num_of_channels > 0:
            self.channels.pop(index)
            self.num_of_channels -= 1
            self.seq_channel_indices.pop(index)
            self.set_latest_sequence_event()
            self.set_first_sequence_event()
            return True
        else:
            return False

    def adjust_channel_times(self, chantype='a1'):
        """this is a critical method that adjusts channel times for all other channels besides the one specified.
        THis is often needed when we either increment times in a given channel that would then end up conflicting
        with other channels start/stop times; or when we add new events into a channel
        :param chantype: string that gives the channel type that will not be adjusted """
        # first figure out which channel we are being asked to ignore
        insertchan = self.channels[0]
        for (idx, chan) in enumerate(self.channels):
            if chan.ch_type == chantype:
                insertchan = chan
        # here we get all the start and stop times that we need from that channel
        earliest_start_time = insertchan.first_channel_event
        latest_stop_time = insertchan.latest_channel_event
        latest_start_time = np.amax(np.array(insertchan.event_start_times, dtype=np.float32))
        push_time = float(latest_start_time - earliest_start_time)
        for (idx, chan) in enumerate(self.channels):
            if chan.ch_type != insertchan.ch_type:
                for idx, evt in enumerate(chan.event_train):
                    # store any values of the start_increment and stop intcrement from the event
                    temp1 = evt.start_increment
                    temp2 = evt.stop_increment
                    # check if the inserted channel start time conflicts with previous start times
                    if (evt.start > earliest_start_time) and (evt.start < latest_stop_time):
                        evt.start_increment = 1  # set the increments to 1
                        evt.stop_increment = 1
                        evt.increment_time(dt=push_time)  # increment the event
                    # restore the old values of increment
                    evt.start_increment = temp1
                    evt.stop_increment = temp2
                    # store the new start and stop times in the arrays
                    chan.event_start_times[idx] = evt.start
                    chan.event_stop_times[idx] = evt.stop
                # update the first and latest channel events
                chan.set_first_channel_event()
                chan.set_latest_channel_event()

    def convert_text_to_seq(self, seqtext):
        """This method parses the sequence definition which is currently just a string, and converts
        it to a list of list of strings.  Eventually may include more sophisticated parsing techniques, e.g. using a
        lexer/parser library like PLY, ATL5"""
        # get a list of all the lines in the text
        all_lines = seqtext.split('\n')
        b_all_lines = all_lines[:]  # make a copy
        # now iterate over the copy, and create a list of a list of strings which specify the sequence
        for (idx, line) in list(enumerate(b_all_lines)):
            wfm = line.split(',')
            self.seq.append(wfm)
            # b_all_lines[idx:idx] = [wfm]
        # self.seq = self.seq[:-1]
        # print('text box converted to', self.seq)

    ## Changes made by Gurudev 2020-07-08 : Modifying the unpacking of optional params so that order of the optional
    # params does not matter, also added in a new optional param phase = NN
    def unpack_optional_params(self, seq_idx=0):
        '''get the optional params in the list of strings
        :param seq_idx: index in the list of strings to unpack
        '''
        ch_type = self.seq[seq_idx][0]  # type of channel
        opt_params = self.seq[seq_idx][3:]  # all the optional parameters
        # currently we support 4 parameters: pulsetype, num-events, amplitude_scale,fname
        amplitude_scale = 1.0
        num_events = 1
        fname = None
        phase = self.pulseparams['phase']
        pulsetype = ''
        ## GURUDEV 2021-07-12: trying to fix issue that number scan is being overwritten by the nevents parameter
        temp_pulseparams = self.pulseparams.copy()
        ## GURUDEV 2021-07-23: for Randomized benchmarking, we need to know whether the width or the amplitude of the
        # event should be changed to make pi pulses
        change_amp = False
        change_width = False
        if ch_type == _WAVE:  # if the ch_type is Wave or RandBench, then we need several
            # other params
            simple_ptypes = _PULSE_TYPES[0:-1]  # the simple pulsetypes e.g. Gauss, Sech etc
            # at a minimum this type must be present
            try:
                if len(opt_params) >= 1:
                    pulsetype = opt_params[0]
                    if pulsetype in simple_ptypes:  # check whether pulsetype is of 1st 3 types
                        # check if there are any other optional parameters
                        if len(opt_params) > 4:
                            self.logger.warning(f"only 3 optional parameters supported for {pulsetype} channels")
                        for s in opt_params[1:]:
                            # the allowed patterns are amp = N.N, phase = N.N, num = N in any order
                            patt = r'(amp\s*\=\s*)(?P<amp>\d\.?\d*)|(phase\s*\=\s*)(?P<phase>\d\.?\d*)' \
                                   r'(?P<incp>\+\+)?|(n\s*=\s*)(?P<num>\d{,4})(?P<incn>\+\+)?'  ## Gurudev: trying this
                            m = re.search(patt, s)
                            if m:
                                if m.group('amp'):
                                    val = float(m.group('amp'))  # the match is returned in group 'amp'
                                    amplitude_scale = val if (0 <= val <= 1.0) else 1.0
                                if m.group('num'):
                                    val = int(m.group('num'))  # the match is returned in group 'num'
                                    num_events = val if (val > 1) else 1
                                if m.group('incn') == '++':  # we take the number from the pulseparams,
                                    # used when scanning the number of pulses
                                    num_events = temp_pulseparams['num pulses']
                                if m.group('phase'):
                                    val = Decimal(m.group('phase'))  # the match is returned in group 'phase'
                                    # we take the phase modulo 360 degrees, have to use Decimal for modulo to work
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                                if m.group('incp') == '++':
                                    # we take the phase from the pulseparams, used when scanning the phase
                                    val = temp_pulseparams['phase']
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                            else:
                                raise RuntimeError("Optional params must be of form amp = D.D or phase = D.D or n = D")
                    elif pulsetype == _PULSE_TYPES[-1]:  # this is for loading waveforms
                        # regex allows f = blah.txt, f = blah.csv ,fname = blah.txt etc
                        if len(opt_params) < 2:  # not enough optional parms were supplied
                            raise RuntimeWarning('Filename must be supplied else will use default')
                        if len(opt_params) > 5:
                            self.logger.error(f"only 4 optional parameters supported for {pulsetype} channels")
                            raise RuntimeError(f"only 4 optional parameters supported for {pulsetype} channels")
                        for s in opt_params[1:]:
                            # the allowed patterns are amp = N.N, phase = N.N, num = N, fname = ABC in any order
                            patt = r'(amp\s*\=\s*)(?P<amp>\d\.?\d*)|(phase\s*\=\s*)(?P<phase>\d\.?\d*)' \
                                   r'(?P<incp>\+\+)?|(n\s*=\s*)(?P<num>\d{,4})(?P<incn>\+\+)?|' \
                                   r'(fname\s*=\s*)(?P<file>\w+)\.(?P<ext>txt|csv)'
                            m = re.search(patt, s)
                            if m:
                                if m.group('amp'):
                                    val = float(m.group('amp'))  # the match is returned in group 'amp'
                                    amplitude_scale = val if (0 <= val <= 1.0) else 1.0
                                if m.group('num'):
                                    val = int(m.group('num'))  # the match is returned in group 'num'
                                    num_events = val if (val > 1) else 1
                                if m.group('incn') == '++':
                                    num_events = temp_pulseparams['num pulses']
                                if m.group('phase'):
                                    val = Decimal(m.group('phase'))  # the match is returned in group 'phase'
                                    # we take the phase modulo 360 degrees, have to use Decimal for modulo to work
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                                if m.group('incp') == '++':
                                    # we take the phase from the pulseparams, used when scanning the phase
                                    val = temp_pulseparams['phase']
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                                if m.group('file'):
                                    fname = m.group('file') + '.' + m.group('ext')
                            else:
                                raise RuntimeError("Optional params must be of form amp = D.D or phase = D.D or width++ "
                                                   "or fname = ABC.txt or fname = ABC.csv")
                    else:
                        raise RuntimeError(f'Supported types are {_PULSE_TYPES} for Wave channels')
                else:
                    raise RuntimeError('Must specify type of pulse for Wave channels')
            except (RuntimeWarning, RuntimeError) as err:
                self.logger.error('Runtime warning/error: {0}'.format(err))
                sys.stderr.write('Runtime warning/error: {0}\n'.format(err))
        elif ch_type == _RANDBENCH:
            """For the random benchmarking, we will use amp = 1.0++ to mean the amplitude should be 1.0 for a pi/2 pulse 
            and will be multiplied by 2 to get a pi pulse; phase = 10 means 10 degree is the x-axis, width++ means the
             width of the event should be multiplied by 2 to get a pi pulse; n = 1 means generate 1 pauli random sequence"""
            # other params
            simple_ptypes = _PULSE_TYPES[0:-1]  # the simple pulsetypes e.g. Gauss, Sech etc
            # at a minimum this type must be present
            try:
                if len(opt_params) >= 1:
                    pulsetype = opt_params[0]
                    if pulsetype in simple_ptypes:  # check whether pulsetype is of 1st 3 types
                        # check if there are any other optional parameters
                        if len(opt_params) > 5:
                            self.logger.warning(f"only 4 optional parameters supported for {pulsetype} channels")
                        for s in opt_params[1:]:
                            # the allowed patterns are amp = N.N++, phase = N.N, width++
                            patt = r'(amp\s*\=\s*)(?P<amp>\d\.?\d*)(?P<changea>\+\+)|(phase\s*\=\s*)(?P<phase>\d\.?\d*)' \
                                   r'|(?P<changew>width\+\+)|(n\s*=\s*)(?P<num>\d{,4})'  ## Gurudev: trying this
                            m = re.search(patt, s)
                            if m:
                                if m.group('amp'):
                                    val = float(m.group('amp'))  # the match is returned in group 'amp'
                                    amplitude_scale = val if (0 <= val <= 1.0) else 1.0
                                if m.group('changea'):  # match returned in group 'changea'
                                    change_amp = True
                                if m.group('changew'):
                                    change_width = True
                                if m.group('num'):
                                    val = int(m.group('num'))  # the match is returned in group 'num'
                                    num_events = val if (val > 1) else 1
                                if m.group('phase'):
                                    val = Decimal(m.group('phase'))  # the match is returned in group 'phase'
                                    # we take the phase modulo 360 degrees, have to use Decimal for modulo to work
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                            else:
                                raise RuntimeError("Optional params must be of form amp = D.D++ or phase = D.D or width++")
                    elif pulsetype == _PULSE_TYPES[-1]:  # this is for loading waveforms
                        # regex allows f = blah.txt, f = blah.csv ,fname = blah.txt etc
                        if len(opt_params) < 2:  # not enough optional parms were supplied
                            raise RuntimeWarning('Filename must be supplied else will use default')
                        if len(opt_params) > 6:
                            self.logger.error(f"only 5 optional parameters supported for {pulsetype} channels")
                            raise RuntimeError(f"only 4 optional parameters supported for {pulsetype} channels")
                        for s in opt_params[1:]:
                            # the allowed patterns are amp = N.N++, phase = N.N, num = N, fname = ABC, width++ in any order
                            patt = r'(amp\s*\=\s*)(?P<amp>\d\.?\d*)(?P<changea>\+\+)|(phase\s*\=\s*)(?P<phase>\d\.?\d*)' \
                                    r'|(?P<changew>width\+\+)|(n\s*=\s*)(?P<num>\d{,4})' \
                                   r'|(fname\s*=\s*)(?P<file>\w+)\.(?P<ext>txt|csv)'
                            m = re.search(patt, s)
                            if m:
                                if m.group('changea'):  # match returned in group 'changea'
                                    change_amp = True
                                if m.group('changew'):
                                    change_width = True
                                if m.group('phase'):
                                    val = Decimal(m.group('phase'))  # the match is returned in group 'phase'
                                    # we take the phase modulo 360 degrees, have to use Decimal for modulo to work
                                    phase = float(val % Decimal('360.0')) if (val > 360.0) else float(val)
                                if m.group('num'):
                                    val = int(m.group('num'))  # the match is returned in group 'num'
                                    num_events = val if (val > 1) else 1
                                if m.group('file'):
                                    fname = m.group('file') + '.' + m.group('ext')
                            else:
                                raise RuntimeError("Optional params must be of form amp = D.D++ or phase = D.D "
                                                   "or n = D or fname = ABC.txt or fname = ABC.csv")
                    else:
                        raise RuntimeError(f'Supported types are {_PULSE_TYPES} for Wave or Rand Bench channels')
                else:
                    raise RuntimeError('Must specify type of pulse for Wave or Rand Bench channels')
            except (RuntimeWarning, RuntimeError) as err:
                self.logger.error('Runtime warning/error: {0}'.format(err))
                sys.stderr.write('Runtime warning/error: {0}\n'.format(err))
        else:  # if channel type is marker, then only one other parameter is allowed, the number of pulses
            pulsetype = self.seq[seq_idx][0]  # the pulsetype and channel name are identical for marker types
            try:
                if opt_params is None:
                    num_events = 1
                elif len(opt_params) >= 1:
                    patt = r'(n\s*=\s*)(\d{,4})[\.]?'  # regex which allows 1 or n = 1
                    m = re.search(patt, str(opt_params[0]))
                    if opt_params[0] and m:
                        val = int(m.group(2))
                        num_events = val if (val > 1) else 1
                    else:
                        raise RuntimeError('only one opt param type n = D allowed for Marker types')
            except (RuntimeWarning, RuntimeError) as err:
                self.logger.error('Runtime warning/error: {0}'.format(err))
                sys.stderr.write('Runtime warning/error: {0}\n'.format(err))
        return pulsetype, amplitude_scale, num_events, fname, phase,change_width, change_amp

    def create_channels_from_seq(self, dt=0.0):
        """This method parses the sequence definition which is currently just a list of list of strings, and converts
        it to Channel objects.  Eventually may include more sophisticated parsing techniques, e.g. using a
        lexer/parser library like PLY, ATL5
        :param dt: increment for the start or stop times, will be multiplied by any increment factor specified in string"""

        t_start = np.zeros(len(self.seq))
        t_stop = t_start.copy()
        start_inc = t_start.copy()
        stop_inc = t_start.copy()
        num_event_train = t_start.copy()
        ch_type = []
        self.set_first_sequence_event()
        self.set_latest_sequence_event()
        temp_pulseparams = self.pulseparams.copy()  # this must be done as pulseparams is an immutable dict
        for i in range(len(self.seq)):  # loop through the list of list of strings
            self.pulseparams = temp_pulseparams.copy()  # get the original pulse params
            chan_name = self.seq[i][0]  # the first element is the name of the channel
            if chan_name not in ch_type:  # if the channel does not exist already
                ch_type.append(chan_name)
                # the first 3 in the list are mandatory
                t_start[i], t_stop[i], start_inc[i], stop_inc[i] = find_start_stop_increment_times(pulse=self.seq[i])
                # then we could have optional parameters
                ptype, ampfactor, nevents, fname, phase,change_width, change_amp = self.unpack_optional_params(seq_idx=i)
                # create the channel modifying the pulse params as needed for that channel
                self.pulseparams['amplitude'] = self.pulseparams['amplitude'] * ampfactor
                self.pulseparams['num pulses'] = nevents
                self.pulseparams['phase'] = phase  # added this on 2020-07-08 to change the phase as well
                num_event_train[i] = nevents
                self.change_amp = change_amp
                self.change_width = change_width
                self.add_channel(ch_type=ch_type[i])
                # get this last added channel
                ch = self.channels[-1]
                if ch.ch_type == _RANDBENCH:
                    #ch.set_pauli_num(self.paulinum)
                    ch.set_lengths_list(self.trunc_lengths)
                    nevents = self.rb_nevents  # this is the nevents value for random benchmarking
                    final_state, final_seq = ch.add_event_train(time_on=t_start[i], time_off=t_stop[i], start_inc=start_inc[i],
                                       stop_inc=stop_inc[i], pulse_type=ptype, events_in_train=nevents, dt=dt,
                                       fname=fname)
                    self.rbinfo_list = [final_state, final_seq]  # gathering these data to pass it to the app
                else:
                    ch.add_event_train(time_on=t_start[i], time_off=t_stop[i], start_inc=start_inc[i],
                                   stop_inc=stop_inc[i], pulse_type=ptype, events_in_train=nevents, dt=dt, fname=fname)
            else:  # we have an existing channel of this name
                # get all the parameters of the pulses to be added to the existing channel
                # the first 3 in the list are mandatory
                ch_type.append(chan_name)  # we still append the channel name
                t_start[i], t_stop[i], start_inc[i], stop_inc[i] = find_start_stop_increment_times(pulse=self.seq[i])
                # then we could have optional parameters
                ptype, ampfactor, nevents, fname, phase,change_width, change_amp = self.unpack_optional_params(seq_idx=i)
                # set the pulse params as needed for the pulse
                self.pulseparams['amplitude'] = self.pulseparams['amplitude'] * ampfactor
                self.pulseparams['num pulses'] = nevents
                self.pulseparams['phase'] = phase  # added this on 2020-07-08 to change the phase as well
                num_event_train[i] = nevents
                for (idx, chan) in enumerate(self.channels):
                    if chan.ch_type == chan_name:
                        tempchan = Channel(ch_type=chan_name, delay=self.delay, pulse_params=self.pulseparams,
                                           connection_dict=self.connectiondict, sampletime=self.timeres,
                                           event_channel_idx=
                                           self.channels[-1].event_channel_index + 1)
                        tempchan.add_event_train(time_on=t_start[i], time_off=t_stop[i], start_inc=start_inc[i],
                                                 stop_inc=stop_inc[i], pulse_type=ptype, events_in_train=nevents, dt=dt,
                                                 fname=fname)
                        chan.insert_channel_events(tempchan)

        for i in range(len(self.seq)):
            self.adjust_channel_times(chantype=ch_type[i])  # if we need to adjust all the channels after this
        self.set_first_sequence_event()
        self.set_latest_sequence_event()

    def create_sequence(self, dt=0.0):
        """Creates the data for the sequence.
        :param dt: Increment in time.
        """
        # get the AOM delay
        aomdelay = int((self.delay[0] + self.timeres / 2) / self.timeres)  # proper way of rounding delay[0]/timeres
        self.logger.info("AOM delay is found to be %d", aomdelay)
        # get the MW delay
        mwdelay = int((self.delay[1] + self.timeres / 2) // self.timeres)
        self.logger.info("MW delay is found to be %d", mwdelay)
        # create all the channels from the self.seq object
        self.create_channels_from_seq(dt=dt)
        # now we need to find the data length i.e. the largest stop time in the list of stop times
        maxend = np.int64(self.latest_sequence_event / self.timeres) + 1
        # print("the max. event value is {}".format(self.maxend))
        # now we can init the arrays
        # dummydata = np.zeros(maxend, dtype=_MARKTYPE)
        c1m1 = np.zeros(maxend, dtype=_MARKTYPE)
        c1m2 = c1m1.copy()
        c2m1 = c1m1.copy()
        c2m2 = c1m1.copy()
        waveI = np.zeros(maxend, dtype=_IQTYPE)
        waveQ = waveI.copy()

        for (idx, channel) in enumerate(self.channels):
            if channel.ch_type == _WAVE or channel.ch_type == _RANDBENCH:
                for (n, evt) in enumerate(channel.event_train):
                    waveI[evt.t1_idx:evt.t2_idx] = evt.data[0]
                    waveQ[evt.t1_idx:evt.t2_idx] = evt.data[1]
            elif channel.ch_type == _GREEN_AOM:
                for (n, evt) in enumerate(channel.event_train):
                    c1m2[evt.t1_idx:evt.t2_idx] = evt.data
                c1m2 = np.roll(c1m2, -aomdelay)
            elif channel.ch_type == _MW_S2:
                for (n, evt) in enumerate(channel.event_train):
                    c1m1[evt.t1_idx:evt.t2_idx] = evt.data
                c1m1 = np.roll(c1m1, -mwdelay)
            elif channel.ch_type == _MW_S1:
                for (n, evt) in enumerate(channel.event_train):
                    c2m1[evt.t1_idx:evt.t2_idx] = evt.data
                c2m1 = np.roll(c2m1, -mwdelay)
                self.logger.warning(
                    'Value error: only MW switch connected is S2 using Ch1, M1, this channel will do nothing')
            elif channel.ch_type == _ADWIN_TRIG:
                for (n, evt) in enumerate(channel.event_train):
                    c2m2[evt.t1_idx:evt.t2_idx] = evt.data

        self.c1markerdata = c1m1 + c1m2
        self.c2markerdata = c2m1 + c2m2
        # the wavedata will store the data for the I and Q channels in a 2D array
        self.wavedata = np.array((waveI, waveQ))


class RandomSequence(Sequence):
    pass


class SequenceList(object):
    def __init__(self, sequence, delay=None, scanparams=None, pulseparams=None, connectiondict=None, timeres=1, **kwargs):
        """This class creates a list of sequence objects that each have the waveforms for one step in the scanlist.
        :param sequence: string that will be interpreted in same manner as Sequence class def
        :param delay: list with [AOM delay, MW delay] , possibly other delays to be added.
        :param pulseparams: a dictionary containing the amplitude, pulsewidth,SB frequency,IQ scale factor,
                        phase, skewphase
        :param connectiondict: a dictionary of the connections between AWG channels and switches/IQ modulators
        :param timeres: clock rate in ns
        :param scanparams : a dictionary that specifies the type, start, stepsize, number of steps
        """
        self.comp_seq_num = kwargs['compseqnum']
        self.pauli_rand_num = kwargs['paulirandnum']
        if delay is None:
            delay = [0.0, 0.0]
        if scanparams is None:
            self.scanparams = {'type': 'amplitude', 'start': 0, 'stepsize': 10, 'steps': 10}
        else:
            self.scanparams = scanparams
        if pulseparams is None:
            self.pulseparams = {'amplitude': 0, 'pulsewidth': 20e-9, 'SB freq': 0.00, 'IQ scale factor': 1.0,
                                'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
        else:
            self.pulseparams = pulseparams
        if connectiondict is None:
            self.connectiondict = _CONN_DICT
        else:
            self.connectiondict = connectiondict
        self.scanlist = np.arange(self.scanparams['start'], self.scanparams['start'] + self.scanparams['stepsize'] *
                                  self.scanparams['steps'], self.scanparams['stepsize'])
        self.delay = delay
        # self.pulseparams = pulseparams
        # self.connectiondict = connectiondict
        self.timeres = timeres
        self.sequence = sequence
        self.sequencelist = []
        self.rbinfo_list = []
        self.rbscanlengths = []

    def create_sequence_list(self):
        # dt = float(self.scanparams['stepsize'])
        temp_pulseparams = self.pulseparams.copy()  # store a temporary copy of the pulseparams variable
        if self.scanparams['type'] == 'no scan':
            # the no scan may be useful for testing sequences
            s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                         connectiondict=self.connectiondict, timeres=self.timeres)
            s.create_sequence(dt=0)
            self.sequencelist.append(s)
        # now we do the random scan
        elif self.scanparams['type'] == 'random scan':
            # rng = np.random.default_rng()
            stop = self.scanparams['start'] + (self.scanparams['steps']-1) * self.scanparams['stepsize']
            # generate a list of random truncation lengths for the scans, the number of lengths given by steps param
            # self.scanlist = rng.integers(self.scanparams['start'],stop,self.scanparams['steps'])
            # modified this as: we first generate a uniform list and then shuffle it for the purpose of interleaving. because the earlier method was repeating length values
            self.scanlist = np.linspace(self.scanparams['start'], stop, self.scanparams['steps'])
            random.shuffle(self.scanlist)
            self.scanlist = self.scanlist.astype(int)
            # for each truncation length, we need N_p pauli randomizations.
            self.scanlist = np.repeat(self.scanlist, self.pauli_rand_num)
            # choose how many pauli gate sequences you will run encoded in the parameter stepsize
            # self.paulinum = self.scanparams['stepsize']
            for x in self.scanlist:
                s = Sequence(self.sequence,delay=self.delay,pulseparams=self.pulseparams,connectiondict=self.connectiondict, timeres=self.timeres)
                s.trunc_lengths = self.scanlist
                # s.paulinum = self.paulinum
                s.rb_nevents = x
                s.comp_seq_num = self.comp_seq_num
                print("scan length is",x)
                s.create_sequence(dt=0.0)
                self.rbinfo_list.append(s.rbinfo_list)
                self.rbscanlengths.append(x)
                self.sequencelist.append(s)
            print(self.rbscanlengths)
        else:
            # all other types of scans
            for x in self.scanlist:
                self.pulseparams = temp_pulseparams.copy()
                if self.scanparams['type'] == 'time':
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(float(x))
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'amplitude':
                    self.pulseparams['amplitude'] = float(x)
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'SB freq':
                    self.pulseparams['SB freq'] = float(x)
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'pulsewidth':
                    self.pulseparams['pulsewidth'] = float(x)
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'number':
                    self.pulseparams['num pulses'] = int(x)
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'Carrier frequency':
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
                elif self.scanparams['type'] == 'phase':
                    self.pulseparams['phase'] = float(x)
                    s = Sequence(self.sequence, delay=self.delay, pulseparams=self.pulseparams,
                                 connectiondict=self.connectiondict, timeres=self.timeres)
                    s.create_sequence(dt=0)
                    self.sequencelist.append(s)
