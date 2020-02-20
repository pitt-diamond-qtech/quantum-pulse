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
import visa
import sys


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

    def __init__(self, PTSport = _ARD_COM_PORT):
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
            self.arduino.query('f' + str(freq) +'#')
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

    def set(self,amp):
        if (int(amp) < 0 or int(amp) > 255):
            sys.stderr.write('Invalid power given')
            return False
        try:
            self.arduino.query('p' + str(amp) +'#')
            return True
        except visa.VisaIOError as error:
            sys.stderr.write('VISA IO Error: {0}'.format(error))
            return False
        except:
            sys.stderr.write("Unexpected error", sys.exc_info()[0])
            return False

    def reset(self,amp):
        pass

    def scan(self, start, stop, numsteps, dwelltime):
        pass

    def cleanup(self):
        self.arduino.write('f0#')
        self.arduino.close()
