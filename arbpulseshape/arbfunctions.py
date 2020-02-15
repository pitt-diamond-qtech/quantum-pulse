import numpy as np
from matplotlib import pyplot as plt
import math

path = 'D:/workspace/awg test/wfm files/'


def gaussian(x, mu, sig): #x is array of values
    return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))/(np.sqrt(2*np.pi*sig**2))
def newgauss(x,mu,sig, vmax):
    return np.exp(-np.power(x-mu,2.)/(2*np.power(sig,2.)))*vmax

def sech(x):
    #y = np.zeros(len(x))
    #for i in range(0,len(x)-1):
        #y[i] = 2/(np.exp(x)+np.exp(-x))

    return 2/(np.exp(x)+np.exp(-x))

def tanh(x):
    y = np.zeros(len(x))
    for i in range(0,len(x) - 1):
        y[i] = math.tanh(x[i])
    return y

def zerothFile(maxend, timeFactor):
    '''the first .wfm for any sequence should be blank. it runs 'infinitely' until event occurs. all other .wfm's in seq run 50000 times to accumulate counts.'''

    f = open(path + '0_1.wfm', 'wb')
    f.write('MAGIC 1000\r\n')
    f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))

    for i in range(maxend):
        f.write(np.float32(0))
        f.write(np.byte(0))
    if timeFactor == 1:
        f.write('CLOCK 1.0000000000E+9\r\n')
    elif timeFactor == 5:
        f.write('CLOCK 2.0000000000E+08\r\n')
    elif timeFactor == 10:
        f.write('CLOCK 1.0000000000E+08\r\n')
    elif timeFactor == 25:
        f.write('CLOCK 4.0000000000E+07\r\n')
    elif timeFactor == 100:
        f.write('CLOCK 1.0000000000E+07\r\n')
    f.close()

    f = open(path + '0_2.wfm', 'wb')
    f.write('MAGIC 1000\r\n')
    f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))

    for i in range(maxend):
        f.write(np.float32(0))
        f.write(np.byte(0))
    if timeFactor == 1:
        f.write('CLOCK 1.0000000000E+9\r\n')
    elif timeFactor == 5:
        f.write('CLOCK 2.0000000000E+08\r\n')
    elif timeFactor == 10:
        f.write('CLOCK 1.0000000000E+08\r\n')
    elif timeFactor == 25:
        f.write('CLOCK 4.0000000000E+07\r\n')
    elif timeFactor == 100:
        f.write('CLOCK 1.0000000000E+07\r\n')
    f.close()

