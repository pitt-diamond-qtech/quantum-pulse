__author__ = "Vincent Musso"
from sys import stdout
import os
import visa
import SG_errors
import SG_commands
import logging

rm = visa.ResourceManager(r"C:\Windows\System32\visa64.dll")
#sg = rm.open_resource('GPIB0::27::INSTR')
# Max input voltage = ~0.5 V
# RF output max for Type-N port is 16 dBm
# Front BNC max output is 13 dBm
"""
Ended up using "logging" instead

class CommandError(Exception):
    def __init__(self, message):
        super(CommandError, self).__init__(message)
"""
class SG_Control():
    err_dict = SG_errors.err_dict()

    """
    Currently only load in one category of commands, sig_synth_commands(), for testing purposes.
    Define a variable for SG_commands.mod_commands() for access to more commands.
    See SG_commands.py for a list of the command codes, and see the SRS manual for the command descriptions.

    """
    commands = SG_commands.sig_synth_commands()
    sg = rm.open_resource('GPIB0::27::INSTR')
    print(sg.query("*IDN?"))

    def __init__(self):
        if(self.ask(self.commands[0]) != "Stanford Research Systems,SG384,s/n003163,ver1.24.26\r\n"):
            raise IOError("SRS RF signal generator not detected")

    def idn(self):
    	"""
		Retrieve device's IDN string

    	"""

        return self.sg.query("*IDN?")

    def ask(self, command):
    	"""
		Used specifically for query commands, i.e. retrieving information from the device.
		Queries user-provided command, to which the device will automatically provide
		a response if no errors occur.

		Keyword arguments:

		command -- command abbreviation, in the form of 4 characters followed by a question mark;
				   some commands have the option of being queried, others are hard-coded queries

		"""

        try:
            answer = self.sg.query(command)
        except visa.VisaIOError:
            error = self.last_err()
            logging.error(" Query error, " + error)
            return
        return answer

    def write(self, command):
    	"""
		Writes the given value as an input for a device command.
		Can be either a command itself, or paramters for a command,
		e.g. a new frequency for the output waveform

		Keyword arguments:

		command -- command abbreviation, in the form of 4 chatacters
				   OR
				   a numerical command parameter; either an integer or floating point value
				   		-floating point values for freq, phase, time, or volts; units must be provided

    	"""

        self.sg.write(command)
        error = self.get_error()

        # Error code 0 (i.e. "False") indicates no error. Non-zero value (i.e. "True") indicates an error
        if(error):
            logging.warning(" Write error, " + self.err_dict[error])

    """
    # For testing purposes
    
    def bad_idn(self):
        try:
            ID = self.sg.query("ID")
        except visa.VisaIOError:
            raise CommandError(self.last_err())
    """
    def get_error(self):
    	"""
    	Queries the device for the most recent error code.

    	"""

        return int(self.sg.query("LERR?").strip('\r\n'))

    def last_err(self):
    	"""
		Retrieves and returns in a readable format the most 
		recent error loaded into the error buffer

    	"""
        code = self.get_error()
        error = self.err_dict[code]
        #print error
        return error

    def empty_err_buffer(self):
    	"""
		Retrieves most recent error loaded into the error buffer until
		the buffer has been emptied of errors.

    	"""

        err = self.get_error()
        err_list = [err]
        while(err != 0):
            err = self.get_error()
            err_list.append(err)

        err_list.remove(0)
        for i in range(len(err_list)):
            print(self.err_dict[err_list[i]])



if __name__ == '__main__':
    srs = SG_Control()

    # Create menu of signal synthesis commands, with the option to set them as queries
    print("Choose an attribute: (Add 'q' to query)\n"
          "1. RF Doubler Amplitude              7. Frequency\n"
          "2. BNC Output Amplitude              8. RF PLL Loop Filter Noise Mode\n"
          "3. Type-N Amplitude                  9. Rear DC Offset\n"
          "4. Enable RF Doubler                 10. BNC Output Offset\n"
          "5. Enable BNC Output                 11. Phase\n"
          "6. Enable Type-N Output              12. Relative Phase\n")

    while(True):
        choice = input()

        # Exit program; otherwise, the menu will keep appearing
        if(choice == 'e' or choice == '0'): # 'e' for 'exit'
            break


        if(choice[-1] == 'q'):
            print(srs.ask(srs.commands[int(choice[:-1])] + '?'))
        else:
        	# If the command is not a query, ask the user for the value of the parameter they wish to set
            param = input("Input parameters: ")
            command = srs.commands[int(choice)] + param
            srs.write(command)
    srs.sg.close()






