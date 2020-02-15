# -*- coding: utf-8 -*-
"""
Created on Fri Nov 18 13:58:24 2016

@author: HatLab_Xi Cao
"""

# The new sequence class for the new AWG code

import numpy as np
import struct

MIN_ELEMENT_LENGTH = 250
### Functions that will be used in calculating the sequence element
def make_empty(header):
    length = header[1] - header[0]
    if length == 0:
        return []
    elif np.mod(length, MIN_ELEMENT_LENGTH) == 0:
        return [0, MIN_ELEMENT_LENGTH, 0, int(length)/MIN_ELEMENT_LENGTH]
    elif np.mod(length, MIN_ELEMENT_LENGTH) != 0:
#        return [0, MIN_ELEMENT_LENGTH, 0, (int(length)/MIN_ELEMENT_LENGTH) - 1, 0, np.mod(length, MIN_ELEMENT_LENGTH) + MIN_ELEMENT_LENGTH, 0, 1]
        if int(length)/MIN_ELEMENT_LENGTH == 1:
            return [0, np.mod(length, MIN_ELEMENT_LENGTH) + MIN_ELEMENT_LENGTH, 0, 1]
        else:
            return [0, MIN_ELEMENT_LENGTH, 0, (int(length)/MIN_ELEMENT_LENGTH) - 1, 0, np.mod(length, MIN_ELEMENT_LENGTH) + MIN_ELEMENT_LENGTH, 0, 1]
#        
def nonempty_name(header, block):
    if header == []:
        return []
    length = header[1] - header[0]
    name1 = str(length)
    name2 = str(length)

    i = 0    
    if block[0] == []:
        name1 = name1 + ',-1'
    else:
        while i < len(block[0])-1:
            name1 = name1 + ',' + str(block[0][i]) + ',' + str(block[0][i+1] - header[0])
            i = i +2
    
    i = 0      
    if block[1] == []:
        name2 = name2 + ',-1'
    else:
        while i < len(block[1])-1:
            name2 = name2 + ',' + str(block[1][i]) + ',' + str(block[1][i+1] - header[0])
            i = i+2
        
    
    return [name1, name2]
        
def empty_name(header, block):
    if header == []:
        return []
    length = header[1] - header[0]
    name1 = str(length) + ',-1' 
    name2 = str(length) + ',-1'
    name3 = None
    name4 = None
    if len(header) > 4:
        length = header[5] - header[4]
        name3 = str(length) + ',-1' 
        name4 = str(length) + ',-1'

    result = [name1, name2, name3, name4]  
    return [x for x in result if x is not None]
#    return [name1, name2, name3, name4]

def AWG_upload(header, block, AWG, sequence_index, goto):
    if header == []:
        return sequence_index
    i = 0
    while i < len(header):    
#        print i
#        print sequence_index
#        print header
#        print block
#        AWG.waittrigger(sequence_index, header[i][2])
#        AWG.repeat(sequence_index, header[i][3])
#        AWG.jump(sequence_index)
#        AWG.goto_state(sequence_index, goto)
#        
#        AWG.addwaveform(sequence_index, 1, block[i][2][0]+'_I')
#        AWG.addwaveform(sequence_index, 2, block[i][2][0]+'_Q')
#        AWG.addwaveform(sequence_index, 3, block[i][2][1]+'_I')
#        AWG.addwaveform(sequence_index, 4, block[i][2][1]+'_Q')

        AWG.waittrigger(sequence_index, header[i+2])
        AWG.repeat(sequence_index, header[i+3])
        AWG.jump(sequence_index)
        AWG.goto_state(sequence_index, goto)
        
        AWG.addwaveform(sequence_index, 1, block[2][0+i/2]+'_I')
        AWG.addwaveform(sequence_index, 2, block[2][0+i/2]+'_Q')
        AWG.addwaveform(sequence_index, 3, block[2][1+i/2]+'_I')
        AWG.addwaveform(sequence_index, 4, block[2][1+i/2]+'_Q')        
        i = i + 4
        sequence_index = sequence_index + 1
    
