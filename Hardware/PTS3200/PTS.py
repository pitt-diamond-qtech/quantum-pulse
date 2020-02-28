# Created by Gurudev Dutt <gdutt@pitt.edu> on 1/3/20
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

_ARD_COM_PORT = 'COM13'
_LOWFREQ_LIMIT = 1000000
_HIGHFREQ_LIMIT = 3200000000
_DEFAULT_POWER = 13.01
import visa
import sys
import math


class PTS(object):
    '''
    This is the main module imported to other programs if not using control panel GUI.
    We assume that the sketch running on the arduino connected to PTS is PTS.ino which
    is in the same folder as this python code. It contains 6 main method:
        1, __init__: finds Arduino, gets visa, and gets ready to communicate, 
        2, read: read current command freq from Arduino
        3, write: write command freq to Arduino
        4, set: set amplitude input voltage.
        5, reset: reset amplitude input to default. (default amplitude adjustable on PTS rear panel)
        6, scan: scan frequency from start to stop, with number of steps, and dwell time specified by the caller
        7, cleanup: cleanup
    If not using GUI control panel, just import this class.
    '''

    def __init__(self, PTSport=_ARD_COM_PORT):
        self.rm = visa.ResourceManager()
        self.arduino = self.rm.open_resource(PTSport)
        try:
            self.arduino.read()
        except visa.VisaIOError:
            sys.stderr.write('Error communicating with PTS')

    def read(self):
        try:
            s = self.arduino.query('b').replace('\r\n', '')
        except visa.VisaIOError as error:
            sys.stderr.write('VISA IO Error: {0}'.format(error))
            return None
        return self.decode(s)

    def write(self, freq):
        if (int(freq) < _LOWFREQ_LIMIT or int(freq) > _HIGHFREQ_LIMIT):
            sys.stderr.write('Invalid frequency given')
            return False
        try:
            self.arduino.query('f' + str(freq) + '#')
            return True
        except visa.VisaIOError as error:
            sys.stderr.write('VISA IO Error: {0}'.format(error))
            return False
        except:
            sys.stderr.write("Unexpected error", sys.exc_info()[0])
            return False

    def decode(self, s):
        '''
        This function decodes BCD string into frequency integer.
        Every 4 bits are decoded to 1 decimal digit.
        @param s: str that consists of '0' and '1' only
        @return: int decoded frequency
        '''
        try:
            while s[0] == '0':
                s = s[1:]
        except IndexError:
            return 0  # This happens when s is nothing but a series of '0'
        if len(s) % 4 != 0:
            s = '0' * (4 - len(s) % 4) + s
        ss = []
        while s != '':
            ss.append(s[:4])
            s = s[4:]
        freq = 0
        for each_4_bits in ss:
            freq *= 10
            freq += int(each_4_bits, 2)
        return freq

    def encode(self, freq):
        '''
        This function encodes integer frequency into BCD string.
        Each digit is encoded to 4 bits.
        @param freq: int frequency
        @return: str that consists of '0' and '1' only,length of 38
        '''
        dec_str = str(freq)
        bcd_str = ''
        for each_digit in dec_str:
            s = bin(int(each_digit))[2:]
            if len(s) < 4:
                s = '0' * (4 - len(s)) + s
            bcd_str += s
        l = len(bcd_str)
        if l < 38:
            bcd_str = '0' * (38 - l) + bcd_str
        elif l > 38:
            bcd_str = bcd_str[(l - 38):]
        print(bcd_str)
        return bcd_str

    # need to account for input being in units of Pdbm, not PWM duty cycle, which is input to PTS.ino
    # the first line of the function takes a Pdbm input and converts it to the corresponding PWM duty cycle
    # derivation for the conversion is in my lab notebook
    def set_power(self, amp):
        pwm_duty = (10 ** (amp / 20)) * (256 / math.sqrt(500))
        if (int(pwm_duty) < 0 or int(pwm_duty) > 255):
            sys.stderr.write('Invalid power given')
            return False
        try:
            self.arduino.query('p' + str(pwm_duty) + '#')
            return True
        except visa.VisaIOError as error:
            sys.stderr.write('VISA IO Error: {0}'.format(error))
            return False
        except:
            sys.stderr.write("Unexpected error", sys.exc_info()[0])
            return False

    # need to figure out what default power setting on PTS is so we can set it at top of code
    def reset_power(self, default_power):
        self.set_power(default_power)

    def scan(self, start, stop, numsteps, dwelltime):
        # start by setting max and min inputs for each parameter
        '''
        Neither the start nor stop frequencies can be out of the permitted frequency range,
        I don't think there are any conditions on numsteps other than it can't be less than 1, because this would
        cause a second frequency that's larger than the stop frequency
        '''
        if (int(start) < _LOWFREQ_LIMIT or int(start) > _HIGHFREQ_LIMIT):
            sys.stderr.write('Invalid start frequency given')
            return False
        elif (int(stop) < _LOWFREQ_LIMIT or int(stop) > _HIGHFREQ_LIMIT):
            sys.stderr.write('Invalid stop frequency given')
            return False
        elif (int(numsteps) < 1):
            sys.stderr.write('Invalid step number given')
            return False
        try:
            self.arduino.query('s' + str(start) + '#' + str(stop) + '#' + str(numsteps) + '#' + str(dwelltime) + '#')
            return True
        except visa.VisaIOError as error:
            sys.stderr.write('VISA IO Error: {0}'.format(error))
            return False
        except:
            sys.stderr.write("Unexpected error", sys.exc_info()[0])
            return False

    def cleanup(self):
        self.arduino.write('f0#')
        self.arduino.close()
