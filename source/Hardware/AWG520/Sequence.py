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

from .Pulse import Gaussian, Square, Marker, Sech, Lorentzian, LoadWave
from source.common.utils import log_with, create_logger, get_project_root
import copy

maindir = get_project_root()
seqfiledir = Path('.') / 'sequencefiles/'
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
# dictionary of connections from marker channels to devices,
_CONN_DICT = {_MW_S1: None, _MW_S2: 1, _GREEN_AOM: 2, _ADWIN_TRIG: 4}
# dictionary of IQ parameters that will be used as default if none is supplied
_IQ_PARAMS = {'amplitude': 0.0, 'pulsewidth': 20, 'SB freq': 0.00, 'IQ scale factor': 1.0,
              'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}


def to_int(iterable):
    return [int(x) for x in iterable]


class SequenceEvent:
    """A single sequence event.
    :param event_type: The type of event, e.g. Green, Wave etc
    :param start: The start time of the event.
    :param stop: The stop time of the event.
    :param start_increment: The multiplier for incrementing the start time.
    :param stop_increment: The multiplier for incrementing the stop time.
    :param sampletime: the sampling time (clock rate) used for this event
    """

    def __init__(self, event_type=_GREEN_AOM, start=1.0*_us, stop=1.1 *_us, start_increment=0, stop_increment=0,
                 sampletime=1.0 * _ns):
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


class Channel:
    """Provides functionality for a sequence of :class:`sequence events <SequenceEvent>`.
    :param event_train: A collection of :class:`sequence events <SequenceEvent>`.
    :param delay: Delay in the format [AOM delay, MW delay].
    :param iq_params: A dictionary containing parameters for the IQ modulator: amplitude, pulseWidth,
                        SB frequency, IQ scale factor, phase, skewPhase.
    :param connection_dict: A dictionary of the connections between AWG channels and switches/IQ modulators.
    """

    def __init__(self, event_train: List[SequenceEvent], delay=None, iq_params=None, connection_dict=None):
        if delay is None:
            delay = [0, 0]
        self.logger = logging.getLogger('seqlogger.seq_class')
        self.event_train = event_train
        self.delay = delay

        # init the arrays
        self.wavedata = None
        self.c1markerdata = None
        self.c2markerdata = None

        # set the maximum length to be zero for now
        self.maxend = 0

        if iq_params is None:
            self.iq_params = _IQ_PARAMS
        else:
            self.iq_params = iq_params

        if connection_dict is None:
            self.connection_dict = _CONN_DICT
        else:
            self.connection_dict = connection_dict
        self.num_of_events = len(event_train)
        self.event_channel_index = 0
        self.latest_channel_event = 0
        self.first_channel_event = 0
        if self.num_of_events == 1 or self.num_of_events == 0:
            self.separation = 0.0
        self.event_start_times = []
        for idx, evt in self.event_train:
            self.event_start_times.append(round(evt.start + i * (self.width + self.separation), 10))
        self.pulse_widths = [width] * int(pulses_in_train)

        self.latest_channel_event = np.amax(np.array(self.pulse_on_times)) + width
        self.first_channel_event = np.amin(np.array(self.pulse_on_times))

    # TODO : Possibly make more self-explanatory function names
    def extract_pulse_params_from_dict(self):
        ssb_freq = float(self.iq_params['SB freq']) * _MHz  # SB freq is in units of Mhz
        iqscale = float(self.iq_params['IQ scale factor'])
        phase = float(self.iq_params['phase'])
        deviation = int(self.iq_params['pulsewidth']) // self.timeres
        amp = int(self.iq_params['amplitude'])  # needs to be a number between 0 and 100
        skew_phase = float(self.iq_params['skew phase'])
        npulses = self.iq_params['num pulses']
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
