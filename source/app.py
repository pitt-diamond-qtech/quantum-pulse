# Created by Gurudev Dutt <gdutt@pitt.edu> on 12/24/19
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from source.Hardware.Threads import UploadThread,ScanThread,KeepThread
from source.common.utils import get_project_root,create_logger,log_with
#from SeqEditor.Wrapper import GUI_Wrapper as SeqEditorWrapper
from source.Hardware.AWG520.Sequence import SequenceList
from source.Hardware.AWG520.AWG520 import AWGFile
from PyQt5 import QtCore, QtWidgets, QtGui,uic
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from pathlib import Path
import sys,numpy,datetime,os
import logging

import numpy as np
import matplotlib.pyplot as plt
from source.Hardware.AWG520.Sequence import Sequence

"""
if I import the Ui_Pulseshaper class from the python file, then I will have to inherit from it in the main appGUI class from appgui, load Ui_Pulseshaper. Instead I use the uic 
module to directly load GUI. Then I dont have to inherit from it and can assign a ui variable inside the appGUI class. Either method is fine.
"""

thisdir = get_project_root()
qtdesignerfile = thisdir/'appgui_V3.ui'  # this is the .ui file created in QtCreator

# start the logger
logger = create_logger('qpulseapp')

Ui_quantumpulse, junk = uic.loadUiType(qtdesignerfile)

