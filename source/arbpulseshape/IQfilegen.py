import numpy as np
import matplotlib.pyplot as plt


T = 1000
n = 100
time = np.linspace(0, T, n)
yI = np.cos(80e-3*np.pi*time**2/T)
yQ = np.sin(80e-3*np.pi*time**2/T)

f = r'D:\PyCharmProjects\quantum-pulse\source\arbpulseshape\IQdata.txt'

with open(f,'w') as f:
    for i, tt in enumerate(time):
        f.write(f'{i}, {tt}, {yI[i]}, {yQ[i]} \n')


plt.plot(time,yQ)
plt.show()