#    print 'Hello'
#    print sequence_index
    return sequence_index

def wavestring(data):
    data += 8192    
    wavestr = struct.pack('<H', int(data[0]))
    i = 1
#    print data
    while i < len(data):
        wavestr += struct.pack('<H', int(data[i]))
        i += 1      
    
    return wavestr

def add_wave_data(I_old, Q_old, I_new, Q_new):
    marker1_I = ( ((I_old + 8192) >= 16384) & ((I_old + 8192) < 32768) ) & ( ((I_new + 8192) >= 16384) & ((I_new + 8192) < 32768) )
    marker1_Q = ( ((Q_old + 8192) >= 16384) & ((Q_old + 8192) < 32768) ) & ( ((Q_new + 8192 )>= 16384) & ((Q_new + 8192) < 32768) )
    
    
    I = I_old + I_new
    Q = Q_old + Q_new
    
    for i in range(len(marker1_I)):
        if marker1_I[i]:
            I[i] = I[i] - 16384
            
    for i in range(len(marker1_Q)):
        if marker1_Q[i]:
            Q[i] = Q[i] - 16384
            
    return (I, Q)

    
def wavedata(name, pulse):
    name = name.split(',')
#    print name
    I_data = np.zeros(int(float(name[0])))
    Q_data = np.zeros(int(float(name[0])))
    i = 1
    while i < len(name)-1:
        pulsename = int(float(name[i]))
        if pulsename >= 0:
            start = int(float(name[i+1]))
            
#            I_data[start:(start+pulse[pulsename].width)] += pulse[pulsename].I_data
#            Q_data[start:(start+pulse[pulsename].width)] += pulse[pulsename].Q_data
        
            (I_data[start:(start+pulse[pulsename].width)], Q_data[start:(start+pulse[pulsename].width)]) = add_wave_data(I_data[start:(start+pulse[pulsename].width)], Q_data[start:(start+pulse[pulsename].width)], pulse[pulsename].I_data, pulse[pulsename].Q_data)

        i = i + 2
    
    I_str = wavestring(I_data)
    Q_str = wavestring(Q_data)
    
    return (I_str, Q_str)
    
    
### Function ends


