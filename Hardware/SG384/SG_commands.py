__author__ = "Vincent Musso"

"""
Dictionary of relevant SRS commands for the console menu.
"""

def sig_synth_commands():
    """
    List of all signal synthesis commands supported by the SRS, plus the IDN query

    """
    dict = {0 : "*IDN?",
            1 : "AMPH",
            2 : "AMPL",
            3 : "AMPR",
            4 : "ENBH",
            5 : "ENBL",
            6 : "ENBR",
            7 : "FREQ",
            8 : "NOIS",
            9 : "OFSD",
            10 : "OFSL",
            11 : "PHAS",
            12 : "RPHS"}
    return dict

def mod_commands():
    """
    List of all signal modulation commands supported by the SRS

    """
    dict = {1 : "ADEP",
            2 : "ANDP",
            3 : "COUP",
            4 : "FDEV",
            5 : "FNDV",
            6 : "MFNC",
            7 : "MODL",
            8 : "PDEV",
            9 : "PDTY",
            10 : "PFNC",
            11 : "PNDV",
            12 : "PPER",
            13 : "PRBS",
            14 : "PWID",
            15 : "QFNC",
            16 : "RATE",
            17 : "RPER",
            18 : "SDEV",
            19 : "SFNC",
            20 : "SRAT",
            21 : "TYPE"}
    return dict