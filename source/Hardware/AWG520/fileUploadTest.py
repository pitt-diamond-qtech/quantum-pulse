# This is a script written to test the file upload function to the AWG
# This uploads the files in dirPath to a folder awgPath inside the AWG

import os
from pathlib import Path
from source.Hardware.AWG520 import AWG520
awg=AWG520()

dirPath = Path('D:\PyCharmProjects\quantum-pulse\source\Hardware\AWG520\sequencefiles')
awgPath = Path('./pulsed_esr')

i=1
for filename in os.listdir(dirPath):
    awg.sendfile(awgPath / filename, dirPath / filename)
    print('uploaded {} files'.format(i))
    i+=1

awg.cleanup()