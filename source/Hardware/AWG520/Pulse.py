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

# this code borrows heavily from Hatlab group Xi Cao's code

import numpy as np
import sys
import logging
from scipy.interpolate import interp1d


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
        # print(f'ssb freq {self.ssb_freq}, phase {self.phase}, iqscale {self.iqscale},skewphase {self.skew_phase}')
        tempx = np.arange(self.width * 1.0)
        self.Q_data = np.array(data * np.sin(2 * np.pi * (tempx * self.ssb_freq + self.phase/360.0 + self.skew_phase/360.0)) * self.iqscale, dtype=_IQTYPE)
        self.I_data = np.array(data * np.cos(2 * np.pi * (tempx * self.ssb_freq + self.phase/360.0)), dtype=_IQTYPE)

    def i_generator(self,data):
        tempx = np.arange(self.width * 1.0)
        self.Q_data = np.zeros(len(data))
        self.I_data = np.array(data)
        # self.I_data = np.array(data * np.cos(2 * np.pi * (tempx * self.ssb_freq + self.phase/360.0)), dtype=_IQTYPE)

    def q_generator(self,data):
        tempx = np.arange(self.width * 1.0)
        # self.Q_data = np.array(data * np.sin(2 * np.pi * (tempx * self.ssb_freq  + self.phase/360.0 + self.skew_phase/360.0)) * self.iqscale, dtype=_IQTYPE)
        self.Q_data = np.array(data)
        self.I_data = np.zeros(len(data))

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
        # print('mean {0}, deviation {1}, amp {2}, width {3}'.format(self.mean,self.deviation,self.amp,self.width))

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

