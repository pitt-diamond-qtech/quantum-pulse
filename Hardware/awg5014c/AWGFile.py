# -*- coding: utf-8 -*-
"""
Created on Sat Nov 12 10:50:21 2016

@author: HatLab_Xi Cao
"""

# AWG file generator 

import struct
import numpy as np
import AWGDefines as Def
from shutil import copyfile
import os


class AWGFile:
    def __init__(self, filename, headerfile = 'newsetting_setup.awg'):
#        headerfile = 'C:\Users\HatLab_Xi Cao\Desktop\\SetupHeader1.awg'
#        headerfile = 'C:\Users\HatLab_Xi Cao\Desktop\\newsetting_setup.awg'
        cwd =  os.getcwd()
        self.filename = filename
#        self.filename = 'C:\Users\HatLab_Xi Cao\Desktop\\Fastcodetest.awg'
        copyfile(cwd + '\\' + headerfile, self.filename)
#        self.file = open(self.filename, 'w')
#        self.file.close()        
    
    def binarymaker(self, name, data):
        self.file = open(self.filename, 'ab')
        Record = struct.pack('<L', len(name)+1)
        Record += struct.pack('<L', len(data))
        Record += struct.pack(str(len(name))+'s', name) + '\x00' + data     
        self.file.write(Record)
        self.file.close()
        
#    def headerfile(self):
#        # Put the system setting into the file.
#        name = 'MAGIC'
#        data = struct.pack('<H', 5000)
#        self.binarymaker(name, data)

    def newwaveform(self, wavenum, wavename, wavelength):
        wavename = struct.pack(str(len(wavename))+'s', wavename) + '\x00'
        wavelength = struct.pack('<L', wavelength)
        wavetype = struct.pack('<H', Def.WaveType_Integer)
        timestamp = '\xe0\x07\x0b\x00\x00\x00\x0d\x00\x0c\x00\x2d\x00\x06\x00\x00\x00'
#        timestamp = '\xe0\x07\x0b\x00\x00\x00\x0d\x00\x0c\x00\x2d\x00\x08\x00\x00\x00'        
        self.binarymaker('WAVEFORM_NAME_'+str(wavenum), wavename)
        self.binarymaker('WAVEFORM_TYPE_'+str(wavenum), wavetype)
        self.binarymaker('WAVEFORM_LENGTH_'+str(wavenum), wavelength)
        self.binarymaker('WAVEFORM_TIMESTAMP_'+str(wavenum), timestamp)
        
    def setwaveform(self, wavenum, wavedata):
        self.binarymaker('WAVEFORM_DATA_'+str(wavenum), wavedata)
        
    def addwaveform(self, elementnum, channelnum, wavename):
        name =  struct.pack(str(len(wavename))+'s', wavename) + '\x00'       
        self.binarymaker('SEQUENCE_WAVEFORM_NAME_CH_'+str(channelnum)+'_'+str(elementnum), name)
        
    def waittrigger(self, elementnum, trigger):
        if trigger == 1:
            state = struct.pack('<H', Def.WaitTrigger_On)
            self.binarymaker('SEQUENCE_WAIT_'+str(elementnum), state)
        else:
            state = struct.pack('<H', Def.WaitTrigger_Off)
            self.binarymaker('SEQUENCE_WAIT_'+str(elementnum), state)
    
    def jump(self, elementnum, jumpindex = 0):
        index = struct.pack('<H', jumpindex)
        self.binarymaker('SEQUENCE_JUMP_'+str(elementnum), index)

    def repeat(self, elementnum, repeatnum):
        num = struct.pack('<L', repeatnum)        
        self.binarymaker('SEQUENCE_LOOP_'+str(elementnum), num)
        
    def goto_state(self, elementnum, gotonum):
        num = struct.pack('<H', gotonum)
        self.binarymaker('SEQUENCE_GOTO_'+str(elementnum), num)
        

if __name__ == '__main__':
    filename = 'C:\Users\HatLab_Xi Cao\Desktop\\XCFastcodetest.awg'
    AWG = AWGFile(filename)
    wavename1 = 'Q_waveform1'
    wavelength = 447
    wavedata = np.zeros(wavelength) + 8192 + 3000
    for x in range(0,wavelength):
        if x == 0:
            wavestr = struct.pack('<H',int(wavedata[x]))
        else:
            wavestr += struct.pack('<H',int(wavedata[x]))
            
    AWG.newwaveform(26, wavename1, wavelength)
    AWG.setwaveform(26, wavestr)
    
    wavename2 = 'I_waveform1'
    wavedata = np.arange(wavelength)*10 + 8192 
#    wavedata[20:80] = 8192 + 10
#    wavedata[100:300] = 8192 + 10
    for x in range(0,wavelength):
        if x == 0:
            wavestr = struct.pack('<H',int(wavedata[x]))
        else:
            wavestr += struct.pack('<H',int(wavedata[x]))
    AWG.newwaveform(27, wavename2, wavelength)
    AWG.setwaveform(27, wavestr)    
    
    AWG.waittrigger(1, 1)
    AWG.repeat(1, 1)
    AWG.jump(1)
    AWG.goto_state(1, 1)
    AWG.addwaveform(1, 1, wavename1)
    AWG.addwaveform(1, 2, wavename2)
    AWG.addwaveform(1, 3, wavename1)
    AWG.addwaveform(1, 4, wavename2)
    
    
    
    
    
    