### Sequence class
class Sequence(object):
    def __init__(self, shotsnum, totwavenum, pulse):
        self.pulse = pulse
        self.raw_sequence = np.empty((totwavenum,5))           # See line 143
        self.sequence_block = [[] for x in xrange(shotsnum-1)] # The length of this sequence_block should be shotsnum - 1
        self.sequence_index = 0                                # A number indicates where we are in the array of raw_sequence
        self.block_count = 0                                   # The number of blocks in this sequence
        self.block_index = 0
        self.name_list = dict()
        
    def get_block(self, pulsename, start, channel, wait_trigger = False):    
        # This method is used to put sequence information into the Sequence class
        # The input is the name of the pulse, when does it starts in the sequence,
        # which channel is it at, does it have a wait trigger or not.
        
        # self.raw_seqeunce is a totwavenum*5 D array. It collects all the pulses
        # in an order that their starts point goes from small to large 
        self.raw_sequence[self.sequence_index, 0:4] = np.array([pulsename, start, start+self.pulse[pulsename].width, channel])
        
        
        if wait_trigger:            # check if this pulse has a wait trigger on it 
            self.raw_sequence[self.sequence_index, 4] = 1       # if so, change the fifth element of this raw_sequence element to 1
            
            if self.block_index == 0:                           # if this is the beginning of the first block, do nothing
                pass
            else:                 # if not, then add all the pulses starts the end of the last block to the one before this one to this sequence_block
                self.sequence_block[self.block_index - 1] = SequenceBlock(self.raw_sequence[self.block_count:self.sequence_index,:])  # we put SequenceBlock object into the sequence_block
                
            self.block_count = self.sequence_index
            self.block_index = self.block_index + 1            
        elif not wait_trigger:
            self.raw_sequence[self.sequence_index, 4] = 0
    
        self.sequence_index = self.sequence_index + 1

    def waveform_name(self, header, block, AWG, wavenum):
        if header == []:
            return ([], wavenum)
        length = header[1] - header[0]        
        i = 0
        while i < len(block[2]):
            if i >= 2:
                length = header[5] - header[4]
                
            if block[2][i] in self.name_list:
                block[2][i] = self.name_list[block[2][i]]
                pass
            else:
                self.name_list.update({block[2][i]: 'WaveForm'+ str(len(self.name_list))})
                (wavestrI, wavestrQ) = wavedata(block[2][i], self.pulse)                  
                AWG.newwaveform(wavenum, self.name_list[block[2][i]]+'_I', length)        
                AWG.setwaveform(wavenum, wavestrI)
                wavenum = wavenum + 1
                AWG.newwaveform(wavenum, self.name_list[block[2][i]]+'_Q', length)        
                AWG.setwaveform(wavenum, wavestrQ)
                wavenum = wavenum + 1
                block[2][i] = self.name_list[block[2][i]]
            i = i +1
        return (block[2], wavenum)
        
    def waveform_data(self, name, block):
        self.waveform_data(block)
        pass
    
    def block_upload(self, block, AWG, sequence_index, goto = 0):
        i = 0
        while i < len(block.header):
            if i != len(block.header) - 1:
                sequence_index = AWG_upload(block.header[i], block.new_block[i], AWG, sequence_index, 0)

            else:
                sequence_index = AWG_upload(block.header[i], block.new_block[i], AWG, sequence_index, goto)
            i = i + 1
        return sequence_index
    
    
    def sequence_upload(self, AWG):
        sequence_index = 1
        j = 0
        wavenum = 26
        while j < len(self.sequence_block):            
            i = 0
            while i < len(self.sequence_block[j].header):
                (self.sequence_block[j].new_block[i][2], wavenum) = self.waveform_name(self.sequence_block[j].header[i], self.sequence_block[j].new_block[i], AWG, wavenum)
                i = i + 1            
            j = j + 1
        
        i = 0
        while i < len(self.sequence_block):
            if i != len(self.sequence_block)-1:
                sequence_index = self.block_upload(self.sequence_block[i], AWG, sequence_index)
            else:
                sequence_index = self.block_upload(self.sequence_block[i], AWG, sequence_index, goto = 1)            
            i = i + 1
    
###############################################################################
### SequenceBlock class      
### This class is to collect all the pulses that are in the same block and 
### sort them out by they channels. Then cut this large block into waveforms
### that may contain several pulses or 0 pulse (empty wavefrom)
    
