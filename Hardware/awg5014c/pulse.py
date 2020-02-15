# -*- coding: utf-8 -*-
"""
Created on Fri Nov 18 09:52:31 2016

@author: HatLab_Xi Cao
"""

# Make pulse class for the new AWG code
import numpy as np

class Pulse(object):
    def __init__(self, name, width, ssb_freq, iqscale, phase, skew_phase):
        self.vmax = 1.0         # The max voltage that AWG is using
        self.name = name        # The name of each pulse. It is an integer number, more like a serial number for different type of pulse
        self.width = width      # How long the pulse is going to be. It is an integer number. 
        self.ssb_freq = ssb_freq    # The side band frequency, in order to get rid of the DC leakage from the mixer. It is a floating point number.
        self.iqscale= iqscale       # The voltage scale for different channels (i.e. the for I and Q signals). It is a floating point number.
        self.phase = phase          # The phase difference between I and Q channels.
        self.skew_phase = skew_phase        
        self.Q_data = None          # The I and Q data that will has the correction of IQ scale
        self.I_data = None          # and phase. Both of them will be an array with floating number.
        
    def iq_generator(self, data):   
        # This method is taking "raw pulse data" and then adding the correction of IQ scale and phase to it.
        # The input is an array of floating point number.
        # For example, if you are making a Gaussain pulse, this will be an array with number given by exp(-((x-mu)/2*sigma)**2)
        # It generates self.Q_data and self.I_data which will be used to create waveform data in the .AWG file        
        # For all the pulse that needs I and Q correction, the method needs to be called after doing in the data_generator after 
        # you create the "raw pulse data"
    
    
        # Making I and Q correction
        tempx = np.arange(self.width*1.0)
        self.Q_data = data * np.sin(tempx*self.ssb_freq*2*np.pi + self.phase + self.skew_phase) * self.iqscale  
        self.I_data = data * np.cos(tempx*self.ssb_freq*2*np.pi + self.phase)
        
#        self.Q_data = data * np.cos(tempx*self.ssb_freq*2*np.pi + self.skew_phase) * self.iqscale * np.sin(self.phase)
#        self.I_data = data * np.cos(tempx*self.ssb_freq*2*np.pi) * np.cos(self.phase)        
        
        # Changing the data from noraml voltage values into deck values for futher steps
        self.Q_data = (self.Q_data+self.vmax)*16384.0/(2.0*self.vmax) - 8192
        self.I_data = (self.I_data+self.vmax)*16384.0/(2.0*self.vmax) - 8192
        

class Gaussian(Pulse):
    def __init__(self, name, width, ssb_freq, iqscale, phase, deviation, amp, skew_phase = 0):
        super(Gaussian, self).__init__(name, width, ssb_freq, iqscale, phase, skew_phase) 
        self.mean = self.width/2.0   # The center of the Gaussian pulse
        self.deviation = deviation   
        self.amp = (amp + 8192)*(2*self.vmax/16384.0) - self.vmax    # amp input as a deck value and this line change it to a noraml value
        
    def data_generator(self):
        data = np.arange(self.width*1.0)
        data = self.amp*np.exp(-((data-self.mean)**2)/(2*self.deviation*self.deviation))  # making a Gaussian function
        self.iq_generator(data)
        
class Square(Pulse):
    def __init__(self, name, width, ssb_freq, iqscale, phase, height, skew_phase = 0):
        super(Square, self).__init__(name, width, ssb_freq, iqscale, phase, skew_phase)
        self.height = (height + 8192)*(2*self.vmax/16384.0) - self.vmax  # height input as a deck value and this line change it to a noraml value

    def data_generator(self):
        data = (np.zeros(self.width) + 1.0) * self.height                                # making a Square function
        self.iq_generator(data)
        
class Marker(Pulse):
    def __init__(self, name, width, markernum, marker_on, marker_off):
        super(Marker, self).__init__(name, width, 0, 1, 0, skew_phase = 0)
        self.markernum = markernum      # this number shows which marker we are using, 1 and 2 are for CH1, 3 and 4 are for CH2, and so on
        self.marker_on = marker_on      # at which point you want to turn on the marker (can use this for marker delay)
        self.marker_off = marker_off    # at which point you want to turn off the marker
        
        
    def data_generator(self):
        self.I_data = np.zeros(self.width*1)
        self.Q_data = np.zeros(self.width*1)
        if self.markernum == 1 or self.markernum == 5:
            self.I_data[self.marker_on:self.marker_off] += 16384         # For marker 1 and 5, turning on the 15th bit of the I channel

        elif self.markernum == 2 or self.markernum == 6:
            self.I_data[self.marker_on:self.marker_off] += 32768         # For marker 2 and 6, turning on the 16th bit of the I channel

        elif self.markernum == 3 or self.markernum == 7:
            self.Q_data[self.marker_on:self.marker_off] += 16384         # For marker 3 and 7, turning on the 15th bit of the I channel
            
        elif self.markernum == 4 or self.markernum == 8:
            self.Q_data[self.marker_on:self.marker_off] += 32768         # For marker 4 and 8, turning on the 16th bit of the I channel
            
            
            
            
            
            
            
            
            
            
            
            