@log_with(logger)
class appGUI(QtWidgets.QMainWindow):
    """ this is the main class for the GUI. It has several important variables:
     1. mw : dictionary where each key value has an array contains all the mw parameters such as 'enable device',
     'frequency (GHz)', 'enable scan', 'start', 'step','stop'
     2. scan: array contains all amplitude scan parameters such as start, stop, numsteps
     3. awg:  array contains all awg parameters such as 'awg device', 'amplitude (mV)', 'pulse width', 'time resolution(ns)', 'pulseshape',  'enable IQ','SB freq',
               'IQ scale factor', 'phase', 'skew phase','iterate pulses','num pulses'
     4. ui: the UI instance variable
     5. mplDataPlot: matplotlib data plot
     6.sigPlot, RefPlot: signal, reference Plots
     7. standingby: boolean for standby
     8. dataPlot_renew : boolean for refreshing data plots
     9. maxcounts : keeps track of maximum counts while tracking
     10. parameters: has all the parameters for pulse sequence such as 'sample', 'count time', 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay'
     11. seq: the array which specifies the sequence
    """

    def __init__(self, parent=None,nohardware=False):
        #QtWidgets.QWidget.__init__(self, parent)
        super().__init__(parent)
        # create and setup the UI
        self.ui = Ui_quantumpulse()
        self.ui.setupUi(self)

        # Data matplotlib widget
        fig = Figure()
        self.ui.mplDataPlot = FigureCanvas(fig)
        self.ui.mplDataPlot.setParent(self.ui.dataMPL)
        self.ui.mplDataPlot.axes = fig.add_subplot(111)
        self.ui.mplDataPlot.setGeometry(QtCore.QRect(QtCore.QPoint(0, 0), self.ui.dataMPL.size()))

        # initialize the plots to be empty
        self.sigPlot = None
        self.refPlot = None
        self.dataPlot_renew = False

        # initialize the parameters for scan, MW, AWG, seq
        self.scan = dict([('type', 'amplitude'), ('start', '0'), ('stepsize', '50'), ('steps', '20')])
        self.mw = {'PTS': [True, '2.870', False, '2.840', '0.001', '100', '2.940'], 'SRS': [False, '2.870', False, '2.840', '0.001','100','2.940']}
        # self.mw = {'PTS':[True, '2870.0', False, '2840.0','1','100','2940.0'],'SRS':[False, '2870.0', False, '2840.0','1','100','2940.0']}
        self.awgparams= {'awg device': 'awg520', 'time resolution': 1, 'pulseshape': 'Square', 'enable IQ': False}
        self.pulseparams = {'amplitude': 1000, 'pulsewidth': 20e-9, 'SB freq': 0.00, 'IQ scale factor': 1.0, 'phase': 0.0, 'skew phase': 0.0, 'num pulses': 1}
        self.parameters = [50000, 300, 2000, 10, 10, 715e-9, 10e-9]
        # should make into dictionary with keys ['sample', 'count time', 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay']
        self.timeRes = 1  # default value for AWG time resolution

        self.init_metadata_text_box()
        self.init_seq_text_box()
        self.scan_random = False  # boolean value to check whether this is a randomized benchmarking scan (because the plot is different for RB)
        self.CompSeqNum = int(self.ui.lineEditCompSeqNum.text())
        self.PauliRandNum = int(self.ui.lineEditPauliRandNum.text())
        self.ui.labelCompSeqNum.hide()
        self.ui.labelPauliRandNum.hide()
        self.ui.lineEditCompSeqNum.hide()
        self.ui.lineEditPauliRandNum.hide()
        self.standingby = False

        self.setup_connections() # this sets up all the connections for push buttons and line edits etc
        if nohardware:
            print("NO HARDWARE IN THIS VERSION !")
        else:
            self.hardware_init()


        # self.load_defaults() # loads the main parameters from defaults.txt such as AOM delay, number of samples etc

        self.maxcounts = 0

    def init_seq_text_box(self):
        f = open('./SeqDesigns/default.txt')
        list_of_strings = f.readlines()
        dummy_seq = ''
        for j, t in enumerate(list_of_strings):
            dummy_seq = dummy_seq + t
        print(f"The initial sequence text box is:\n{dummy_seq}")
        self.ui.metadatatextEdit.setText(dummy_seq)
        #self.updateSequenceText()
        f.close()

    def init_metadata_text_box(self):
        f = open('./metadata.txt')
        list_of_strings = f.readlines()
        mdtext = ''
        for num, text in enumerate(list_of_strings):
            mdtext = mdtext + text
        self.ui.textEditMetaData.setText(mdtext)
        f.close()

    def metadata_save_as_default(self):
        f = open('./metadata.txt', 'w')
        text = self.ui.textEditMetaData.toPlainText()
        f.write(text)
        f.close()

    def load_sequence(self):
        try:
            name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence File', './SeqDesigns')
            # print(name[0])
            if name[0] != '':
                file = open(name[0], 'r')
                with file:
                    text = file.read()
                    self.ui.metadatatextEdit.setText(text)
                file.close()
        except Exception as e:
            print(e)

    def save_sequence(self):
        name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Sequence File', './SeqDesigns')
        if name[0] != '':
            file = open(name[0], 'w')
            text = self.ui.metadatatextEdit.toPlainText()
            file.write(text)
            file.close()

    def show_sequence(self):
        try:
            text = self.ui.metadatatextEdit.toPlainText()
            self.convert_text_to_seq(text)
            self.getReady()
            newparams = {'amplitude': 1000, 'pulsewidth': 50e-9, 'SB freq': 0.01, 'IQ scale factor': 1.0, 'phase': 0.0, 'skew phase':0.0, 'num pulses': 1}
            s = Sequence(self.seq, pulseparams=newparams, timeres=1)
            s.create_sequence(dt=500)
            tt = np.linspace(0,s.maxend,len(s.c1markerdata))
            plt.plot(tt, s.wavedata[0, :], 'r-', label='I Channel')
            plt.plot(tt, s.wavedata[1, :], 'b-', label='Q Channel')
            plt.plot(tt, s.c1markerdata, 'g-', label='S2+Green')
            plt.plot(tt, s.c2markerdata, 'y-', label='Measure')
            plt.legend()
            plt.show()
        except Exception as e:
            print(e)


    def setup_connections(self):
        # setup scan buttons and line edits
        # self.ui.checkBoxScanAmplitude.stateChanged.connect(self.enableAmpScan) # removed this chekbox on 2/6/20
        #self.ui.scantypecomboBox.currentIndexChanged.connect(self.updateScanType)
        self.ui.scantypecomboBox.setCurrentIndex(0)
        self.choosescanValidator()
        #self.ui.scantypecomboBox.activated.connect(self.choosescanValidator)
        self.ui.scantypecomboBox.activated.connect(self.updateScanType)

        # setup default text and also the slots for changes in the scan line edits
        self.ui.lineEditScanStart.setPlaceholderText('0')
        self.ui.lineEditScanStep.setPlaceholderText('0')
        self.ui.lineEditScanStop.setPlaceholderText('0')
        self.ui.lineEditScanNum.setPlaceholderText('0')
        self.ui.lineEditAvgNum.setPlaceholderText('1')

        self.ui.lineEditScanStart.editingFinished.connect(self.updateScanNum)
        self.ui.lineEditScanStep.editingFinished.connect(self.updateScanNum)
        self.ui.lineEditScanStop.editingFinished.connect(self.updateScanNum)
        self.ui.lineEditScanNum.editingFinished.connect(self.updateScanStop)
        self.ui.lineEditCompSeqNum.editingFinished.connect(self.updateCompSeqNum)
        self.ui.lineEditPauliRandNum.editingFinished.connect(self.updatePauliRandNum)

        # setup default text and slots for changing the sequence samples, count time, and reset time parameters
        self.ui.lineEditSamples.setPlaceholderText('50000')
        self.ui.lineEditCountTime.setPlaceholderText('300')
        self.ui.lineEditResetTime.setPlaceholderText('2000')

        self.ui.lineEditSamples.setValidator(QtGui.QIntValidator(1, 1000000))
        self.ui.lineEditCountTime.setValidator(QtGui.QIntValidator(1,100000))
        self.ui.lineEditResetTime.setValidator(QtGui.QIntValidator(1,100000))

        self.ui.lineEditSamples.editingFinished.connect(self.updateSamples)
        self.ui.lineEditCountTime.editingFinished.connect(self.updateCountTime)
        self.ui.lineEditResetTime.editingFinished.connect(self.updateResetTime)

        # PTS controls
        self.ui.checkBoxUsePTS.stateChanged.connect(self.enablePTS)
        self.ui.checkBoxTrackMW.stateChanged.connect(self.trackMW)
        # setup the line edit only to accept frequencies in allowed PTS range
        self.ui.lineEditPTSFreq.setValidator(QtGui.QDoubleValidator(10.0,3200.0,3))
        self.ui.lineEditPTSFreq.editingFinished.connect(self.updatePTSFreq)
        # removed these next 4 controls in GUI on 2/6/20
        # self.ui.checkBoxScanPTS.stateChanged.connect(self.enablePTSScan)
        # self.ui.lineEditPTSScanStart.editingFinished.connect(self.updatePTSScanStop)
        # self.ui.lineEditPTSScanStep.editingFinished.connect(self.updatePTSScanStop)
        # AWG controls
        self.set_awgvalidator()
        self.ui.comboBoxTimeRes.currentIndexChanged.connect(self.timeResChanged)
        self.ui.awgSelectcomboBox.currentIndexChanged.connect(self.awgSelect)
        self.ui.voltageSlider.valueChanged[int].connect(self.updateAmplitude)
        self.ui.lineEditPulsewidth.editingFinished.connect(self.updatePulsewidth)
        self.ui.pulseshapecomboBox.currentIndexChanged.connect(self.awgPulseshape)
        self.ui.checkBoxIQmod.stateChanged.connect(self.enableIQ)
        self.ui.lineEditSBfreq.editingFinished.connect(self.updateSBfreq)
        self.ui.lineEditIQscale.editingFinished.connect(self.updateIQscale)
        self.ui.lineEditPhase.editingFinished.connect(self.updatePhase)
        self.ui.lineEditSkewPhase.editingFinished.connect(self.updateSkewPhase)
        #self.ui.checkBoxIteratePulses.stateChanged.connect(self.enableIterPulses) #removed this chekbox on 2/6/20
        #self.ui.lineEditNumPulses.stateChanged.connect(self.updatePulsenum) #removed this  on 2/6/20
        self.ui.lineEditPulsewidth.setText('20e-9')
        # Misc line edits and buttons
        #self.ui.metadatatextEdit.editingFinished.connect(self.updateSequenceText)
        self.ui.lineEditThreshold.setValidator(QtGui.QIntValidator(1,1000000))
        self.ui.lineEditAvgNum.setValidator(QtGui.QIntValidator(1, 10000))
        self.ui.pushButtonUpload.clicked.connect(self.upload)
        self.ui.lineEditThreshold.editingFinished.connect(self.updateThreshold)
        self.ui.lineEditAvgNum.editingFinished.connect(self.updateAvg)
        self.ui.pushButtonReady.clicked.connect(self.updateSequenceText)
        self.ui.pushButtonStart.clicked.connect(self.start)
        self.ui.pushButtonSaveData.clicked.connect(self.saveData)
        self.ui.pushButtonStop.clicked.connect(self.stop)

        # added by Pubudu for the appGUI v3
        self.ui.pushButtonMetaDatasad.clicked.connect(self.metadata_save_as_default)
        self.ui.pushButtonloadSeq.clicked.connect(self.load_sequence)
        self.ui.pushButtonsaveSeq.clicked.connect(self.save_sequence)
        self.ui.pushButtonshowSeq.clicked.connect(self.show_sequence)

    # this section updates all the line edits related to samples, count time and reset time
    def updateSamples(self):
        self.parameters[0] = int(self.ui.lineEditSamples.text())

    def updateCountTime(self):
        self.parameters[1] = int(self.ui.lineEditCountTime.text())

    def updateResetTime(self):
        self.parameters[2] = int(self.ui.lineEditResetTime.text())

    # this section updates all AWG related parameters from the GUI
    def set_awgvalidator(self):
        self.ui.lineEditSBfreq.setValidator(QtGui.QDoubleValidator(-100.0,100.0,9)) # freq in MHz allowed
        self.ui.lineEditPhase.setValidator(QtGui.QDoubleValidator(-179.99,180.0,3)) # phase in degrees allowed
        self.ui.lineEditSkewPhase.setValidator(QtGui.QDoubleValidator(-179.99,180.0,3)) # skew phase in adegrees
        self.ui.lineEditIQscale.setValidator(QtGui.QDoubleValidator(0.0,1.0,3)) # IQ ratio allowed
        # self.ui.lineEditPulsewidth.setValidator(QtGui.QIntValidator(5,1000)) # pulseweidth in ns allowed
        self.ui.lineEditPulsewidth.setValidator(QtGui.QDoubleValidator(5e-9,1e-6,2)) # pulseweidth in ns allowed

    def awgSelect(self):
        device = int(self.ui.awgSelectcomboBox.currentIndex())
        try:
            if device == 0:
                self.awgparams['awg device'] = 'awg520'
            elif device == 1:
                self.awgparams['awg device'] = 'awg5014c'
            else:
                raise ValueError
        except ValueError:
            sys.stderr.write('Select a valid AWG device')

    def awgPulseshape(self):
        pulseshapes = {0: 'Square', 1: "Gaussian", 2: "Sech", 3: 'Load Wfm'}
        self.awgparams['pulseshape'] = pulseshapes[self.ui.pulseshapecomboBox.currentIndex()]

    # def enableIterPulses(self, checkstate):
    #     if checkstate:
    #         self.awgparams['iterate pulses'] = True
    #     else:
    #         self.awgparams['iterate pulses'] = False
    #
    # def updatePulsenum(self):
    #     self.awgparams['num pulses'] = int(self.ui.lineEditNumPulses.currentText())

    def enableIQ(self, checkstate):
        if checkstate:
            self.awgparams['enable IQ'] = True
        else:
            self.awgparams['enable IQ'] = False

    def timeResChanged(self):
        self.timeRes = int(self.ui.comboBoxTimeRes.currentText())
        self.uThread.timeRes = int(self.ui.comboBoxTimeRes.currentText())
        self.awgparams['time resolution']= int(self.ui.comboBoxTimeRes.currentText())

    # end AWG section
    # begin pulseshape dictionary update functions
    def updateAmplitude(self,value):
        # print(value)
        #amp = self.ui.voltageSlider.tickPosition()
        self.pulseparams['amplitude'] = value

    def updatePulsewidth(self):
        self.pulseparams['pulsewidth'] = float(self.ui.lineEditPulsewidth.text())

    def updateSBfreq(self):
        self.pulseparams['SB freq'] = float(self.ui.lineEditSBfreq.text())

    def updateIQscale(self):
        self.pulseparams['IQ scale factor']= int(self.ui.lineEditIQscale.text())

    def updatePhase(self):
        self.pulseparams['phase'] = float(self.ui.lineEditPhase.text())

    def updateSkewPhase(self):
        self.pulseparams['skew phase'] = float(self.ui.lineEditSkewPhase.text())

    # end section updating pulse parameters

    def hardware_init(self):
        '''This function creates all the threads needed to carry out I/O with hardware. '''
        self.uThread = UploadThread()
        self.uThread.done.connect(self.uploadDone) # when the done signal is emitted we handle it using uploadDone
        self.uThread.rbinfo.connect(self.updateRBinfo) # updates the RB fields in the app (final states, seqs and scan lengths) once it's being received by the seqlist class
        self.sThread = ScanThread()
        self.sThread.data.connect(self.dataBack) # when data signal is emitted we handle using dataBack
        # self.sThread.tracking.connect(self.trackingBack) # when tracking signal is emitted we handle using trackingback
        self.kThread = KeepThread()
        self.kThread.status.connect(self.keepStatus) # when status signal is emitted we handle using keepstatus

    def save_defaults(self):
        ''' Saves the parameters to the defaults.txt file '''
        f = open('defaults.txt', 'w')
        f.write('parameters\n')
        para = ['sample', 'count time', 'reset time', 'avg', 'threshold', 'AOM delay', 'microwave delay']
        for i in range(7):
            f.write(para[i] + '=' + str(self.parameters[i]) + '\n')
        f.write('scan parameters\n')
        scan = ['start', 'step', 'num of steps']
        for i in range(len(scan)):
            f.write(scan[i] + '=' + str(self.scan[i]) + '\n')
        # f.write('mw PTS\n')
        mw = ['use this or not', 'frequency (GHz)', 'scan freq or not', 'start', 'step']
        f.write('MW PTS\n')
        for i in range(len(mw)):
            f.write(mw[i] + '=' + str(self.mw['PTS'][i]) + '\n')
        #awg = ['device','amplitude (mV)', 'pulse width','time resolution(ns)','pulseshape','SB freq',
         #     'IQ scale factor', 'phase', 'skew phase','num pulses']
        f.write('MW SRS\n')
        for i in range(len(mw)):
            f.write(mw[i] + '=' + str(self.mw['SRS'][i]) +'\n')
        f.write('AWG \n')
        for key in self.awgparams:
            f.write(str(key) + '=' + str(self.awgparams[key]) + '\n')
        f.close()

    def load_defaults(self, fname='defaults.txt'):
        ''' Loads the parameters from the defaults.txt file'''
        f = open(fname, 'r')

        # para=[sample, count time, reset time, avg, threshold, AOM delay, microwave delay]
        self.parameters = []
        for i in range(7):
            line = f.readline()
            while '=' not in line:
                line = f.readline()
            self.parameters.append(int(line.split('=')[1]))

        # scan=[start,step,num of steps]
        self.scan = []
        for i in range(3):
            line = f.readline()
            while '=' not in line:
                line = f.readline()
            self.scan.append(int(line.split('=')[1]))

        self.ui.lineEditThreshold.setText(str(self.parameters[4]))
        self.ui.lineEditAvgNum.setText(str(self.parameters[3]))
        self.ui.lineEditScanStart.setText(str(self.scan['start']))
        self.ui.lineEditScanStep.setText(str(self.scan['stepsize']))
        self.ui.lineEditScanNum.setText(str(self.scan['steps']))
        self.updateScanStop()

        # microwave parameters: [use this or not, frequency (GHz), scan freq or not, start, step]
        # num of steps uses self.scan[2]
        # AWG para: [device, amplitude, pulsewidth, time resolution, pulseshape]
        # microwave amplifier parameters: power level
        self.mw = {'PTS':[],'SRS':[]}
        for i in range(5):
            line = f.readline()
            while '=' not in line:
                line = f.readline()
            try:
                self.mw['PTS'].append(float(line.split('=')[1]))
            except ValueError:
                self.mw['PTS'].append(line.split('=')[1] == 'True')
        for i in range(5):
            line = f.readline()
            while '=' not in line:
                line = f.readline()
            try:
                self.mw['SRS'].append(float(line.split('=')[1]))
            except ValueError:
                self.mw['SRS'].append(line.split('=')[1] == 'True')
        for i in range(11):
            line = f.readline()
            while '=' not in line:
                line = f.readline()
            try:
                key = line.split('=')[0]
                val = line.split('=')[1]
                self.awgparams[key] = val
            except ValueError:
                self.mw['AWG'].append(line.split('=')[1] == 'True')
        print(self.mw)
        print(self.awgparams)

        self.ui.lineEditPTSFreq.setText(str(self.mw['PTS'][1]))
        #self.ui.lineEditPTSScanStart.setText(str(self.mw['PTS'][3]))
        #self.ui.lineEditPTSScanStep.setText(str(self.mw['PTS'][4]))
        self.updatePTSScanStop()

        f.close()

    # update all the scan type values from the GUI
    # 2/7/20 : enable Amp scan no longer needed with new GUI
    # def enableAmpScan(self,checkstate):
    #     if checkstate:
    #         self.scan['type'] = 'amplitude'
    #         self.updateScanStop()
    #     else:
    #         pass

    def updateScanType(self):
        selection = self.ui.scantypecomboBox.currentIndex()
        scantypes = {0:'amplitude', 1:'time', 2: 'number', 3:'Carrier frequency', 4:'SB freq', 5:'pulsewidth', 6:'phase', 7:'random scan', -1:'no scan'}
        self.scan['type'] = scantypes.get(selection)
        # testing whether the scan is a Randomized Benchmarking scan
        if self.scan['type'] == scantypes[7]:
            self.scan_random = True  # Sets the scan_random variable to True if the user selects 'random scan'
            self.ui.labelCompSeqNum.show()
            self.ui.labelPauliRandNum.show()
            self.ui.lineEditCompSeqNum.show()
            self.ui.lineEditPauliRandNum.show()
            self.ui.label_8.setText('# of Lengths (Nl)')
            self.ui.label_10.setText('# of Runs (Ne)')
        else:
            self.scan_random = False
            self.ui.labelCompSeqNum.hide()
            self.ui.labelPauliRandNum.hide()
            self.ui.lineEditCompSeqNum.hide()
            self.ui.lineEditPauliRandNum.hide()
            self.ui.label_8.setText('# of Steps')
            self.ui.label_10.setText('# of Averages')
        self.choosescanValidator()

    def updateAvg(self):
        self.parameters[3] = int(self.ui.lineEditAvgNum.text())

    def choosescanValidator(self):
        selector = self.ui.scantypecomboBox.currentIndex()
        if selector == 0: # amplitude scan
            regexp = QtCore.QRegExp("[0-9]{1,4}") # prevents negative numbers, and number can at most have 4 digits
        elif selector == 1: # time scan
            #regexp = QtCore.QRegExp("\d{1,6}") # match any sets of digits [0-9] upto 6 allowed i.e. ms long times
            regexp = QtCore.QRegExp("\\d{1,6}(\\.)?\\d{,6}(e|E)?([+-])?\\d")  # match any number of type N.N, N.NE-N, N.Ne-N, N.NeN,etc
        elif selector == 2: # number scan
            regexp = QtCore.QRegExp("[0-9]{,3}") # can at most have 3 digits
        elif selector == 3: # MW frequency
            regexp = QtCore.QRegExp("[0-9]{1,4}\\.[0-9]{1,3}") # frequency in MHz, don't allow frequencies below 1
        elif selector == 4: # sideband frequency
            regexp = QtCore.QRegExp("[0-9]{,3}\\.[0-9]{1,3}") # we don't allow for scans larger than 100 MHz
        elif selector == 5: # pulsewidth
            regexp = QtCore.QRegExp("\\d{1,6}(\\.)?\\d{,6}(e|E)?([+-])?\\d")  # we don't allow for pulsewidths larger than 1000 ns for now
        elif selector == 6: # phase scan
            regexp = QtCore.QRegExp("(?:36[0]|3[0-5][0-9]|[12][0-9][0-9]|[1-9]?[0-9])?$")  # we don't allow for pulsewidths larger than 1000 ns for now
        elif selector == 7: # random scan
            regexp = QtCore.QRegExp("[0-9]{,3}") # can at most have 3 digits
        else:
            regexp = QtCore.QRegExp("[0-9]*")
        validator = QtGui.QRegExpValidator(regexp)
        self.ui.lineEditScanStart.setValidator(validator)
        self.ui.lineEditScanStep.setValidator(validator)
        self.ui.lineEditScanNum.setValidator(QtGui.QIntValidator(1,1000)) # we allow for at most 1000 steps at the
        # moment
        self.ui.lineEditAvgNum.setValidator(QtGui.QIntValidator(1,1000)) # same with number of averages
        self.ui.lineEditScanStop.setValidator(validator)

    # def choosescanValidator(self):
    #     selector = self.ui.scantypecomboBox.currentIndex()
    #     if selector == 0:  # amplitude scan
    #         validator = QtGui.QDoubleValidator(0.0, 1.0e3, 2)
    #         # validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
    #     elif selector == 1:  # time scan
    #         validator = QtGui.QDoubleValidator(0, 2.0e-3, 2)
    #     elif selector == 2:  # number scan
    #         validator = QtGui.QIntValidator(0, 1000)
    #     elif selector == 3:  # MW frequency
    #         validator = QtGui.QDoubleValidator(1.0, 3200.0, 3)
    #     elif selector == 4:  # sideband frequency
    #         validator = QtGui.QDoubleValidator(0, 100.0, 3)
    #     elif selector == 5:  # pulsewidth
    #         validator = QtGui.QDoubleValidator(0, 1.0e-6, 2)
    #
    #     self.ui.lineEditScanStart.setValidator(validator)
    #     self.ui.lineEditScanStep.setValidator(validator)
    #     self.ui.lineEditScanStop.setValidator(validator)
    #     self.ui.lineEditScanNum.setValidator(QtGui.QIntValidator(1, 1000))  # we allow for at most 1000 steps at the moment
    #     self.ui.lineEditAvgNum.setValidator(QtGui.QIntValidator(1, 1000))  # same with number of averages

    def updateRBinfo(self, final_states, final_seqs, x_arr):
        # this function is used to capture information about the scan when the scan is randomized benchmarking
        self.rb_x_arr = x_arr  # sent for plotting
        sort_index = np.argsort(np.array(x_arr))  # returns the indices that sorts the x_arr
        final_states_sorted = [final_states[i] for i in sort_index]
        final_seqs_sorted = [final_seqs[i] for i in sort_index]
        self.ui.rbStatestext.setText(' '.join(final_states_sorted))
        temp = [' '.join(seqs) for seqs in final_seqs_sorted]
        self.ui.rbSeqstext.setText('\n\n'.join(temp))


    def updateScanStop(self):
        ''' This function will set up the amplitude scan when start, step, and numsteps are specified,
        and stop is calculated by the function'''
        #self.scanValidator()
        start = float(self.ui.lineEditScanStart.text())
        step = float(self.ui.lineEditScanStep.text())
        num = float(self.ui.lineEditScanNum.text())
        stop = start + step * num
        self.scan['start'] = start
        self.scan['stepsize'] = step
        self.scan['steps'] = num
        self.ui.lineEditScanStop.setText(str(stop))

    def updateScanNum(self):
        '''this function also updates the amplitude scan but when start, step, and stop are specified, so numsteps
        is calculated by the function'''
        #self.scanValidator()

        start = float(self.ui.lineEditScanStart.text())
        step = float(self.ui.lineEditScanStep.text())
        stop = float(self.ui.lineEditScanStop.text())
        num = int((stop - start) / step)
        self.scan['start'] = start
        self.scan['stepsize']  = step
        self.scan['steps']  = num
        self.ui.lineEditScanNum.setText(str(num))
    # end amplitude scan updates
    # begin PTS scan updates

    def updateCompSeqNum(self):
        '''this function updates the Comp Seq Number'''
        self.CompSeqNum = int(self.ui.lineEditCompSeqNum.text())

    def updatePauliRandNum(self):
        '''this function updates the Pauli Randomization Number'''
        self.PauliRandNum = int(self.ui.lineEditPauliRandNum.text())

    def enablePTS(self, checkState):
        if checkState:
            #self.ui.checkBoxScanPTS.setEnabled(True)
            # if not self.ui.checkBoxScanPTS.isChecked():
            self.ui.lineEditPTSFreq.setEnabled(True)
            self.mw['PTS'][0] = True
        else:
            #self.ui.checkBoxScanPTS.setEnabled(False)
            self.ui.lineEditPTSFreq.setEnabled(False)
            self.mw['PTS'][0] = False

    def trackMW(self, checkState):
        if checkState:
            self.ui.lineEditTrackMWFreq.setEnabled(True)

        else:
            self.ui.lineEditTrackMWFreq.setEnabled(False)


    def updatePTSFreq(self):
        self.mw['PTS'][1] = float(self.ui.lineEditPTSFreq.text())

    def updatetrackMWFreq(self):
        pass

    # disabled these functions on 2/7/20 as no longer needed
    # def enablePTSScan(self, checkState):
    #     if checkState:
    #         self.ui.lineEditPTSScanStart.setEnabled(True)
    #         self.ui.lineEditPTSScanStep.setEnabled(True)
    #         self.mw['PTS'][2] = True
    #         self.ui.lineEditPTSFreq.setEnabled(False)
    #         start = self.mw['PTS'][1]
    #         self.ui.lineEditPTSScanStart.setText(str(start))
    #         self.updatePTSScanStop()
    #         self.scan['type'] = 'frequency'
    #     else:
    #         self.ui.lineEditPTSScanStart.setEnabled(False)
    #         self.ui.lineEditPTSScanStep.setEnabled(False)
    #         self.mw['PTS'][2] = False
    #         self.ui.lineEditPTSFreq.setEnabled(True)
    #
    # def updatePTSScanStop(self):
    #     start= float(self.ui.lineEditPTSScanStart.text())
    #     step = float(self.ui.lineEditPTSScanStep.text())
    #     num = int(self.ui.lineEditScanNum.text())
    #     self.mw['PTS'][3] = self.scan['start']  = start
    #     self.mw['PTS'][4] = self.scan['stepsize']= step
    #     self.mw['PTS'][5] = self.scan['steps'] =  num
    #     stop = start + step * num
    #     self.mw['PTS'][6] = stop
    #     self.ui.lineEditPTSScanStop.setText(str(stop))

    # end PTS scan updates
    # begin upload functions

    def upload(self):

        self.ui.pushButtonUpload.setEnabled(False)
        self.ui.pushButtonStart.setEnabled(False)
        #------------------------------------------------------------
        # 2021-02-07 : Gurudev modified this code so that we create and write the wfms and SEQ files directly from
        # the main app. Upload thread is now called only to upload files to the AWG. If we want to go back to having
        # Uploadthread do those things, we will need to uncomment lines that mark this block

        # we are now ready to upload the sequence file to awg
        self.uThread.seq = self.seq
        self.uThread.scan = self.scan
        self.uThread.parameters = self.parameters
        self.uThread.awgparams = self.awgparams
        self.uThread.pulseparams = self.pulseparams
        self.uThread.mw=self.mw
        self.uThread.timeRes=self.timeRes
        self.uThread.CompSeqNum=self.CompSeqNum
        self.uThread.PauliRandNum=self.PauliRandNum

        #--------------------------------------------------------------
        # and now comment out the lines below this block
        # # create files
        # samples = self.parameters[0]
        # delay = self.parameters[-2:]
        #
        # enable_scan_pts = self.mw['PTS'][2]
        # if enable_scan_pts:
        #     # we can scan frequency either using PTS or using the SB freq
        #     # self.scan['type'] = 'frequency'
        #     self.scan['type'] = 'no scan'  # this tells the SeqList class to simply put one sequence as the PTS will
        #     # scan the frequency
        # # now create teh sequences
        # self.sequences = SequenceList(sequence=self.seq, delay=delay, pulseparams=self.pulseparams,
        #                               scanparams=self.scan,
        #                               timeres=self.timeRes)
        # # write the files to the AWG520/sequencefiles directory
        # self.awgfile = AWGFile(ftype='SEQ', timeres=self.timeRes)
        # self.awgfile.write_sequence(self.sequences, repeat=samples)
        # ending here -----------------------------------------------------------
        # start the upload
        self.uThread.start()
        self.ui.statusbar.showMessage("Uploading Files to the AWG...")

    def uploadDone(self):
        self.ui.pushButtonUpload.setEnabled(True)
        self.ui.pushButtonStart.setEnabled(True)
        self.ui.statusbar.showMessage("Upload Done!", 3000)
        if self.ui.checkBoxStart.isChecked():
            self.start()

    # end upload functions
    # begin KeepNV  functions
    def standby(self):
        self.standingby = True
        self.ui.pushButtonStart.setEnabled(False)
        # self.kThread.start()

    def getReady(self):
        self.kThread.running = False

    def keepStatus(self, s):
        self.ui.statusbar.showMessage(s)
        s = str(s)
        if s == 'Ready!':
            self.standingby = False
            self.ui.pushButtonUpload.setEnabled(True)
            self.ui.pushButtonStart.setEnabled(True)
            # TODO: this next section makes no sense , taken from old code, fix later
            # try:
            #     self.seq
            # except AttributeError:
            #     self.ui.pushButtonStart.setEnabled(False)
        elif s.startswith('Monitoring counts...'):
            self.maxcounts = int(s[20:]) # the keep thread emits a string signal which can be either 1. "Tracking..."
            # or 2. "Monitoring counts...NNN" where NNN is the counts

    def updateThreshold(self):
        self.parameters[4] = int(self.ui.lineEditThreshold.text())
        try:
            if self.sThread.scanning:
                self.sThread.parameters[4] = self.parameters[4]
        except:
            pass
    # end keep NV functions
    # update sequence from metadata textbox
    def updateSequenceText(self):
        seqtext = self.ui.metadatatextEdit.toPlainText()
        print('the sequence text which will be converted is',seqtext)
        # self.convert_text_to_seq(seqtext)   # trying this -- Gurudev 2021-04-29
        self.seq = seqtext      # we will simply send the sequence text to the sequence object on backend
        self.getReady() # turn off the keep process
        #print("the new seq text is",new_stext)
        #self.ui.metadatatextEdit.clear()
        #self.ui.metadatatextEdit.setText(new_stext)
    # commented this out on 2021-04-29 -- Gurudev
    # def convert_text_to_seq(self, seqtext):
    #     # get a list of all the lines in the textbox
    #     all_lines = seqtext.split('\n')
    #     self.seq = []
    #     b_all_lines = all_lines[:]  # make a copy
    #     # now iterate over the copy, and create a list of a list of strings which specify the sequence
    #     for (idx, line) in list(enumerate(b_all_lines)):
    #         wfm = line.split(',')
    #         self.seq.append(wfm)
    #         #b_all_lines[idx:idx] = [wfm]
    #     #self.seq = self.seq[:-1]
    #     print('text box converted to',self.seq)
    #
    #     # new_stext = ''
    #     # for (l,s) in list(enumerate(b_all_lines)):
    #     #     new_stext = new_stext + s + '\n'
    #     # return new_stext




    # begin scanning and other misc functions
    def start(self):
        self.sThread.parameters = self.parameters
        self.sThread.scan = self.scan
        self.sThread.mw = self.mw
        self.sThread.awgparams = self.awgparams
        self.sThread.pulseparams = self.pulseparams
        self.sThread.maxcounts = self.maxcounts
        self.ui.pushButtonStart.setEnabled(False)
        self.ui.pushButtonUpload.setEnabled(False)
        self.ui.checkBoxAutoSave.setEnabled(False)
        numavgs = self.parameters[3]
        start = self.scan['start']
        step = self.scan['stepsize']
        if self.scan_random: self.scan['steps'] = int(self.scan['steps'])*self.PauliRandNum  # accounting for pauli randomizations
        numsteps = int(self.scan['steps'])
        use_pts = self.mw['PTS'][0]
        enable_scan_pts = self.mw['PTS'][2]
        current_freq = self.mw['PTS'][1]
        start_freq = self.mw['PTS'][3]
        step_freq = self.mw['PTS'][4]
        num_freq_steps = self.mw['PTS'][5]
        stop_freq = self.mw['PTS'][6]
        self.tab_data = numpy.zeros((numavgs,numsteps, 2), dtype=int)
        self.raw_data = self.tab_data.reshape(1, numavgs * numsteps, 2)[0]
        self.raw_data.fill(-1)
        self.dataCount = 0
        self.avgCount = 0

        self.x_arr = list(range(1, numsteps + 1))
        if use_pts and enable_scan_pts:  # if scanning PTS freq
            self.x_arr = numpy.arange(start_freq, start_freq + step_freq * num_freq_steps,
                                      step_freq) #[:self.scan[2]] this was from old code, not sure why
                                                # maybe to drop a point in the array?
        else:
            self.x_arr = numpy.arange(start, start + step * numsteps, step)
            #[:self.scan[2]]

        if self.ui.checkBoxAutoSave.checkState():
            self.getDataDir()

        self.sThread.start()

    def getDataDir(self):
        numsteps = int(self.scan['steps'])
        numavgs = self.parameters[3]
        dir = Path('.')
        dir = 'D:\\Data\\quantum-pulse\\' + str(datetime.date.today())
        if not os.path.isdir(dir):
            os.makedirs(dir)
        self.dir = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Data As...', dir + '\\' + 'Untitled' + '.txt',
                                                         "Text files (*.txt)")
        self.dir = str(self.dir.replace('/', '\\'))
        self.dir_log = self.dir[:-4] + '.log'

    def dataBack(self, sig, ref):
        numsteps = int(self.scan['steps'])
        avgs = int(self.parameters[3])
        steps = numsteps*avgs
        self.ui.lineEditSig.setText(str(sig))
        self.ui.lineEditRef.setText(str(ref))

        self.raw_data[self.dataCount] = [sig, ref]
        self.dataCount += 1

        if self.dataCount % numsteps == 0:
            self.avgCount += 1
            if self.ui.checkBoxAutoSave.checkState():
                f = open(self.dir, 'a')
                for i in range(numsteps):
                    f.write(str(self.tab_data[self.avgCount - 1][i][0]) + '\t' + str(
                        self.tab_data[self.avgCount - 1][i][1]) + '\n')
                f.close()
            if self.scan_random: self.updateRBplot()
            else: self.updateDataPlot()


        if self.dataCount == len(self.raw_data):
            self.scanDone()
        scp = (self.dataCount/steps)*100  # scan completion percentage
        self.ui.statusbar.showMessage("Scan Completion: " + str(round(scp, 2)) + "%")
        # self.ui.statusbar.showMessage("Currently Scanning... Step: " + str(self.dataCount) + "/" + str(steps) +
        #                               " Scan: " + str(self.avgCount) + "/" + str(avgs))


    def trackingBack(self, count):
        pass

    def stop(self):
        self.sThread.proc_running = False
        self.scanDone()

    def scanDone(self):
        self.sThread.scanning = False
        # self.ui.pushButtonStart.setEnabled(True)
        self.ui.pushButtonUpload.setEnabled(True)
        self.ui.checkBoxAutoSave.setEnabled(True)
        self.ui.checkBoxAutoSave.setEnabled(True)
        self.dataPlot_renew = True
        if self.scan_random: self.updateRBplot()
        else: self.updateDataPlot()

        if self.ui.checkBoxAutoSave.checkState():
            f = open(self.dir_log, 'w')
            f.write(
                str(self.parameters) + '\n' + str(self.scan) + '\n' + str(self.mw) + '\n' + str(self.avgCount) + '\n')
            for each_x in self.x_arr:
                f.write(str(each_x) + '\t')
            f.write('\n')
            f.close()

        self.standby()

    def saveData(self):
        # self.getDataDir()
        try:
            date_today = str(datetime.date.today())
            time_now = (datetime.datetime.now()).strftime("%H-%M-%S")

            numsteps = int(self.scan['steps'])
            numavgs = self.parameters[3]

            dir = 'D:\\Data\\quantum-pulse\\' + date_today
            if not os.path.isdir(dir):
                os.makedirs(dir)

            filename = self.ui.lineEditExpName.text()
            if filename == '':
                self.dir = dir + '\\' + time_now + '.txt'
                self.dir_log = dir + '\\' + time_now + '.log'
            else:
                self.dir = dir + '\\' + filename + '.txt'
                self.dir_log = dir + '\\' + filename + '.log'

            if self.dir != '':
                f = open(self.dir, 'a')
                for i in range(self.avgCount * numsteps):
                    f.write(str(self.raw_data[i][0]) + '\t' + str(self.raw_data[i][1]) + '\n')
                f.close()

                f = open(self.dir_log, 'w')
                f.write(str(self.parameters) + '\n' + str(self.scan) + '\n' + str(self.mw) + '\n' + str(self.avgCount) + '\n')
                for each_x in self.x_arr:
                    f.write(str(each_x) + '\t')
                f.write('\n\n')
                metadata = self.ui.textEditMetaData.toPlainText()
                f.write(metadata)
                f.write('\n')
                f.close()
        except Exception as e:
            print(e)
        self.ui.lineEditExpName.setText('')

    def updateDataPlot(self):
        avgData = numpy.average(self.tab_data[:self.avgCount], 0)
        [sigData, refData] = numpy.transpose(avgData)
        print(len(self.x_arr), len(sigData), len(refData))
        print(self.x_arr)

        if self.dataPlot_renew:
            self.ui.mplDataPlot.figure.clear()
            self.ui.mplDataPlot.axes = self.ui.mplDataPlot.figure.add_subplot(111)
            self.sigPlot = None
            self.refPlot = None
            self.dataPlot_renew = False

        if self.refPlot is not None:
            self.refPlot.set_xdata(self.x_arr)
            self.refPlot.set_ydata(refData)
        else:
            self.refPlot, = self.ui.mplDataPlot.axes.plot(self.x_arr, refData, 'k')
        if self.sigPlot is not None:
            self.sigPlot.set_xdata(self.x_arr)
            self.sigPlot.set_ydata(sigData)
        else:
            self.sigPlot, = self.ui.mplDataPlot.axes.plot(self.x_arr, sigData, 'r')

        self.ui.mplDataPlot.draw()
    # end scanning functions

    def updateRBplot(self):
        # This function updates the plot when the scan is a random scan -> Scatter Plot
        self.ui.mplDataPlot.axes.clear()
        avgData = numpy.average(self.tab_data[:self.avgCount], 0)
        [sigData, refData] = numpy.transpose(avgData)
        print(len(self.rb_x_arr), len(sigData), len(refData))
        print(self.rb_x_arr)

        self.ui.mplDataPlot.axes.set_xlim(min(self.rb_x_arr)-1,max(self.rb_x_arr)+1)
        self.ui.mplDataPlot.axes.scatter(self.rb_x_arr, refData, c='k')
        self.ui.mplDataPlot.axes.scatter(self.rb_x_arr, sigData, c='r')
        self.ui.mplDataPlot.draw()

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    window = appGUI(nohardware=False)
    #myClass.load_defaults()
    window.show()
    #finish logger
    logging.info("Finished")

    sys.exit(app.exec_())
