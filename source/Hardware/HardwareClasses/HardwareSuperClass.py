"""
HardwareSuperClass is a class meant to outline the behavior that will be common to all hardware instruments in DuttLab.

HardwareDevice may be directly inherited in the instrument's class, or HardwareSuperClass may be inherited by an
instrument-type subclass from which the instrument will then be derived.
[ex. WaveformGenerator will inherit from HardwareSuperClass, and AWG520 will inherit from WaveformGenerator]

"""

from abc import ABCMeta, abstractmethod


class HardwareDevice(object):
    """
        HardwareDevice is a superclass that outlines all of the common characteristics and behaviors that each Hardware
        Instrument should implement in the lab

        This superclass enforces that each child-class MUST implement the methods below in their own, appropriate way
        (the wave form generators will implement the startUp method differently than the adwin may.) Otherwise,
        an object of that sub-class cannot be instantiated without throwing an error.
        [This is enforced using the Abstract Base Classes '@abstractmethod']

    """
    __metaclass__ = ABCMeta


    @abstractmethod
    def startUp(self):
        """
            This is an abstractmethod and MUST be implemented by the Child-Class otherwise a
            "TypeError: Can't instantiate abstract class" error will be thrown

            startUp(): startUp executes everything required to get this hardware instrument running, and
            ready to send data, recieve data, or take instructions.
            If this hardware instrument requires nothing to start up (for instance, the instrument is ready to go once
            plugged into an outlet) then pass this function with:

            def startUp(self):
                pass
        """
        pass

    @abstractmethod
    def verify(self):
        """
            This is an abstractmethod and MUST be implemented by the Child-Class otherwise a
            "TypeError: Can't instantiate abstract class" error will be thrown

            verify(): verify is an operation that allows us to check that the hardware instrument is turned on and
            useable. This should be accomplished with a redundant operation that does not alter the state of the
            instrument; it only allows us to determine whether the instrument is on or not.
        """
        pass

    @abstractmethod
    def sendData(self):
        """
            This is an abstractmethod and MUST be implemented by the Child-Class otherwise a
            "TypeError: Can't instantiate abstract class" error will be thrown

            sendData(): sendData allows us to send data to the instrument. Often, this method may require
            multiple arguments to specify other parameters specific to the instrument's operation.
            In the case that the instrument does not accept data from the computer, implement this method with
            a 'pass' body
        """
        pass

    @abstractmethod
    def getData(self):
        """
            This is an abstractmethod and MUST be implemented by the Child-Class otherwise a
            "TypeError: Can't instantiate abstract class" error will be thrown

            getData(): getData pulls data from the instrument. Often, this method may require
            multiple arguments to specify other parameters specific to the instrument's operation.
        """
        pass

    @abstractmethod
    def shutDown(self):
        """
            This is an abstractmethod and MUST be implemented by the Child-Class otherwise a
            "TypeError: Can't instantiate abstract class" error will be thrown

            shutDown(): shutDown executes every operation required to shut-down the device, if that function
            is possible.
            If "shutting down" is not relevant to this instrument, then implement this method with a 'pass' body
        """
        pass