#Gerono class added on 10/28/2021
class Gerono(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase,deviation, amp,skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.amp = amp * self.vmax/_DAC_UPPER # amp can be a value anywhere from 0 - 1000


    def data_generator(self):

        n_points = 5000
        l_max = 2*np.pi
        l = self.build_l(l_max, n_points)
        phi = np.pi/2
        alpha = self.calculate_alpha(phi)

        x, y = self.gerono_func(alpha, l)  # Require l_max = np.pi

        #Numerically calculate the pulse function.
        pulse_func, t_of_l_list, kappa = self.core_calculation(l, x, y)

        data = np.linspace(min(t_of_l_list), max(t_of_l_list), num=self.width,dtype=_IQTYPE)
        data = self.NormalizeGerono(pulse_func(data))
        data = np.float32(self.amp*data)  # Gerono goes here
        self.iq_generator(data)

    # Gerono parametrization
    def gerono_func(self,alpha, l):
        """Note that this function return x and y of l at the same time.

            Note also that we are using the sympy functions sin, cos and not the numpy np.cos, ..."""
        x = alpha / 2. * np.sin(2 * l)
        y = np.sin(l)
        return x, y

    # Calculating alpha
    def calculate_alpha(self,phi):
        alpha = -1/(np.tan(phi/2))
        return alpha

    def NormalizeGerono(self,data):
        return data/(np.max(abs(data)))

    def num_integrate(self,x, l):
        """Numerical integration."""
        # Dubious integration (sum of the list instead of "smarter" quadrature).
        # Pros, it is fast and the results are good enough.
        dl = l[2] - l[1]
        return np.cumsum(x) * dl


    def link_t_and_l(self,l, integrated_part):
        """Realize the link between lambda (l) and  the time"""
        t_of_l_list = self.num_integrate(integrated_part, l)
        # calculate the function l(t) by cubic interpolation
        return t_of_l_list


    def calculate_derivate(self,x, y, l):
        """Calculate all the derivatives that are required.
            Note that after this process, two points are removed from each list.
            (this is the reason why I've added two points in the build_l function)"""
        dl = l[1] - l[0]
        # Calculate derivations
        x_prime = np.diff(x)  / dl
        y_prime = np.diff(y) / dl
        x_prime2 = np.diff(x_prime) / dl
        y_prime2 = np.diff(y_prime) / dl

        # remove the last points of l and x and x_prime (idem for y) to get every list of same length
        l = l[:-2]
        x = x[:-2]
        y = y[:-2]
        x_prime = x_prime[:-1]
        y_prime = y_prime[:-1]
        return l, x, y, x_prime, y_prime, x_prime2, y_prime2

    def calculate_kappa(self,x_prime, x_prime2, y_prime, y_prime2):
        """Calculate kappa(l) (and not of "t")."""
        return (x_prime * y_prime2 - y_prime * x_prime2) / (x_prime ** 2 + y_prime ** 2) ** (3. / 2)

    def build_l(self,l_max, n_points):
        """Build the lambda function"""
        l = np.linspace(0, l_max, num=n_points)
        dl = l[1] - l[0]
        # Manually add two points that will be removed later, in the dirrentiation process...
        l = np.concatenate((l, [l.max() + dl, l.max() + 2 * dl]))
        return l

    def core_calculation(self,l, x, y):
        """ Generate the interpolated function corresponding to the pulse."""

        # Calculate numerically the derivatives:
        l, x, y, x_prime, y_prime, x_prime2, y_prime2 = self.calculate_derivate(x, y, l)

        # Calculate kappa of l:
        kappa = self.calculate_kappa(x_prime, x_prime2, y_prime, y_prime2)

        # Calculate t of l:
        integrated_part = np.sqrt(x_prime ** 2 + y_prime ** 2)
        t_of_l_list = self.link_t_and_l(l, integrated_part)

        # Interpolate the pulse function
        pulse_func = interp1d(t_of_l_list,kappa,  kind='cubic')
        return pulse_func, t_of_l_list, kappa

class Square(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, height, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0
        self.height = height * self.vmax / _DAC_UPPER  # height can be a value anywhere from 0 - 1000

    def data_generator(self):
        data = (np.zeros(self.width) + 1.0) * self.height  # making a Square function
        self.iq_generator(data)

class SquareI(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, height, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0
        self.height = height * self.vmax / _DAC_UPPER  # height can be a value anywhere from 0 - 1000

    def data_generator(self):
        data = (np.zeros(self.width) + 1.0) * self.height  # making a Square function
        self.i_generator(data)

class SquareQ(Pulse):
    def __init__(self, num, width, ssb_freq, iqscale, phase, height, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.mean = self.width / 2.0
        self.height = height * self.vmax / _DAC_UPPER  # height can be a value anywhere from 0 - 1000

    def data_generator(self):
        data = (np.zeros(self.width) + 1.0) * self.height  # making a Square function
        self.q_generator(data)

class DataIQ(Pulse):
    def __init__(self, filename, num, width, ssb_freq, iqscale, phase, deviation, amp, skew_phase=0):
        super().__init__(num, width, ssb_freq, iqscale, phase, skew_phase)
        self.amp = amp * self.vmax/_DAC_UPPER  # amp can be a value anywhere from 0 - 1000
        self.deviation = deviation
        self.mean = self.width/2.0
        self.filename = filename  # may want to fix this so path is always the same place.

    def data_generator(self):
        try:
            csv = np.genfromtxt(self.filename, delimiter=',')  # load a file with amplitude and phase values written by the other module/function
            tt = np.array(csv[:, 1], dtype=_IQTYPE)
            dataI = np.array(csv[:, 2], dtype=_IQTYPE)
            dataQ = np.array(csv[:, 3], dtype=_IQTYPE)
            maxampI = np.amax(dataI)  # find maximum value before resampling
            maxampQ = np.amax(dataQ)
            # now we need to resample the data to be compatible with the width
            resampleidx = np.linspace(tt[0], tt[-1], self.width) # generate a list of integers which goes from tmin to tmax and has width number of samples
            dataI = np.interp(resampleidx, tt, dataI)  # obtain values of amplitude at resampled values
            dataI = dataI * self.amp / maxampI  # normalize to maximum value
            dataQ = np.interp(resampleidx, tt, dataQ)  # obtain values of amplitude at resampled values
            dataQ = dataQ * self.amp / maxampQ  # normalize to maximum value
            self.time = np.interp(resampleidx, tt, tt)  # obtain time at resampled values

            self.Q_data = np.array(dataQ)
            self.I_data = np.array(dataI)

        except IOError as err:
            print("OS error: {0}".format(err))
            pulselogger.error("OS error: {0}".format(err))
        except ValueError:
            pulselogger.error('Could not resample supplied waveform data')
        except:
            pulselogger.error('Unknown error')


class Marker(Pulse):
    def __init__(self, num, width, markernum, marker_on, marker_off):
        super().__init__(num, width, 0, 1, 0, skew_phase=0)
        self.markernum = markernum  # this number shows which marker we are using, 1 and 2 are for CH1 m1 and m2,
                                    # 3 and 4 are for CH2 m1 and m2, and so on
        self.marker_on = marker_on  # at which point you want to turn on the marker (can use this for marker delay)
        self.marker_off = marker_off  # at which point you want to turn off the marker
        self.data = np.zeros(self.width * 1, dtype=_MARKTYPE)

    def data_generator(self):
        """

        :rtype: object
        """
        if self.markernum == 1 or self.markernum == 3:
            # For marker 1 and 3, turning on the 1st bit of the marker byte
            #self.data[self.marker_on:self.marker_off] += 1
            self.data += 1
        elif self.markernum == 2 or self.markernum == 4:
            # For marker 2 and 4, turning on the 2nd bit of the marker byte
            #self.data[self.marker_on:self.marker_off] += 2
            self.data += 2

class LoadWave(Pulse):
    def __init__(self,filename,num, width, ssb_freq, iqscale, phase, deviation, amp, skew_phase=0):
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







