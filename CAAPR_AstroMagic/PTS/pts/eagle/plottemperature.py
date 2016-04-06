#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.eagle.plottemperature Plot a histogram of dust mass versus dust temperature for an EAGLE SKIRT-run.

# The facilities in this module serve to plot a histogram of dust mass versus dust
# temperature for a particular EAGLE SKIRT-run.
# The data is obtained from the <prefix>_ds_celltemps.dat file generated by SKIRT.
#
# ----------------------------------------------------------------------

import matplotlib.pyplot as plt

# import standard modules
import os.path
import numpy as np

# import pts modules
from ..core.tools import archive as arch

# ----------------------------------------------------------------------

## This function creates a histogram of dust mass versus dust temperature for
# a particular EAGLE SKIRT-run.
# The data is obtained from the prefix_ds_celltemps.dat file generated by SKIRT.
# The output plot is placed in the SKIRT-run's visualization directory.
def plottemperature(skirtrun):
    simulation = skirtrun.simulation()

    # setup the figure
    figure = plt.figure(figsize=(10,6))

    # load the mass and temperature data for all cells
    filepath = simulation.outfilepath("ds_celltemps.dat")
    M,T = np.loadtxt(arch.opentext(filepath), unpack=True)

    Mtot =  M.sum()
    if Mtot > 0:
        # calculate the average temperature and corresponding standard deviation
        Tavg = np.average(T, weights=M)
        Tstd = np.sqrt( (M*((T-Tavg)**2)).sum()/Mtot )
        skew = (M*((T-Tavg)**3)).sum()/Mtot/ Tstd**3
        kurtosis = (M*((T-Tavg)**4)).sum()/Mtot/ Tstd**4 - 3

        # plot the histogram
        Tmax = 40
        T[T>Tmax] = Tmax
        plt.hist(T.flatten(), weights=M, bins=Tmax, range=(0,Tmax), histtype='step', normed=True, log=True, color='r')

        # add vertical lines at the average temperature plus-min one sigma
        plt.vlines(Tavg, 1e-4, 1, colors='m', linestyle='solid')
        plt.vlines((Tavg+Tstd,Tavg-Tstd), 1e-4, 1, colors='m', linestyle='dashed')
        plt.vlines((Tavg+Tstd*skew,), 1e-4, 1, colors='b', linestyle='dotted')

        # add textual information about the statistics
        plt.text(Tmax-1, 0.2, " mean = {:.2f} K\n stddev = {:.2f} K\n skew = {:.3f}\n kurtosis = {:.3f}" \
                    .format(Tavg, Tstd, skew, kurtosis), horizontalalignment='right', backgroundcolor='w')

    # add axis labels and title
    plt.grid('on')
    plt.xlabel("T (K)", fontsize='medium')
    plt.ylabel("Dust Mass (normalized)", fontsize='medium')
    plt.ylim(1e-4, 1)
    plt.title("runid {} -- {}".format(skirtrun.runid(), skirtrun.prefix()), fontsize='medium')

    # save the figure
    plotpath = os.path.join(skirtrun.vispath(), skirtrun.prefix()+"_dust_temperature.pdf")
    plt.savefig(plotpath, bbox_inches='tight', pad_inches=0.25)
    plt.close()
    print "Created PDF plot file " + plotpath

# ----------------------------------------------------------------------