import HardwareSuperClass

class AgilentUniversalFrequencyCounter(HardwareSuperClass.HardwareDevice):
    """ Agilent Universal Frequency Counter (AUFC) is a hardware instrument used to
        calculate the frequency present in one of the AUFC's inputs.
        This class inherits from the HardwareDevice superclass.

    """
    def __init__(self):
        pass

    def startUp(self):
        print("starting up from child")

    def verify(self):
        print("child verified that instrument is running")

    def sendData(self):
        print("starting up from child")

    def getData(self):
        print("starting up from child")

    def shutDown(self):
        print("starting up from child")



if __name__ == "__main__":
    AUFC=AgilentUniversalFrequencyCounter()
    AUFC.startUp()
    AUFC.shutDown()