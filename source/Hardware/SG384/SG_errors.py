__author__ = "Vincent Musso"
"""
Dictionary of signal generator errors so that error handling more human readable.
"""

def err_dict():
    dict = { 0 : "No Error",
            10 : "Illegal Value",
            11 : "Illegal Mode",
            12 : "Not allowed",
            13 : "Recall Failed",
            14 : "No Clock Option",
            15 : "No RF Doubler Option",
            16 : "No IQ Option",
            17 : "Failed Self Test",
            30 : "Lost Data",
            32 : "No Listener",
            40 : "Failed ROM Check",
            42 : "Failed EEPROM Check",
            43 : "Failed FPGA Check",
            44 : "Failed SRAM Check",
            45 : "Failed GPIB Check",
            46 : "Failed LF DDS Check",
            47 : "Failed RF DDS Check",
            48 : "Failed 20 MHz PLL",
            49 : "Failed 100 MHz PLL",
            50 : "Failed 19 MHz PLL",
            51 : "Failed 1 GHz PLL",
            52 : "Failed 4 GHz PLL",
            53 : "Failed DAC Test",
            110 : "Illegal Command Syntax",
            111 : "Undefined Command",
            112 : "Illegal Query",
            113 : "Illegal Set",
            114 : "Null Paramter",
            115 : "Too Many Parameters",
            116 : "Missing Parameters",
            117 : "Parameter Buffer Overflow",
            118 : "Invalid Floating Point Number",
            120 : "Invalid Integer",
            121 : "Integer Overflow",
            122 : "Invalid Hexadecimal",
            126 : "Syntax Error",
            127 : "Illegal Units",
            128 : "Missing Units",
            170 : "Communication Error",
            171 : "Remote Input Buffer Overflow",
            254 : "Error Buffer Full"}
    return dict