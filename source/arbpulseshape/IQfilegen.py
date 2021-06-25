import numpy as np
import matplotlib.pyplot as plt
import scipy.fftpack as fftpack

# fc = 1e8  # Carrier frequency (GHz)
# T = 1000.0e-9  # Time Range (ns)
# n = 5000  # Number of Steps
# sweep_range = 2*20.0e6  # Sweep range (GHz)

T = 2000  # Time Range (ns)
n = 100  # Number of Steps
sweep_range = 2*20.0e-3  # Sweep range (GHz)

time = np.linspace(0, T, n)  # time-space
yI = np.sin(sweep_range*2*np.pi*time**2/T)  # I Channel
yQ = np.cos(sweep_range*2*np.pi*time**2/T)  # Q Channel

# yF = yI*np.cos(2*np.pi*fc*time) + yQ*np.sin(2*np.pi*fc*time)  # Final Output
# yF = np.cos(2*np.pi*fc*time)


def create_wfmfile(time, yI, yQ):
    f = r"D:\PyCharmProjects\quantum-pulse\source\arbpulseshape\IQdata.txt"
    with open(f, 'w') as f:
        for i, tt in enumerate(time):
            f.write(f'{i}, {tt}, {yI[i]}, {yQ[i]} \n')


def fourier(t, y):
    N = len(t)
    f = fftpack.fftfreq(N, t[1] - t[0])

    # find the FFT and choose only positive frequencies
    sig_fft = fftpack.fft(y)
    power = np.abs(sig_fft)
    pos_mask = np.where(f > 0)
    freqs = f[pos_mask]
    # peak_freq = freqs[power[pos_mask]>0]
    # print('The peak frequencies are:', peak_freq)
    psd = power[pos_mask]
    choosef = freqs[freqs<50.0]
    choosep = psd[freqs < 50.0]

    fig, ax = plt.subplots(2,tight_layout='True')
    ax[0].plot(t, y, 'b-',label=r'f(t)')
    ax[1].plot(choosef,choosep,'r.-',label=r'$|F(\omega)|^2$')
    ax[0].legend(loc=0)
    ax[1].legend(loc=0)
    ax[0].set_xlabel(r'Time (ns)', fontsize=12)
    ax[0].set_ylabel(r' ', fontsize=12)
    ax[1].set_ylabel(r'Power(W)', fontsize=12)
    ax[1].set_xlabel(r'GHz', fontsize=12)
    plt.show()

plt.plot(time, yI, time, yQ)
# plt.plot(time, yF)
plt.show()

# fourier(time, yF)

create_wfmfile(time, yI, yQ)
