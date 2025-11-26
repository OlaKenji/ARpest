"""Helpers for fitting and aligning Fermi-Dirac distributions."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.optimize import curve_fit

from ..constants import kB, elementary_charge
from scipy import ndimage

def fit_fermi_dirac(energies, edc, e_0, T=10, sigma0=1, a0=0, b0=-0.1):
    # Normalize the EDC to interval [0, 1]
    edcmin = edc.min()
    edcmax = edc.max()
    edc = (edc-edcmin)/(edcmax-edcmin)

    # Initial guess and bounds for parameters
    p0 = [e_0, sigma0, a0, b0]
    de = 1
    lower = [e_0-de, 0, -10, -1]
    upper = [e_0+de, 100, 10, 1]

    # Carry out the fit
    p, cov = curve_fit(FD_function, energies, edc, p0=p0, bounds=(lower, upper))

    res_func = lambda x : FD_function(x, *p)
    return p, res_func

def FD_function(E, E_F, sigma, a, b, T=10):
    # Basic Fermi Dirac distribution at given T
    sigma = 0
    kT = kB * T / elementary_charge
    y = 1 / (np.exp((E-E_F)/kT) + 1)

    # Add a linear contribution to the 'below-E_F' part
    y += (a*(E-E_F)+b) * step_function(E, E_F, flip=True)

    # Convolve with instrument resolution
    if sigma > 0 :
        y = ndimage.gaussian_filter(y, sigma)
    return y

def step_function(x, step_x, flip) :
    res = \
    np.frompyfunc(lambda x : step_function_core(x, step_x, flip), 1, 1)(x)
    return res.astype(float)

def step_function_core(x, step_x, flip) :
    """ Implement a perfect step function f(x) with step at `step_x`::

                / 0   if x < step_x
                |
        f(x) = {  0.5 if x = step_x
                |
                \ 1   if x > step_x

    **Parameters**

    ======  ====================================================================
    x       array; x domain of function
    step_x  float; position of the step
    flip    boolean; Flip the > and < signs in the definition
    ======  ====================================================================
    """
    sign = -1 if flip else 1
    if sign*x < sign*step_x :
        result = 0
    elif x == step_x :
        result = 0.5
    elif sign*x > sign*step_x :
        result = 1
    return result        
