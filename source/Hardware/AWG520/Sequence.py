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
import os

from .Pulse import Gaussian, Square, Marker, Sech, Lorentzian, LoadWave
from source.common.utils import log_with, create_logger,get_project_root
import copy

maindir = get_project_root()
seqfiledir = Path('.') / 'sequencefiles/'
# logfiledir = maindir / 'logs/'
# print('the sequence file directory is {0} and log file directory is {1}'.format(seqfiledir.resolve(),logfiledir.resolve()))



modlogger = create_logger('seqlogger')





def to_int(iterable):
    return [int(x) for x in iterable]


class Event:
     """A single sequence event.
    :param event_type: The type of event.
    :param start: The start time of the event.
    :param stop: The stop time of the event.
    :param start_increment: The multiplier for incrementing the start time.
    :param stop_increment: The multiplier for incrementing the stop time.
    """
    def __init__(self, event_type, start, stop, start_increment=0, stop_increment=0):
        self.event_type = event_type
        self.start = start
        self.stop = stop
        self.start_increment = start_increment
        self.stop_increment = stop_increment

    def increment_time(self, dt=0):
        """Increments the start and stop times by dt.
        :param dt: The time increment.
        """

        self.start += dt * self.start_increment
        self.stop += dt * self.stop_increment

class Channel:
    """Provides functionality for a sequence of :class:`sequence events <SequenceEvent>`.
    :param seq: A collection of :class:`sequence events <SequenceEvent>`.
    :param delay: Delay in the format [AOM delay, MW delay].
    :param pulse_params: A dictionary containing parameters for the pulse, containing: amplitude, pulseWidth, SB frequency, IQ scale factor, phase, skewPhase.
    :param connection_dict: A dictionary of the connections between AWG channels and switches/IQ modulators.
    :param timeres: The clock rate in ns.
    """

    def __init__(self, seq, delay=[0, 0], pulse_params=None, connection_dict=None, timeres=1):
        self.logger = logging.getLogger('seqlogger.seq_class')
        self.seq = seq
        self.timeres = timeres
        self.delay = delay

        # init the arrays
        self.wavedata = None
        self.c1markerdata = None
        self.c2markerdata = None

        # set the maximum length to be zero for now
        self.maxend = 0

        if pulse_params is None:
            self.pulse_params = self._PULSE_PARAMS
        else:
            self.pulse_params = pulse_params

        if connection_dict is None:
            self.connection_dict = self._CONN_DICT
        else:
            self.connection_dict = connection_dict

    # TODO : Possibly make more self-explanatory function names
    def convert_pulse_params_from_dict(self):
        ssb_freq = float(self.pulseparams['SB freq']) * _GHZ  # SB freq is in units of GHZ
        iqscale = float(self.pulseparams['IQ scale factor'])
        phase = float(self.pulseparams['phase'])
        deviation = int(self.pulseparams['pulsewidth']) // self.timeres
        amp = int(self.pulseparams['amplitude'])  # needs to be a number between 0 and 100
        skew_phase = float(self.pulseparams['skew phase'])
        npulses = self.pulseparams['num pulses']
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