def squareSweepT(NOS,amp,timeFactor,  StepSize):
    '''rabi sequences using traditional square sequence. amplitude is fixed, t varies in steps of StepSize wrt timeFactor NOS times.'''
    maxend = 5000
    wave1 = np.zeros([NOS, maxend])
    wave1_sq = np.zeros([NOS, maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])
    MW_start_time = 1000
    x = range(maxend)
    MW_start = 1000

    for j in range(NOS):
        f = open(path + str(j + 1) + '_1.wfm', 'wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))

        file_name = 'D:\workspace\\awg test\\test' + str(j) + '.txt'
        tt, omegarr, tt2, posomegarr = readfrompaul(file_name)


        for i in range(maxend):
            #MW_end_time = MW_start + StepSize * j
            wave1[j, i] = amp  # fixed mixer amplitude (always on)
            mark1[j, MW_start:(MW_start+ StepSize * j)] = 1.0  # c1m1 on - switch gates(?) mixer

            f.write(np.float32(wave1[j, i]))  # wave1[j,i]))
            f.write(np.byte(mark1[j, i]))
        if timeFactor == 1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor == 5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor == 10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor == 25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor == 100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()
    for j in range(NOS):
        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        for i in range(maxend):

            MW_end_time = MW_start + StepSize * j
            laserOn =MW_end_time +180#MW_end_time+S1delay
            startMeasure = laserOn + 820
            stopMeasure = startMeasure + 100
            laserOff = laserOn +3000


            wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
            mark2[j, startMeasure:stopMeasure] = 3  # measure


            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()


    plt.plot(x, wave1[5, :])  # , color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, (wave2[5, :]+1)/2 + 4, color='g')
    plt.plot(x, ((mark2[5, :])+1)/2 + 6, color='r')
    plt.show()


    plt.plot(x, wave1[-1, :])  # , color='b')
    plt.plot(x, mark1[-1, :] + 2, color='k')
    plt.plot(x, (wave2[-1, :]+1)/2 + 4, color='g')
    plt.plot(x, (mark2[-1, :]+1)/2 + 6, color='r')
    plt.show()

def spinEcho0(NOS,piPulse,t1):
    '''echo to find t1=t2. the first pi/2 to pi pulse are separated by fixed t. the final pi/2 pulse sweeps in time.'''
    maxend = 5000
    amp = 0.25
    wave1 = np.full([NOS, maxend],amp)
    wave1_sq = np.zeros([NOS, maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])

    x = range(maxend)
    halfpi1_On = 1000
    halfpi1_Off = halfpi1_On + piPulse/2
    pi_on = halfpi1_Off + t1
    pi_off = pi_on +piPulse
    halfpi2_On = pi_off + t1
    halfpi2_off = halfpi2_On + piPulse/2
    timeFactor = 1


    for j in range(NOS):
        f = open(path + str(j + 1) + '_1.wfm', 'wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))


        mark1[j,halfpi1_On:halfpi1_Off] = 1.0 #a half pi pulse
        mark1[j,pi_on:pi_off] = 1.0 #a pi pulse at fixed t from first half pi
        mark1[j, halfpi2_On:halfpi2_off] = 1.0  # a half pi pulse that sweeps wrt t
        for i in range(maxend):
            f.write(np.float32(0.25))  # wave1[j,i]))
            f.write(np.byte(mark1[j, i]))
        if timeFactor == 1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor == 5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor == 10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor == 25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor == 100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        MW_end_time =  halfpi2_off
        laserOn = MW_end_time +180#MW_end_time+S1delay
        startMeasure = laserOn + 820
        stopMeasure = startMeasure + 100
        laserOff = laserOn +3000

        wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
        mark2[j, startMeasure:stopMeasure] = 3  # measure
        for i in range(maxend):
            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()


    plt.plot(x, wave1[5, :])  # , color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, (wave2[5, :]+1)/2 + 4, color='g')
    plt.plot(x, ((mark2[5, :])+1)/2 + 6, color='r')
    plt.show()


    plt.plot(x, wave1[-1, :])  # , color='b')
    plt.plot(x, mark1[-1, :] + 2, color='k')
    plt.plot(x, (wave2[-1, :]+1)/2 + 4, color='g')
    plt.plot(x, (mark2[-1, :]+1)/2 + 6, color='r')
    plt.show()

def spinEcho1(NOS, stepSize, piPulse,t1,t2Start):
    '''echo to find t1=t2. the first pi/2 to pi pulse are separated by fixed t. the final pi/2 pulse sweeps in time.
    NOS = number of .wfm that will be in sequence
    stepSize = reso




    '''
    maxend = 7000

    amp = 0.25
    wave1 = np.full([NOS, maxend],amp)
    wave1_sq = np.zeros([NOS, maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])

    x = range(maxend)
    piPulse = int(piPulse + (2*piPulse))
    MW_start = 1000
    halfpi1 = int(MW_start + piPulse/2)

    fixedpi_on = int(halfpi1 + t1)
    fixedpi_off = int(fixedpi_on + piPulse)
    timeFactor = 1


    for j in range(NOS):
        f = open(path + str(j + 1) + '_1.wfm', 'wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        t2_on = fixedpi_off + t2Start + j*stepSize
        t2_off = t2_on + piPulse/2
        print t2_on, t2_off, t2_on-t2_off
        mark1[j,MW_start:halfpi1] = 1.0 #a half pi pulse
        mark1[j,fixedpi_on:fixedpi_off] = 1.0 #a pi pulse at fixed t from first half pi
        mark1[j, t2_on:t2_off] = 1.0  # a half pi pulse that sweeps wrt t
        for i in range(maxend):
            f.write(np.float32(wave1[j, i]))  # wave1[j,i]))
            f.write(np.byte(mark1[j, i]))
        if timeFactor == 1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor == 5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor == 10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor == 25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor == 100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        MW_end_time =  t2_off
        laserOn = MW_end_time +180#MW_end_time+S1delay
        startMeasure = laserOn + 820
        stopMeasure = startMeasure + 100
        laserOff = laserOn +3000

        wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
        mark2[j, startMeasure:stopMeasure] = 3  # measure
        for i in range(maxend):
            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()


    plt.plot(x, wave1[5, :])  # , color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, (wave2[5, :]+1)/2 + 4, color='g')
    plt.plot(x, ((mark2[5, :])+1)/2 + 6, color='r')
    plt.show()


    plt.plot(x, wave1[-1, :])  # , color='b')
    plt.plot(x, mark1[-1, :] + 2, color='k')
    plt.plot(x, (wave2[-1, :]+1)/2 + 4, color='g')
    plt.plot(x, (mark2[-1, :]+1)/2 + 6, color='r')
    plt.show()

def createWFM(timeFactor, NOS, func): #dt in ns, NOS = number of WFM files in sequence, V or C amp, MW start/end in UNITS OF DT
    maxend = 5000
    num_pts = int(maxend)

    # min_amp = float(input('minimum amp?'))
    # max_amp = float(input('maximum amp?'))
    # amp = np.linspace(min_amp, max_amp, NOS)
    # amp_resolution = (max_amp - min_amp) / (NOS - 1)
    wave1 = np.zeros([NOS,maxend])
    wave1_sq = np.zeros([NOS,maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])
    MW_start_time = 1000
    PiPulse = 50
    #MW_end_time = 1300#MW_start_time + 4*PiPulse
    #time_mw = MW_end_time - MW_start_time
    x=range(maxend)

    # print('amplitude will vary in steps of ' + str(amp_resolution) + 'V')

######################################################################################
    zerothFile(maxend, 1)


    '''real scan files/functions here'''



    for j in range(NOS):
        f = open(path+str(j+1)+'_1.wfm','wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))



        for i in range(maxend):
            mark= 0 #c1m1[i]+c1m2[i]*2
            if func == 'square':
                VStep = 0.3/(NOS-1)

                wave1[j, i] = VStep * j #1.0 * amp[j] # ch 1 connected to mixer, changing amp
                mark1[j, MW_start_time:MW_end_time] = 1.0 #c1m1 connected to switch

            if func == 'gauss':
                vmax = 0.3
                MW_start_time = 1000
                MW_end_time = 1300
                #sigma = (j+1)/(np.sqrt(2*np.pi))
                inc = np.linspace(1,53,NOS)
                sigma = inc[j]/(np.sqrt(2*np.pi))
                time_mw = MW_end_time-MW_start_time

                t_gauss = np.linspace(-100,100, time_mw)

                wave1[j,MW_start_time:MW_end_time] = newgauss(t_gauss,0,sigma, vmax)
                if wave1[j,i] >= 0.00399:
                    mark1[j,i] = 1.0

                # if wave1[j,i] >= 0.003:
                #     mark1[j,i] = 1.0
               # mark1[j,MW_start_time:MW_end_time] = 1.0
                wave1_sq[j, MW_start_time:(MW_start_time + 45)] = 0.3
            if func == 'gauss sweep':
                # V = 0.4
                # dV = V/(NOS-1)
                # vmax = dV*j
                # sigma = 80/(np.sqrt(2*np.pi))
                vmax = 0.3
                sigma = np.linspace(1,22.5,NOS)

                t_gauss = np.linspace(-50,50, time_mw)



                wave1[j,MW_start_time:MW_end_time] = newgauss(t_gauss,0,sigma[j], vmax)
                if wave1 >= 0.399:
                    mark1[j,i] = 1.0

                wave1_sq[j, MW_start_time:(MW_start_time + 45)] = 0.3

            if func == 'sech':
                # V = 0.4
                # dV = V/(NOS-1)
                # vmax = dV*j
                # sigma = 80/(np.sqrt(2*np.pi))
                vmax = 0.3
                dV = vmax/(NOS-1)
                Vj = dV*(j+1)
                vj = np.linspace(dV*40,dV*60,NOS)


                t_sech = np.linspace(-0.15,0.15, time_mw)

                wave1[j,MW_start_time:MW_end_time] = vmax * sech(np.pi*t_sech/vj[j])
                mark1[j,MW_start_time:MW_end_time] = 1.0
                wave1_sq[j, MW_start_time:(MW_start_time + 45)] = 0.3
            # if func == 'gauss':
            #     VStep = 0.3 / (NOS - 1)
            #     dA = 13.5/(NOS-1)
            #
            #     Vmax = 0.3
            #     sigma = dA*(NOS-1)/(np.sqrt(np.pi*2)*Vmax)
            #     t_g1 = np.linspace(0, 6*sigma, time_mw)  # x values for gaussian function
            #     wave1[j, MW_start_time:MW_end_time] = gaussian(t_g1, 3*sigma, sigma) * dA * (j+1)
            #     wave1_sq[j,MW_start_time:(MW_start_time+45)] = 0.3
            #     mark1[j, MW_start_time:MW_end_time] = 1.0  # c1m1 connected to switch
            if func == 'sweep':
                StepSize = 1 #(MW_end_time-MW_start_time)/(NOS-1)
                MW_end_time = MW_start_time + StepSize * j

                wave1[j,i] = 0.3 #fixed mixer amplitude (always on)

                #wave1[j,MW_start_time:(MW_start_time+StepSize*j)] = 1.0 #analog ch1 - controls IF signal
                mark1[j, MW_start_time:(MW_end_time)] = 1.0 #c1m1 on - switch gates(?) mixer

            f.write(np.float32(wave1[j,i]))#wave1[j,i]))
            f.write(np.byte(mark1[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

    for j in range(NOS):
        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        for i in range(maxend):
            if func == 'sweep':
                MW_end_time = MW_end_time#MW_start_time + StepSize * j

                laserOn =MW_end_time +180#MW_end_time+S1delay
                startMeasure = laserOn + 820
                stopMeasure = startMeasure + 100
                laserOff = laserOn +3000
            if func == 'gauss':
                #StepSize = 1

                #MW_end_time = MW_start_time + StepSize * j

                laserOn = MW_end_time + 180  # MW_end_time+S1delay
                startMeasure = laserOn + 820
                stopMeasure = startMeasure + 100
                laserOff = laserOn + 3000
            else:
                MW_end_time = MW_end_time

                laserOn = MW_end_time + 180  # MW_end_time+S1delay
                startMeasure = laserOn + 820
                stopMeasure = startMeasure + 100
                laserOff = laserOn + 3000


            wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
            mark2[j, startMeasure:stopMeasure] = 3  # measure


            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

    plt.plot(x,wave1_sq[5,:]-2)
    plt.plot(x,wave1[5,:])#, color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, wave2[5, :]+4, color='g')
    plt.plot(x, mark2[5, :]+6, color='r')
    plt.show()

    #plt.plot(x, wave1_sq[44, :] - 2)
    plt.plot(x, wave1[-1, :], color = 'b')#, color='b')
    #plt.plot(x, mark1[-1, :]+2, color='k')
    plt.plot(x, (wave2[-1, :]/2)+4, color='g')
    plt.plot(x, (mark2[-1, :]/2)+6,color='r')
    plt.show()

def timeSweep(NOS):
    maxend = 5000
    num_pts = int(maxend)
    wave1 = np.zeros([NOS,maxend])
    wave1_sq = np.zeros([NOS,maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])
    MW_start_time = 1000
    MW_end_time = 1100

    x=range(maxend)

def generateSeqFile(NOS):

    f = open(path + 'scan.seq', 'wb')
    f.write('MAGIC 3002\r\n')
    f.write('LINES ' + str(NOS+1) +'\r\n')  # len(amp))+'\r\n')
    seqtxt0 ='"0_1.wfm","0_2.wfm",0,1,0,0\r\n'
    print seqtxt0
    f.write('"0_1.wfm","0_2.wfm",0,1,0,0\r\n')#'"0_ch1.wfm","0_ch2.wfm",0,1,0,0\r\n')
    for i in range(NOS):
        seqtxt = '"' + str(i + 1) + '_1.wfm","' + str(i + 1) + '_2.wfm",50000,1,0,0\r\n'
        print seqtxt
        f.write('"' + str(i + 1) + '_1.wfm","' + str(i + 1) + '_2.wfm",50000,1,0,0\r\n')

    f.write('JUMP_MODE SOFTWARE\r\n')
    f.close()

def logic(on, off, NOS):
    """
    on = on_length
    off = off_length
    NOS = # of steps
    """
    x = np.full(on,1)
    y = np.zeros(off)

    one_cycle = np.append(x,y)
    output = np.array([])

    for i in range(NOS):
        output = np.append(output, one_cycle)

    return output

def repeatFunc(on, off, NOS):
    """
    on = on_length
    off = off_length
    NOS = # of steps
    """
    t = np.linspace(-100,100,on)
    x = newgauss(t,0,12.5525,0.3)
    y = np.zeros(off)


    one_cycle = np.append(x,y)
    output = np.array([])

    for i in range(NOS):
        output = np.append(output, one_cycle)

    return output

def piPulsesArbFunc(NOS,timeFactor, t):#piPulse,t):
    '''rabi sequences using traditional square sequence. amplitude is fixed, t varies in steps of StepSize wrt timeFactor NOS times.'''
    maxend = 12000
    wave1 = np.zeros([NOS, maxend])
    wave1_sq = np.zeros([NOS, maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])
    MW_start_time = 1000
    x = range(maxend)
    MW_start = 1000
    stepSize = 1 #ns
    # piPulse = 20
    # t=20


    for j in range(NOS):
        f = open(path + str(j + 1) + '_1.wfm', 'wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        # MW_end = stepSize * j

        step_sequence = repeatFunc(300, t, j)#logic(piPulse, t, j) # returns j pulses of length piPulse
        #mark1[j, MW_start:MW_end] = 1.0

        step_sequence = np.append(np.zeros(MW_start), step_sequence)
        MW_end = len(step_sequence) # assuming each element of step_sequence represents 1 ns

        wave1[j,:len(step_sequence)] = step_sequence

        for i in range(maxend):
            #MW_end_time = MW_start + StepSize * j
              # c1m1 on - switch gates(?) mixer
            if wave1[j,i] > 0.0029:
                mark1[j,i] = 1.0

            f.write(np.float32(wave1[j, i]))  # wave1[j,i]))
            f.write(np.byte(mark1[j, i]))
        if timeFactor == 1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor == 5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor == 10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor == 25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor == 100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        for i in range(maxend):


            laserOn =MW_end +180#MW_end_time+S1delay
            startMeasure = laserOn + 820
            stopMeasure = startMeasure + 100
            laserOff = maxend-1#laserOn +3000


            wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
            mark2[j, startMeasure:stopMeasure] = 3  # measure


            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        # if laserOff > maxend:
        #     maxend = maxend +4
        # else:
        #     maxend = maxend

        f.close()


    plt.plot(x, wave1[5, :])  # , color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, (wave2[5, :]+1)/2 + 4, color='g')
    plt.plot(x, ((mark2[5, :])+1)/2 + 6, color='r')
    plt.show()


    plt.plot(x, wave1[-1, :])  # , color='b')
    plt.plot(x, mark1[-1, :] + 2, color='k')
    plt.plot(x, (wave2[-1, :]+1)/2 + 4, color='g')
    plt.plot(x, (mark2[-1, :]+1)/2 + 6, color='r')
    plt.show()


def piPulses(NOS,amp,timeFactor, piPulse, t):#piPulse,t):
    '''rabi sequences using traditional square sequence. amplitude is fixed, t varies in steps of StepSize wrt timeFactor NOS times.'''
    maxend = 6000
    wave1 = np.full([NOS, maxend], amp)#amp)
    wave1_sq = np.zeros([NOS, maxend])
    wave2 = np.full([NOS, maxend], -1.0)
    mark1 = np.zeros([NOS, maxend])
    mark2 = np.zeros([NOS, maxend])
    MW_start_time = 1000
    x = range(maxend)
    MW_start = 1000/timeFactor
    stepSize = 1 #ns



    for j in range(NOS):
        f = open(path + str(j + 1) + '_1.wfm', 'wb')
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        # MW_end = stepSize * j

        step_sequence = logic(piPulse, t, j) #repeatFunc(300, t, j)#logic(piPulse, t, j) # returns j pulses of length piPulse
        #mark1[j, MW_start:MW_end] = 1.0

        step_sequence = np.append(np.zeros(MW_start), step_sequence)
        MW_end = len(step_sequence) # assuming each element of step_sequence represents 1 ns

        mark1[j,:len(step_sequence)] = step_sequence
        #wave1[j,:len(step_sequence)] = step_sequence

        for i in range(maxend):
            #MW_end_time = MW_start + StepSize * j
              # c1m1 on - switch gates(?) mixer
            # if mark1[j,i] > 0.003:
            #     wave1[j,i] = 1.0

            f.write(np.float32(0.3))#mark1[j,i]))#wave1[j, i]))  # wave1[j,i]))
            f.write(np.byte(mark1[j,i])) #wave1[j, i]))
        if timeFactor == 1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor == 5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor == 10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor == 25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor == 100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        f.close()

        f = open(path+str(j+1)+'_2.wfm','wb') #.wfm files 1-NOS
        f.write('MAGIC 1000\r\n')
        f.write('#' + str(len(str(maxend * 5))) + str(maxend * 5))
        print str(j+1)+'_2.wfm'

        for i in range(maxend):


            laserOn =MW_end +180#MW_end_time+S1delay
            startMeasure = laserOn + 820
            stopMeasure = startMeasure + 100
            laserOff = maxend-1#laserOn +3000


            wave2[j, laserOn:laserOff] = 1.0  # laser on (analog channel 2)
            mark2[j, startMeasure:stopMeasure] = 3  # measure


            f.write(np.float32(wave2[j,i]))
            f.write(np.byte(mark2[j,i]))
        if timeFactor==1:
            f.write('CLOCK 1.0000000000E+9\r\n')
        elif timeFactor==5:
            f.write('CLOCK 2.0000000000E+08\r\n')
        elif timeFactor==10:
            f.write('CLOCK 1.0000000000E+08\r\n')
        elif timeFactor==25:
            f.write('CLOCK 4.0000000000E+07\r\n')
        elif timeFactor==100:
            f.write('CLOCK 1.0000000000E+07\r\n')
        # if laserOff > maxend:
        #     maxend = maxend +4
        # else:
        #     maxend = maxend

        f.close()


    plt.plot(x, wave1[5, :])  # , color='b')
    plt.plot(x, mark1[5, :] + 2, color='k')
    plt.plot(x, (wave2[5, :]+1)/2 + 4, color='g')
    plt.plot(x, ((mark2[5, :]))/2 + 6, color='r')
    plt.show()


    plt.plot(x, wave1[-1, :]+2)  # , color='b')
    #plt.plot(x, mark1[-1, :] + 2, color='k')
    plt.plot(x, (wave2[-1, :]+1)/2 + 4, color='g')
    plt.plot(x, (mark2[-1, :]+1)/3 + 6, color='r')
    plt.ylim(0,8)
    plt.show()

def alphafromphi(maxphi,n):
    phiarr = np.linspace(0.1,maxphi,n)
    alpha = np.cos(phiarr)/np.sin(phiarr)
    return phiarr,alpha

def readfrompaul(file_name):
    csv = np.genfromtxt(file_name,delimiter=',')
    tt = csv[:,1]
    omegarr = csv[:,2]
    posomegarr = omegarr[omegarr>0.0001]
    tt2 = tt[omegarr>0.0001]
    return tt,omegarr,tt2,posomegarr



#piPulses(30,0.192,1, 75, 20)

#squareSweepT(100, 0.2, 1, 2)
#
# path = 'D:/workspace/awg test/'
#
#
# tt,omegarr,tt2,posomegarr = readfrompaul(path+ 'test.txt')
#
# plt.plot(tt2,posomegarr)
# plt.show()
#
# print len(tt2)


#piPulsesArbFunc(10,1,1, 20, 10)

#createWFM(1, 100, 'gauss')
#piPulsesArbFunc(10,10,1, 300, 10)
#piPulses(20,0.3,1, 50, 30)

piPulsesArbFunc(20,1, 0)

#squareSweepT(100,0.3,1,1)

#piPulsesArbFunc(10,1, 10)