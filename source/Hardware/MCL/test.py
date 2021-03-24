from ctypes import *
import os
import sys
import string
import time


DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__), 'Madlib.dll'))


def __init__(debug=False):
    '''
    Loading the dll.
    The madlib.dll file should be in the same folder as this nanodrive.py file.
    '''
    DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__), 'Madlib.dll'))
    '''
    And set up a universal error handler (UEH).
    Now it's only giving the error details.
    '''
    if debug:
        success = lambda: sys.stdout.write("SUCCESS\n")
    else:
        success = lambda: None
    err1 = lambda: sys.stderr.write(
        "GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.\n")
    err2 = lambda: sys.stderr.write(
        "DEVICE_ERROR: A problem occurred when transferring data to the Nano Drive. It is likely that the Nano Drive will have to be power cycled to correct these errors.\n")
    err3 = lambda: sys.stderr.write(
        "DEVICE_NOT_ATTACHED: The Nano Drive cannot complete the task because it is not attached.\n")
    err4 = lambda: sys.stderr.write(
        "USAGE_ERROR: Using a function from the library which the Nano Drive does not support causes these errors.\n")
    err5 = lambda: sys.stderr.write(
        "DEVICE_NOT_READY: The Nano Drive is currently completing or waiting to complete another task.\n")
    err6 = lambda: sys.stderr.write(
        "ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.\n")
    err7 = lambda: sys.stderr.write(
        "INVALID_AXIS: Attempting an operation on an axis that does not exist in the Nano Drive.\n")
    err8 = lambda: sys.stderr.write(
        "INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.\n")
    UEHdic = {0: success, -1: err1, -2: err2, -3: err3, -4: err4, -5: err5, -6: err6, -7: err7, -8: err8}


def InitHandles():
    '''
    Requested control of all nano stages.
    Return value: a dictionary {"L": handle of LP100 stage, "H": handle of HS3 stage}
    '''
    numDevices = DLL.MCL_GrabAllHandles()
    dic ={}
    dic["L"] = DLL.MCL_GetHandleBySerial(c_short(2849))
    dic["H"] = DLL.MCL_GetHandleBySerial(c_short(2850))
    if numDevices==2:
        return dic
    if dic["L"]==0:
        sys.stderr.write("WARNING: Nano Drive for LP100 is not connected.\n")
    if dic["H"]==0:
        sys.stderr.write("WARNING: Nano Drive for HS3 is not connected.\n")
    return dic





InitHandles()