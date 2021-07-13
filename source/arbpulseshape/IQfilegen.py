import numpy as np
import matplotlib.pyplot as plt

T = 4000  # Time Range (ns)
n = 4000  # Number of Steps
sweep_range = 20.0e-3  # Sweep range (GHz)

time = np.linspace(0, T, n)  # time-space
yI = np.sin(2*np.pi*sweep_range*(time/T-1)*time)
yQ = np.cos(2*np.pi*sweep_range*(time/T-1)*time)

def create_wfmfile(time, yI, yQ):
    f = r"D:\PyCharmProjects\quantum-pulse\source\arbpulseshape\IQdata.txt"
    with open(f, 'w') as f:
        for i, tt in enumerate(time):
            f.write(f'{i}, {tt}, {yI[i]}, {yQ[i]} \n')


create_wfmfile(time, yI, yQ)

plt.plot(time, yI, time, yQ)
plt.show()
