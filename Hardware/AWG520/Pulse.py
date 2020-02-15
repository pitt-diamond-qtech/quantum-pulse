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


import numpy as np
import sys
import logging

_DAC_BITS = 10   # AWG 520 has only 10 bits
_DAC_UPPER = 1024.0 # DAC has only 1024 levels
_DAC_MID = 512
_IQTYPE = np.dtype('<f4') # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1') # AWG520 stores marker values as 1 byte

pulselogger = logging.getLogger('awg520.pulselogger')

class Pulse(object):
    def __init__(self, num, width, ssb_freq, iqscale, phase, skew_phase):
        self.vmax = 1.0  # The max voltage that AWG is using
        self.num = num  # The name of each pulse. It is an integer number, more like a serial number for different type of pulse
        self.width = width  # How long the entire pulse is going to be. It is an integer number representing samples
        self.ssb_freq = ssb_freq  # The side band frequency, in order to get rid of the DC leakage from the mixer. It is a floating point number.
        self.iqscale = iqscale  # The voltage scale for different channels (i.e. the for I and Q signals). It is a floating point number.
        self.phase = phase  # The phase difference between I and Q channels in degrees
        self.skew_phase = skew_phase # corrections to the phase in degrees
        self.Q_data = None  # The I and Q data that will has the correction of IQ scale
        self.I_data = None  # and phase. Both of them will be an array with floating number.

    def iq_generator(self, data):
        # This method is taking "envelope pulse data" and then adding the correction of IQ scale and phase to it.
        # The input is an array of floating point number.
        # For example, if you are making a Gaussain pulse, this will be an array with number given by exp(-((x-mu)/2*sigma)**2)
        # It generates self.Q_data and self.I_data which will be used to create waveform data in the .AWG file
        # For all the pulse that needs I and Q correction, the method needs to be called after
        # you create the "raw pulse data"

        # Making I and Q correction
        tempx = np.arange(self.width * 1.0)
        self.Q_data = np.array(data * np.sin(2 * np.pi *(tempx * self.ssb_freq  + self.phase/360.0 +
                                                         self.skew_phase/360.0)) * \
                      self.iqscale,dtype = _IQTYPE)
        self.I_data = np.array(data * np.cos(2* np.pi * (tempx * self.ssb_freq + self.phase/360.0)),dtype = _IQTYPE)

class Gaussian(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase,deviation, amp, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0  # The center of the Gaussian pulse
        self.deviation = deviation
        self.amp = amp * self.vmax/_DAC_UPPER # amp can be a value anywhere from 0 - 1000


    def data_generator(self):
        data = np.arange(self.width * 1.0,dtype=_IQTYPE)
        data = np.float32(self.amp * np.exp(
            -((data - self.mean) ** 2) / (2 * self.deviation * self.deviation)))  # making a Gaussian function
        self.iq_generator(data)

class Sech(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, deviation, amp, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0  # The center of the Gaussian pulse
        self.deviation = deviation
        self.amp = amp * self.vmax / _DAC_UPPER # amp can be a value anywhere from 0 - 1000

    def data_generator(self):
        data = np.arange(self.width * 1.0)
        data = np.float32(self.amp * 2.0/(np.exp((data - self.mean)/self.deviation) + np.exp(-(data -
                                                                                       self.mean)/self.deviation)))
                               # making a Sech function
        self.iq_generator(data)

class Lorentzian(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, deviation, amp, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0  # The center of the Gaussian pulse
        self.deviation = deviation
        self.amp = amp * self.vmax / _DAC_UPPER  # amp can be a value anywhere from 0 - 100


    def data_generator(self):
        data = np.arange(self.width * 1.0)
        data = np.float32(self.amp * (self.deviation**2)/(4* (np.power(data - self.mean,2) + (self.deviation/2)**2)))
                               # making a Lorentzian function
        self.iq_generator(data)

class Square(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, height, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0
        self.height = height * self.vmax / _DAC_UPPER  # height can be a value anywhere from 0 - 1000

    def data_generator(self):
        data = (np.zeros(self.width) + 1.0) * self.height  # making a Square function
        self.iq_generator(data)


class Marker(Pulse):
    def __init__(self, num, width, markernum, marker_on, marker_off):
        super().__init__(num, width, 0, 1, 0, skew_phase=0)
        self.markernum = markernum  # this number shows which marker we are using, 1 and 2 are for CH1 m1 and m2,
                                    # 3 and 4 are for CH2 m1 and m2, and so on
        self.marker_on = marker_on  # at which point you want to turn on the marker (can use this for marker delay)
        self.marker_off = marker_off  # at which point you want to turn off the marker
        self.data = np.zeros(self.width * 1, dtype=_MARKTYPE)

    def data_generator(self):
        if self.markernum == 1 or self.markernum == 3:
            # For marker 1 and 3, turning on the 1st bit of the marker byte
            self.data[
            self.marker_on:self.marker_off] += 1
        elif self.markernum == 2 or self.markernum == 4:
            # For marker 2 and 4, turning on the 2nd bit of the marker byte
            self.data[self.marker_on:self.marker_off] += 2

class LoadWave(Pulse):
    def __init__(self,filename,num, width, ssb_freq,iqscale,phase,amp,deviation,skew_phase=0):
        super().__init__(num,width,ssb_freq,iqscale,phase,skew_phase)
        self.amp = amp * self.vmax/ _DAC_UPPER # amp can be a value anywhere from 0 - 1000
        self.deviation = deviation
        self.mean = self.width/2.0
        self.filename = filename # may want to fix this so path is always the same place.

    def data_generator(self):
        try:
            csv = np.genfromtxt(self.filename, delimiter=',')# load a file with amplitude and phase values written by
            # the other module/function
            tt = np.array(csv[:, 1],dtype = _IQTYPE)
            data = np.array(csv[:, 2], dtype = _IQTYPE)
            maxamp = np.amax(data) # find maximum value before resampling
            # now we need to resample the data to be compatible with the width
            resampleidx = np.linspace(tt[0],tt[-1],self.width) # generate a list of integers which goes from
            # tmin to tmax and has width number of samples
            data = np.interp(resampleidx,tt,data) # obtain values of amplitude at resampled values
            data = data * self.amp / maxamp # normalize to maximum value
            self.time = np.interp(resampleidx,tt,tt) # obtain time at resampled values
            self.iq_generator(data)
        except IOError as err:
            #sys.stderr.write('File error: %s', err.message)
            print("OS error: {0}".format(err))
            pulselogger.error("OS error: {0}".format(err))
        except ValueError:
            pulselogger.error('Could not resample supplied waveform data')
        except:
            pulselogger.error('Unknown error')