class SequenceBlock(object):
    def __init__(self, block):      # Put in a 
        self.block = block
    
    def compare_old(self):
        count  = 0 
        compare_index = 0
        self.header = [[] for x in xrange(2*len(self.block))]
        self.header[0] = [[],[],[],[]]
        self.header[0][0] = self.block[compare_index][1]
        
        while compare_index < len(self.block)-1:        
            if self.block[compare_index][2] >= self.block[compare_index+1][2]:
                self.header[count][1] = self.block[compare_index][2]
                
            elif self.block[compare_index][2] > self.block[compare_index+1][1]:              
                self.header[count][1] = self.block[compare_index+1][2]
                
            else:
                self.header[count][1] = self.block[compare_index][2]
                self.header[count][2] = 0
                self.header[count][3] = 1
                count  = count + 1
                compare_index = compare_index + 1
                
                self.header[count] = [[] for x in xrange(4)]
                self.header[count][0] = self.block[compare_index-1][2] + 1
                self.header[count][1] = self.block[compare_index][1] - 1
                self.header[count][2] = 0
                self.header[count][3] = 1
                count  = count + 1
                
                self.header[count] = [[],[],[],[]]
                self.header[count][0] = self.block[compare_index][1]
        
        self.header = filter(None, self.header)
        self.header[-1][1] = self.block[-1][2]
        self.header[count][2] = 0
        self.header[count][3] = 1
        self.header[0][2] = 1  
        
    def compare(self):
        count = 0
        compare_index = 0
        compare_index_temp = 1
        self.header = [[] for x in xrange(2*len(self.block))]
        self.header[0] = [[],[],[],[]]
        self.header[0][0] = self.block[compare_index][1]

        while compare_index < len(self.block) and compare_index_temp < len(self.block):
            if self.block[compare_index][2] >= self.block[compare_index_temp][2]:
                self.header[count][1] = self.block[compare_index][2]
                compare_index_temp += 1
            elif self.block[compare_index][2] > self.block[compare_index_temp][1]:
                self.header[count][1] = self.block[compare_index_temp][2]
                compare_index = compare_index_temp
                compare_index_temp += 1

            else:
                self.header[count][1] = self.block[compare_index][2]
                self.header[count][2] = 0
                self.header[count][3] = 1
                count  = count + 1

                self.header[count] = [[] for x in xrange(4)]
                self.header[count][0] = self.block[compare_index][2] + 1
                self.header[count][1] = self.block[compare_index_temp][1] - 1
                self.header[count][2] = 0
                self.header[count][3] = 1
                count  = count + 1

                compare_index = compare_index_temp                
                compare_index_temp += 1
                self.header[count] = [[],[],[],[]]
                self.header[count][0] = self.block[compare_index][1]                
         

        self.header = filter(None, self.header)
        self.header[count][2] = 0
        self.header[count][3] = 1
        self.header[0][2] = 1          
        

    def make_header(self):
        self.compare()

        i = 0       
        while i < len(self.header) - 2:
            length1 = self.header[i][1] - self.header[i][0]
            length2 = self.header[i+1][1] - self.header[i+1][0]

            if  length1 < MIN_ELEMENT_LENGTH:
                if length2 >= (2*MIN_ELEMENT_LENGTH - length1):
                    self.header[i][1] = self.header[i][0] + MIN_ELEMENT_LENGTH
                    self.header[i+1][0] = self.header[i][1] #+ 1
                    self.header[i+1] = make_empty(self.header[i+1])                   
                elif (length2 + length1) >= MIN_ELEMENT_LENGTH:
                    self.header[i][1] = self.header[i+1][1]
                    self.header[i+1][0] = self.header[i+1][1]
                    self.header[i+1] = make_empty(self.header[i+1])            
                else:
                    self.header[i+2][0] = self.header[i][0]
                    self.header[i+2][2] = self.header[i][2] | self.header[i+2][2]
                    self.header[i] = []
                    self.header[i+1] = []
            else:
                if length2 < MIN_ELEMENT_LENGTH:
                    self.header[i][1] = self.header[i+1][1]
                    self.header[i+1] = []
                else:
                    self.header[i+1] = make_empty(self.header[i+1])
            
            i = i +2
            
        if (self.header[-1][1] - self.header[-1][0]) > MIN_ELEMENT_LENGTH:
#            print 'Hello'
            pass
        else:
            print 'Haha'
#        self.header = [x for x in self.header if x != [] ]
        # TODO: there is another situation when the last element's length is less than
        # MIN_ELEMENT_LENGTH, need to consider this later.
        
    def make_block(self):
        self.make_header()
        self.new_block = [[[], [], []] for x in xrange(len(self.header))]
        
        i = 0
        j = 0
        while i < len(self.header):     
            if self.header[i] == []:
                pass
            else:
                while j < len(self.block):
                    if self.block[j][1] >= self.header[i][0] and self.block[j][2] <= self.header[i][1]:
                        if self.block[j][3] == 1:
                            self.new_block[i][0].append(self.block[j][0])
                            self.new_block[i][0].append(self.block[j][1])
                        else:
                            self.new_block[i][1].append(self.block[j][0])
                            self.new_block[i][1].append(self.block[j][1])
                        
                        j = j + 1
                    else:
                        break
                
            self.new_block[i][2] = nonempty_name(self.header[i], self.new_block[i])
            if i+1 >= len(self.new_block):
                pass
            else:
                self.new_block[i+1][2] = empty_name(self.header[i+1], self.new_block[i+1])                
            i = i + 2
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    

        
