'''
Created on May 8, 2014

@author: Kai Zhang

This module contains all Python functions to communicate with Mad City Labs Micro Drive.
version 1.0.0
'''

from ctypes import *
import os
import sys

class MCL_MicroDrive():
    '''
    All functions in Python
    '''
    def __init__(self,debug=False):
        '''
        Loading the dll.
        The microdrive.dll file should be in the same folder as this microdrive.py file. 
        '''
        self.DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__),'microdrive.dll'))
        '''
        And set up a universal error handler.
        Now it's only giving the error details.
        '''
        if debug:
            success=lambda:sys.stdout.write("SUCCESS\n")
        else:
            success=lambda:None
        err1=lambda:sys.stderr.write("GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.\n")
        err2=lambda:sys.stderr.write("DEVICE_ERROR: A problem occurred when transferring data to the Micro Drive. It is likely that the Micro Drive will have to be power cycled to correct these errors.\n")
        err3=lambda:sys.stderr.write("DEVICE_NOT_ATTACHED: The Micro Drive cannot complete the task because it is not attached.\n")
        err4=lambda:sys.stderr.write("USAGE_ERROR: Using a function from the library which the Micro Drive does not support causes these errors.\n")
        err5=lambda:sys.stderr.write("DEVICE_NOT_READY: The Micro Drive is currently completing or waiting to complete another task.\n")
        err6=lambda:sys.stderr.write("ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.\n")
        err7=lambda:sys.stderr.write("INVALID_AXIS: Attempting an operation on an axis that does not exist in the Micro Drive.\n")
        err8=lambda:sys.stderr.write("INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.\n")
        self.UEHdic = {0:success, -1:err1, -2:err2, -3:err3, -4:err4, -5:err5, -6:err6, -7:err7, -8:err8}

    

    def InitHandle(self):
        '''
        Requests control of a single MCL Micro Drive
        Return value: a valid handle (an integer) or 0 for failure
        '''
        return self.DLL.MCL_InitHandle()
    
    def ReleaseAllHandles(self):
        '''
        Release control of all handles
        Return value: None
        We have only one Micro Drive so this is simpler.
        '''
        self.DLL.MCL_ReleaseAllHandles()
        
    def DeviceAttached(self,handle):
        '''
        Report whether the handle (integer input) controls the Micro Drive
        Return value: T/F
        '''
        self.DLL.MCL_DeviceAttached.restype = c_bool
        return self.DLL.MCL_DeviceAttached(0,c_int(handle))
    
    def MicroDriveInformation(self,handle):
        '''
        Get information of the micro drive.
        Return value: a 3-element double list [step size, max velocity, min velocity] 
        We don't have encoder, so encoder resolution is not applicable. Step size is in mm. Max and min velocity is in mm/s.
        '''
        encoderResolution=c_double()
        stepSize=c_double()
        maxVelocity=c_double()
        minVelocity=c_double()
        self.UEHdic.get(self.DLL.MCL_MicroDriveInformation(byref(encoderResolution),byref(stepSize),byref(maxVelocity),byref(minVelocity),c_int(handle)))()
        return [stepSize.value,maxVelocity.value,minVelocity.value]
    
    def MicroDriveMoveStatus(self,handle):
        '''
        Queries the device to see if it is moving.
        Return value: T/F
        '''
        isMoving=c_int(1)  # set default value to be True.
        self.UEHdic.get(self.DLL.MCL_MicroDriveMoveStatus(byref(isMoving),c_int(handle)))()
        return(bool(isMoving))
    
    def MicroDriveWait(self,handle):
        '''
        Waits long enough for the previously commanded move to finish.
        Return value: None
        untested
        '''
        self.UEHdic.get(self.DLL.MCL_MicroDriveWait(c_int(handle)))()
        
    def MicroDriveStatus(self,handle):
        '''
        Reads the limit switches. True for within limit, False for hitting limit.
        Return value: a 3-element T/F list [Success/Failure, Forward limit switch, Reverse limit switch] 
        '''
        status=c_uint()
        self.UEHdic.get(self.DLL.MCL_MicroDriveStatus(byref(status),c_int(handle)))()
        usefulBits=status.value%32
        sf,fl,rl=(False,False,False)
        if usefulBits>=16:
            sf=True
            usefulBits-=16
        if usefulBits>=8:
            fl=True
            usefulBits-=8
        if usefulBits>=4:
            rl=True
        return [sf,fl,rl]
    
    def MicroDriveStop(self,handle):
        '''
        Stops the stage from moving, and reads the limit switches.
        Return value: a 3-element T/F list [Success/Failure, Forward limit switch, Reverse limit switch]
        untested
        '''
        status=c_ubyte()
        self.UEHdic.get(self.DLL.MCL_MicroDriveStop(byref(status),c_int(handle)))()
        usefulBits=status.value%32
        sf,fl,rl=(False,False,False)
        if usefulBits>=16:
            sf=True
            usefulBits-=16
        if usefulBits>=8:
            fl=True
            usefulBits-=8
        if usefulBits>=4:
            rl=True
        return [sf,fl,rl]
    
    def MD1SingleStep(self,directionFlag,handle):
        '''
        Takes a single step in the specified direction.
        Input parameters: directionFlag: T/F, True for forward, False for reverse.
        Return value: None
        '''
        if directionFlag:
            self.UEHdic.get(self.DLL.MCL_MD1SingleStep(c_int(1),c_int(handle)))()
        else:
            self.UEHdic.get(self.DLL.MCL_MD1SingleStep(c_int(-1),c_int(handle)))()
        self.MicroDriveWait(handle)
        
    def MD1MoveSteps(self,velocity,steps,handle):
        '''
        Standard movement function. Acceleration and deceleration ramps are generated  for the specified motion. In some cases when taking smaller steps the velocity parameter may be coerced to its maximum value. The maximum and minimum velocities can be found using MicroDriveInformation.
        Input parameters: velocity: double, speed in mm/sec. 
                          steps: intiger, positive for moving forward, negative for moving reverse.
        Return value: None
        '''
        info = self.MicroDriveInformation(handle)
        if velocity>info[1] or velocity<info[2]:
            sys.stderr.write('WARNING: The input velocity is our of range. There will be an ARGUMENT_ERROR.\n')
        self.UEHdic.get(self.DLL.MCL_MD1MoveProfile_MicroSteps(c_double(velocity),c_int(steps),c_int(handle)))()
        self.MicroDriveWait(handle)
        status=self.MicroDriveStatus(handle)
        if not status[1]:
            sys.stderr.write('WARNING: Hit the reverse limit during movement.\n')
        if not status[2]:
            sys.stderr.write('WARNING: Hit the forward limit during movement.\n')
        
    def CurrentStepPosition(self,handle):
        '''
        Reads the number of microsteps taken since the beginning of the program.
        Return value: integer step position
        '''
        position=c_int()
        if self.MicroDriveMoveStatus(handle):
            self.MicroDriveWait(handle)
        self.UEHdic.get(self.DLL.MCL_MD1CurrentMicroStepPosition(byref(position),c_int(handle)))()
        return position.value
    
    def MD1MoveDistance(self,velocity, distance, handle, rounding=0):
        '''
        Standard movement function. Acceleration and deceleration ramps are generated  for the specified motion. In some cases when taking smaller steps the velocity parameter may be coerced to its maximum value. The maximum and minimum velocities can be found using MicroDriveInformation.
        Input parameters: velocity: double, speed in mm/sec.
                          distance: double, distance of movement. Positive value for forward direction and vice versa. 
                          rounding: int, indicates 3 modes of rounding to steps. 0: nearest microstep. 1: nearest full step. 2:nearest half step.
        Return value: None
        '''
        info = self.MicroDriveInformation(handle)
        if velocity>info[1] or velocity<info[2]:
            sys.stderr.write('WARNING: The input velocity is our of range. There will be an ARGUMENT_ERROR.\n')
        self.UEHdic.get(self.DLL.MCL_MD1MoveProfile(c_double(velocity),c_double(distance),c_int(rounding),c_int(handle)))()
        self.MicroDriveWait(handle)
        status=self.MicroDriveStatus(handle)
        if not status[1]:
            sys.stderr.write('WARNING: Hit the reverse limit during movement.\n')
        if not status[2]:
            sys.stderr.write('WARNING: Hit the forward limit during movement.\n')
        
        
if __name__ == '__main__':
    md=MCL_MicroDrive(True)
    handle = md.InitHandle()
    #print handle
    #print md.DeviceAttached(handle)
    #print md.MicroDriveInformation(handle)
    #print md.MicroDriveMoveStatus(handle)
    #print md.MicroDriveWait(handle)
    #print md.MicroDriveStop(handle)
    #md.MD1SingleStep(True, handle)
    #md.MD1MoveSteps(4, 20000, handle)
    md.MD1MoveDistance(0.1, -0.3, handle)
    #print md.CurrentStepPosition(handle)
    md.ReleaseAllHandles()