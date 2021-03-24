'''
Created on May 15, 2014

@author: Kai Zhang
This module contains all Python functions to communicate with Mad City Labs Nano Drive. ISS option has not been programmed yet in this version.
version 1.0.0
'''

from ctypes import *
import os
import sys
#import string
#import time

class MCL_NanoDrive():
    '''
    All functions in Python
    '''
    def __init__(self,debug=False):
        '''
        Loading the dll.
        The madlib.dll file should be in the same folder as this nanodrive.py file. 
        '''
        # added on Nov. 4, 2019 by Gurudev
        try:
            self.DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__),'madlib.dll'))
        except (OSError, WindowsError) as error:
            print("Unable to load Mad city Labs DLL")
            raise

        '''
        And set up a universal error handler (UEH).
        Now it's only giving the error details.
        '''
        if debug:
            success=lambda:sys.stdout.write("SUCCESS\n")
        else:
            success=lambda:None
        err1=lambda:sys.stderr.write("GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.\n")
        err2=lambda:sys.stderr.write("DEVICE_ERROR: A problem occurred when transferring data to the Nano Drive. It is likely that the Nano Drive will have to be power cycled to correct these errors.\n")
        err3=lambda:sys.stderr.write("DEVICE_NOT_ATTACHED: The Nano Drive cannot complete the task because it is not attached.\n")
        err4=lambda:sys.stderr.write("USAGE_ERROR: Using a function from the library which the Nano Drive does not support causes these errors.\n")
        err5=lambda:sys.stderr.write("DEVICE_NOT_READY: The Nano Drive is currently completing or waiting to complete another task.\n")
        err6=lambda:sys.stderr.write("ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.\n")
        err7=lambda:sys.stderr.write("INVALID_AXIS: Attempting an operation on an axis that does not exist in the Nano Drive.\n")
        err8=lambda:sys.stderr.write("INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.\n")
        self.UEHdic = {0:success, -1:err1, -2:err2, -3:err3, -4:err4, -5:err5, -6:err6, -7:err7, -8:err8}
        

    def InitHandles(self):
        '''
        Requested control of all nano stages.
        Return value: a dictionary {"L": handle of LP100 stage, "H": handle of HS3 stage}
        '''
        numDevices = self.DLL.MCL_GrabAllHandles()
        dic ={}
        dic["L"] = self.DLL.MCL_GetHandleBySerial(c_short(2849))
        dic["H"] = self.DLL.MCL_GetHandleBySerial(c_short(2850))
        if numDevices==2:
            return dic
        if dic["L"]==0:
            sys.stderr.write("WARNING: Nano Drive for LP100 is not connected.\n")
        if dic["H"]==0:
            sys.stderr.write("WARNING: Nano Drive for HS3 is not connected.\n")
        return dic

    def DeviceAttached(self,handle):
        '''
        Report whether the handle (integer input) controls the Micro Drive
        Return value: T/F
        '''
        self.DLL.MCL_DeviceAttached.restype = c_bool
        return self.DLL.MCL_DeviceAttached(0,c_int(handle))
    
    def GetCalibration(self,axis,handle):
        '''
        Request the range of motion of specific axis.
        Input Parameter: axis: one of the following: 'X', 'Y', 'Z','AUX'
        Return value: a double value or None for wrong axis name
        Example: xRange=GetCalibration('X',handle)
        '''
        self.DLL.MCL_GetCalibration.restype = c_double
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3),'AUX':lambda:c_uint(4)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid Axis Input!\n'))
        if axisnum():
            rawvalue=self.DLL.MCL_GetCalibration(axisnum(),c_int(handle))
            value=self.UEHdic.get(rawvalue,lambda:rawvalue)()
            return value

        
    def PrintDeviceInfo(self,handle):
        '''
        print the product name, product id, DLL version, firmware version, and other infomation
        Return value: None
        '''
        self.DLL.MCL_PrintDeviceInfo(handle)
        
    def GetProductInfo(self,handle):
        '''
        Provides some useful device information that is otherwise unavailable.
        Return value: a dictionary {'X':T/F, 'Y':T/F, 'Z':T/F, 'AUX':T/F, 'ZEncoder':T/F, 'ADC':bit resolution, 'DAC':bit resolution, 'ProductID':ID, 'FirmwareVersion':version, 'FirmwareProfile':profile}
        '''
        class PRODUCTINFOMATION(Structure):
            _pack_=1
            _fields_ = [('bitmap',c_ubyte),('ADC',c_short,16),('DAC',c_short,16),('id',c_short,16),('fversion',c_short,16),('fprofile',c_short,16)]
        ProductInfo=PRODUCTINFOMATION()
        self.UEHdic.get(self.DLL.MCL_GetProductInfo(byref(ProductInfo),c_int(handle)))()
        dic = {'X':False,'Y':False,'Z':False,'AUX':False,'ZEncoder':False}
        bitmap=ProductInfo.bitmap%32
        if bitmap>=16:
            dic['ZEncoder']=True
            bitmap-=16
        if bitmap>=8:
            dic['AUX']=True
            bitmap-=8
        if bitmap>=4:
            dic['Z']=True
            bitmap-=4
        if bitmap>=2:
            dic['Y']=True
            bitmap-=2
        if bitmap>=1:
            dic['X']=True
        dic['ADC']=ProductInfo.ADC
        dic['DAC']=ProductInfo.DAC
        dicID={0x2001:'Nano-Drive Single Axis',0x2003:'Nano-Drive Three Axis',0x2053:'Nano-Drive 16bit Tip/Tilt Z',0x2004:'Nano-Drive Single Axis',0x2201:'Nano-Drive 20bit Single Axis',0x2203:'Nano-Drive 20bit Three Axis',0x2253:'Nano-Drive 20bit Tip/Tilt Z',0x2100:'Nano-Gauge',0x2401:'C-Focus'}
        dic['ProductID']=dicID.get(ProductInfo.id)
        dic['FirmwareVersion']=ProductInfo.fversion
        dic['FirmwareProfile']=hex(ProductInfo.fprofile)
        return dic
        
    def SingleReadN(self,axis,handle):
        '''
        Reads the current position of the specified axis.
        Input Parameter: axis = 'X','Y','Z' or 'AUX' (although aux is not available for our setup)
        Return value: position value or None for failure.
        '''
        self.DLL.MCL_SingleReadN.restype = c_double
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3),'AUX':lambda:c_uint(4)}
        # got errors saying string.upper no longer valid so modified by Gurudev Nov. 22, 2019
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if axisnum() and self.GetProductInfo(handle).get(axis.upper()):
            rawvalue=self.DLL.MCL_SingleReadN(axisnum(),c_int(handle))
            value=self.UEHdic.get(rawvalue,lambda:rawvalue)()
            return value
        
    def SingleWriteN(self,position,axis,handle):
        '''
        Commands the Nano-Drive to move the specified axis to a position.
        Input Parameter: axis = 'X','Y','Z' or 'AUX' (although aux is not available for our setup)
                         position is double float.
        Return value: None
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3),'AUX':lambda:c_uint(4)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        self.UEHdic.get(self.DLL.MCL_SingleWriteN(c_double(position),axisnum(),handle))()
        
    def MonitorN(self,position,axis,handle):
        '''
        Commands the Nano-Drive to move the specified axis to a position, and then reads the current position of the axis.
        Sometimes the position reading happens before finishing movement and thus be inaccurate.
        Input Parameter: axis = 'X','Y','Z' or 'AUX' (although aux is not available for our setup)
                         position is double float.
        Return value: position value or None for failure.
        '''
        self.DLL.MCL_MonitorN.restype = c_double
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3),'AUX':lambda:c_uint(4)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if axisnum() and self.GetProductInfo(handle).get(axis.upper()):
            rawvalue=self.DLL.MCL_MonitorN(c_double(position),axisnum(),c_int(handle))
            value=self.UEHdic.get(rawvalue,lambda:rawvalue)()
            return value
        
    def ReadWaveFormN(self,axis,DataPoints,handle,rateMode=6):
        '''
        Sets up and triggers a waveform reading on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to read. maximum 6666.
                          rateMode: by default is 6, meaning 2ms/point. More options on documentation.
        Return value: a list of length DataPoints filled with position sensor data.
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        ArrayType = c_double * DataPoints
        waveform = ArrayType()
        self.UEHdic.get(self.DLL.MCL_ReadWaveFormN(axisnum(),c_uint(DataPoints),c_double(rateMode),byref(waveform),c_int(handle)))()
        return list(waveform)
    
    def ReadWaveFormNSetup(self,axis,DataPoints,handle,rateMode=6):
        '''
        Sets up, but doesn't trigger a waveform reading on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to read. maximum 6666.
                          rateMode: by default is 6, meaning 2ms/point. More options on documentation.
        Return value: None
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        self.UEHdic.get(self.DLL.MCL_Setup_ReadWaveFormN(axisnum(),c_uint(DataPoints),c_double(rateMode),c_int(handle)))()
        
    def ReadWaveFormNTrigger(self,axis,DataPoints,handle):
        '''
        Triggers a waveform reading on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to read. maximum 6666.
        Return value: a list of length DataPoints filled with position sensor data.
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        ArrayType = c_double * DataPoints
        waveform = ArrayType()
        self.UEHdic.get(self.DLL.MCL_Trigger_ReadWaveFormN(axisnum(),c_uint(DataPoints),byref(waveform),c_int(handle)))()
        return list(waveform)
    
    def LoadWaveFormN(self,axis,DataPoints,waveformInput,handle,rate=2):
        '''
        Sets up and triggers a waveform loading on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to write. maximum 6666.
                          rate: by default is 2 (ms/point). acceptable range:1/6 to 5 (ms/points).
                          waveformInput: a list of length DataPoints filled with position command data.
        Return value: None
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        if DataPoints!=len(waveformInput):
            sys.stderr.write('ERROR: Length of waveform input list does not match DataPoints input.')
            return None
        ArrayType = c_double * DataPoints
        waveform = ArrayType(*waveformInput)
        self.UEHdic.get(self.DLL.MCL_LoadWaveFormN(axisnum(),c_uint(DataPoints),c_double(rate),byref(waveform),c_int(handle)))()
    
    def LoadWaveFormNSetup(self,axis,DataPoints,waveformInput,handle,rate=2):
        '''
        Sets up, but doesn't trigger a waveform loading on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to write. maximum 6666.
                          rate: by default is 2 (ms/point). acceptable range:1/6 to 5 (ms/points).
                          waveformInput: a list of length DataPoints filled with position command data.
        Return value: None
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        if DataPoints!=len(waveformInput):
            sys.stderr.write('ERROR: Length of waveform input list does not match DataPoints input.')
            return None
        ArrayType = c_double * DataPoints
        waveform = ArrayType(*waveformInput)
        self.UEHdic.get(self.DLL.MCL_Setup_LoadWaveFormN(axisnum(),c_uint(DataPoints),c_double(rate),byref(waveform),c_int(handle)))()
        
    def LoadWaveFormNTrigger(self,axis,DataPoints,handle):
        '''
        Triggers a waveform writing on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
        Return value: None
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        self.UEHdic.get(self.DLL.MCL_Trigger_LoadWaveFormN(axisnum(),c_int(handle)))()

    def WaveFormNTrigger(self,axis,DataPoints,handle):
        '''
        Triggers both waveform reading and writing on the specified axis.
        Input parameters: axis: 'X', 'Y', 'Z'
                          DataPoints: number of data points to read. maximum 6666.
        Return value: a list of length DataPoints filled with position sensor data.
        '''
        dic={'X':lambda:c_uint(1),'Y':lambda:c_uint(2),'Z':lambda:c_uint(3)}
        axisnum = dic.get(axis.upper(),lambda:sys.stderr.write('WARNING: Invalid axis input!\n'))
        if not axisnum():
            return None
        ArrayType = c_double * DataPoints
        waveform = ArrayType()
        self.UEHdic.get(self.DLL.MCL_TriggerWaveformAcquisition(axisnum(),c_uint(DataPoints),byref(waveform),c_int(handle)))()
        return list(waveform)
    
    def MAWaveFormSetup(self,DataPoints,waveformInputX,waveformInputY,waveformInputZ,iterations,handle,rateMode=6):
        '''
        Sets up, but doesn't trigger a waveform loading on all three axis.
        Input parameters: DataPoints: number of data points per axis to read and write. maximum 2222.
                          rateMode: by default is 6 (2ms/point). More options on documentation.
                          waveformInputX(/Y/Z): a list of length DataPoints filled with position command data.
                          iterations: Unsigned int. Number of times to run the waveform. 0 for infinite loops.
        Return value: None
        '''
        if not DataPoints==len(waveformInputX)==len(waveformInputY)==len(waveformInputZ):
            sys.stderr.write('ERROR: Length of waveform input lists do not match DataPoints input.')
            return None
        ArrayType = c_double * DataPoints
        wfx = ArrayType(*waveformInputX)
        wfy = ArrayType(*waveformInputY)
        wfz = ArrayType(*waveformInputZ)
        self.UEHdic.get(self.DLL.MCL_WfmaSetup(byref(wfx),byref(wfy),byref(wfz),c_uint(DataPoints),c_double(rateMode),c_ushort(iterations),c_int(handle)))()
        
    def MAWaveFormTrigger(self,handle):
        '''
        Triggers the waveform writing on all three axis.
        Return value: None
        '''
        self.UEHdic.get(self.DLL.MCL_WfmaTrigger(c_int(handle)))()
        
    def MAWaveFormRead(self,DataPoints,handle):
        '''
        Reads the waveform on all three axis.
        If this function is called while MAWaveForm is writing, it will wait until it stops (or force stop) and then read the sensor data of last run.
        Input parameter: DataPoints: must be the same as Setup function.
        Return value: a 3-element list. Each element itself is a list of sensor data of each axis. [wfx,wfy,wfz]
        '''
        ArrayType = c_double * DataPoints
        wfx = ArrayType()
        wfy = ArrayType()
        wfz = ArrayType()
        self.UEHdic.get(self.DLL.MCL_WfmaTrigger(byref(wfx),byref(wfy),byref(wfz),c_int(handle)))()
        return [list(wfx),list(wfy),list(wfz)]
    
    def MAWaveFormStop(self,handle):
        '''
        Stops a multi-axis waveform writing.
        Return value: None
        '''
        self.UEHdic.get(self.DLL.MCL_WfmaStop(c_int(handle)))()

    def Clock(self,clockname,handle):
        '''
        Generates a 250ns pulse on a correspending clock.
        Input parameter: clockname: string, name of the clock, one of the following: 'Pixel', 'Line', 'Frame', 'Aux'
        Return value: None
        '''
        dic={'Pixel':self.DLL.MCL_PixelClock,'Line':self.DLL.MCL_LineClock,'Frame':self.DLL.MCL_FrameClock,'Aux':self.DLL.MCL_AuxClock}
        self.UEHdic.get(dic.get(clockname)(c_int(handle)))()
    
    def ClockPolarity(self,clockname,polarity,handle):
        '''
        Configures the polarity of the clock pulses.
        Input parameter: clockname: string, name of the clock, one of the following: 'Pixel', 'Line', 'Frame', 'Aux'
                         polarity: 0 or 1. 0 for low to high pulses and 1 for high to low pulses.
        Return value: None
        '''
        dic={'Pixel':1,'Line':2,'Frame':3,'Aux':4}
        self.UEHdic.get(self.DLL.MCL_IssConfigurePolarity(c_int(dic.get(clockname)),c_int(polarity+2),c_int(handle)))()
        
    def SetClock(self,clockname,level,handle):
        '''
        Sets a clock low or high.
        Input parameter: clockname: string, name of the clock, one of the following: 'Pixel', 'Line', 'Frame', 'Aux'
                         level: 0 or 1. 0 for low and 1 for high.
        Return value: None
        '''
        dic={'Pixel':1,'Line':2,'Frame':3,'Aux':4}
        self.UEHdic.get(self.DLL.MCL_IssSetClock(c_int(dic.get(clockname)),c_int(level),c_int(handle)))()
        
    def BindClock(self,clockname,polarity,axis,handle):
        '''
        Binds clock pulses to read action of axis or to waveform read/write action.
        Input parameter: clockname: string, name of the clock, one of the following: 'Pixel', 'Line', 'Frame', 'Aux'
                         polarity: 0 or 1 or 2. 0 for low to high pulses and 1 for high to low pulses. 2 means unbinding.
                         axis: one of the following: 'X', 'Y', 'Z', 'WaveformRead', 'WaveformWrite'
        Return value: None
        '''
        dic={'Pixel':1,'Line':2,'Frame':3,'Aux':4}
        dic2={'X':1, 'Y':2, 'Z':3, 'WaveformRead':5, 'WaveformWrite':6}
        self.UEHdic.get(self.DLL.MCL_IssBindClockToAxis(c_int(dic.get(clockname)),c_int(polarity+2),c_int(dic2.get(axis)),c_int(handle)))()
        
    def ResetClocks(self,handle):
        '''
        Reset Clocks to default settings. Polarity low to high. Pixel clock bound to waveform read and line clock bound to waveform write.
        Return value: None
        '''
        self.UEHdic.get(self.DLL.MCL_IssResetDefaults(c_int(handle)))()
    
    def ReleaseAllHandles(self):
        '''
        Releases control of all Nano Drives controlled by this instance of the DLL.
        Return value: None
        '''
        self.DLL.MCL_ReleaseAllHandles()

if __name__ == '__main__':
    nd=MCL_NanoDrive(True)
    nd.ReleaseAllHandles()
    handleDic = nd.InitHandles()
    #print handleDic
    #print nd.DeviceAttached(handleDic['L'])
    #print nd.GetCalibration('x', handleDic['L'])

    #print nd.MonitorN(0, 'x', handleDic['L'])
    #time.sleep(0.5)
    #print nd.MonitorN(11, 'y', handleDic['L'])
    # I Didn't modify these -- Gurudev nov. 4, 2019
    #print(nd.MonitorN(20, 'z', handleDic['L']))
    print(nd.MonitorN(50, 'x', handleDic['L']))
    #time.sleep(0.5)
    print(nd.MonitorN(50, 'y', handleDic['L']))
    #print nd.MonitorN(55, 'z', handleDic['L'])
    #nd.PrintDeviceInfo(handleDic['H'])
    #print nd.GetProductInfo(handleDic['L'])
    #print nd.SingleReadN('z', handleDic['L'])
    #nd.ReadWaveFormNSetup('x', 1000, handleDic['L'])
    #nd.LoadWaveFormNSetup('x', 201, range(0,100,1)+range(100,-1,-1),handleDic['L'])
    #print nd.WaveFormNTrigger('x', 1000, handleDic['L'])
    #nd.ResetClocks(handleDic['L'])

    #print nd.MonitorN(0, 'x', handleDic['L'])
    
    #nd.SetClock('Aux', 1, handleDic['L'])

    nd.ReleaseAllHandles()

