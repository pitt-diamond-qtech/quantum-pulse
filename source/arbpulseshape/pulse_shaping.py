import numpy as np
from sympy import *
from sympy.plotting import plot_parametric
import matplotlib.pyplot as plt
# from mpmath import *
from scipy import integrate
from scipy.interpolate import interp1d
import os

"""This programs aims at realizing pulses of different shapes for the control of a spin.

It is based on:
General solution to inhomogeneous dephasing and smooth pulsedynamical decoupling
J. Zeng et al. NJP (2018)

The program used:
-sympy for formal calculation of the function
(mainly to automatically and exactly calculate the derivatives and the functions
kappa and sqrt(x'^2 + y'^2)). This explain why you need a symbolic variable l.
- numpy and scipy for numerical calculation of the integral and interpolation.
- matplotlib for displaying.
(all these package can be easily installed "pip install ..." or "conda install ...")

You should create the parametric functions x and y (depending on lambda) using sympy functions. See my example on bernoulli_func.

The core of the program is the function core_calculation.
It takes into account sympy function x and y (depending on l) and a numpy list of lambda ll
and returns the function kappa (depending on lambda, working with numpy), the numpy list of time t_of_l_list
and the interpolated function of lambdas depending on time l_of_t_func (also working with numpy).

The only work to be done, is generating a set of amplitudes Omega for given times.
To do so, we calculate the longest time of t_of_list (t_max),
and we create a list of time tt ranging from 0 to t_max.
Finally we calculate Omega(t) given by kappa(l_of_t_func(tt)). And that's it.

"""


l = Symbol('l')  # Sympy variable corresponding to lambda (lambda means function in python... so I used l)
dir_path = os.path.dirname(os.path.realpath(__file__))


def core_calculation(x, y, ll, l=l):
    """ Generate  all the necessary functions to calculate Omega(t)."""

    # From x and y (depending on lambda), generates sqrt(x'^2 + y'^2) kappa (of l)
    integrated_part, kappa = func_kappa_and_int(x, y, l)

    # Generate the list of time for lambda and the l(t) function
    t_of_l_list, l_of_t_func = link_t_and_l(ll, integrated_part)

    return kappa, t_of_l_list, l_of_t_func


def link_t_and_l(ll, integrated_part):
    """Realize the link between lambda and time"""
    t_of_l_list = []
    for mu in ll:
        # Calculate numerically the integral
        n_int, err = integrate.quad(integrated_part, 0, mu)
        t_of_l_list.append(n_int)

    # calculate the function l(t) by cubic interpolation
    interpolated_func = interp1d(t_of_l_list, ll, kind='cubic')
    return t_of_l_list, interpolated_func


def func_kappa_and_int(x, y, l=l):
    """ Caculate sqrt(x'^2 + y'^2) and kappa (depending on l)."""
    # Calculate the first and second order derivatives of x(l) and y(l) (with respect to l)
    xprime = x.diff(l)
    xprime2 = xprime.diff(l)
    yprime = y.diff(l)
    yprime2 = yprime.diff(l)

    # Calculate kappa(l) and sqrt(x'^2 + y'^2)
    kappa = (xprime * yprime2 - yprime * xprime2) / (xprime ** 2 + yprime ** 2) ** (3. / 2)
    integrated_part = sqrt(xprime ** 2 + yprime ** 2)

    # Convert them into function that works with numpy arrays (before it was sympy objects)
    integrated_part = convert_numpy(integrated_part, l)
    kappa = convert_numpy(kappa, l)
    return integrated_part, kappa


def convert_numpy(func, param=l):
    """Convert a sympy function into a numpy function"""
    return lambdify(param, func, 'numpy')


# Bernoullli parametrization
def bernoulli_func(alpha, l=l):
    """Note that this function return x and y of l at the same time.

    Note also that we are using the sympy functions sin, cos and not the numpy np.cos, ..."""
    x = alpha * sin(2 * l) / (3 + cos(2 * l))
    y = 2 * sin(l) / (3 + cos(2 * l))
    return x, y


# Gerono parametrization
def gerono_func(alpha, l=l):
    """Note that this function return x and y of l at the same time.

    Note also that we are using the sympy functions sin, cos and not the numpy np.cos, ..."""
    x = alpha / 2. * sin(2 * l)
    y = sin(l)
    return x, y


def non_trivial(a, b, l=l):
    """ Warning: require l_max to be 2 pi and not only pi."""
    x = (a + b * cos(l)) * sin(l)
    y = l * (2 * pi - l) + (4 + b / a) * (cos(l) - 1)
    return x, y

# Modification by Gurudev to generate alphas
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

if __name__ == "__main__":



    phi,alpha = alphafromphi(np.pi/3,5)#50)
    max_val = 0
    kappa_write = np.zeros([len(alpha), 500])

    for i in range(0,len(alpha)):
        # Collect the sympy x and y of l functions
        # x, y = bernoulli_func(alpha=np.pi/2)  # Require ll_max = np.pi
        x, y = gerono_func(alpha[i])  # Require ll_max = np.pi
        # x, y = non_trivial(a=1, b=-6)  # Require ll_max = 2 * np.pi
        # x, y = non_trivial(a=-2 / 3., b=+2 / 3.)  # Require ll_max = 2 * np.pi
       # print alpha[i]

        # Numpy list of lambdas
        ll_max = 2 * np.pi  # Maximum value of the parametrization (can be pi or 2 pi)
        n_points = 500  # Number of points for the calculations (the higher the more accurate it is)
        ll = np.linspace(0, ll_max, num=n_points)

        # Calculate the important parameters
        kappa, t_of_l_list, l_of_t_func = core_calculation(x, y, ll, l=l)

        # Create a list of time
        t_max = max(t_of_l_list)
        tt = np.linspace(0, t_max, num=n_points)

        # Save the data in a file:
        # the information is stored as:
        # n, t, Omega(t)

        file_name = 'test' +str(i)+'.txt'
        with open(os.path.join(dir_path, file_name), 'w') as outfile:
            for ind, t in enumerate(tt):
                outfile.write("%s, %s, %s \n" % (ind, t, kappa(l_of_t_func(t))))

        fig, (ax1, ax2) = plt.subplots(2)

        # Convert the functions into numpy functions to be able to plot them with matplotlib
        xx = convert_numpy(x, param=l)
        yy = convert_numpy(y, param=l)
        ax1.plot(xx(ll), yy(ll))

        ax2.plot(tt, kappa(l_of_t_func(tt)))
        kappa_write[i,:] = kappa(l_of_t_func(tt))

        if np.amax(kappa_write[i,:]) > max_val:
            max_val = np.amax(kappa_write[i,:])
        print(max_val)

        # Can also use the sympy plotting option if you want
        plot_parametric(x, y, (l, 0, ll_max))

        # plt.show()



