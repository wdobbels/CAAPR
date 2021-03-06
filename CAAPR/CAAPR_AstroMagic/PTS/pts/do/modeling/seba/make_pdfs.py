#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.make_pdfs

# -----------------------------------------------------------------

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rc
rc('text', usetex=True)
import glob
import os
from scipy import interpolate
from scipy import integrate


def main():

    correction = 0.6741981381 # Correction factor for dust mass. Simulations were run with the incorrect dust mass
    # degrees of freedom = datapoints - free parameters - 1
    dof = 9.-3.-1.
    outpath = "modelChecks/"
    inpath  = "SKIRTrun/models/"
    
    chi2list1 = outpath+"iteration3_J14/chi2list_weighted.dat"
    chi2list2 = outpath+"iteration4_J14/chi2list_weighted.dat"
    parList1  = inpath+"iteration3_J14/parameters.dat"
    parList2  = inpath+"iteration4_J14/parameters.dat"
    


    params1, probabilities1 = getPDFs(chi2list1,parList1,dof)
    params2, probabilities2 = getPDFs(chi2list2,parList2,dof)

    # combine non-overlapping parameter ranges of both iterations
    params1[2] = params1[2] + params2[2]
   
    MdustProb  = np.array(probabilities1[0]) + np.array(probabilities2[0])
    FyoungProb = np.array(probabilities1[1]) + np.array(probabilities2[1])
    FionizedProb = np.array(probabilities1[2] + probabilities2[2])

    MdustProb = MdustProb / np.sum(MdustProb)
    FyoungProb = FyoungProb / np.sum(FyoungProb)
    FionizedProb = FionizedProb / np.sum(FionizedProb)
    
    if 1:
        fig  = plt.figure(figsize=(10,4))
        plotPDFs(fig, params1,MdustProb, FyoungProb, FionizedProb, correction)
        fig.savefig(outpath+"plotPDFs.pdf",format='pdf')

    if 0:
        "THIS DOES NOT WORK!"
        "Need to interpolate somehow because the 3 parameter vectors have different lengths..."
        fig  = plt.figure(figsize=(10,4))
        plotContours(fig, params1, MdustProb, FyoungProb, FionizedProb, correction)
        fig.savefig(outpath+"plotChi2Contours.pdf",format='pdf')


def findPercentile(parameter, probability, percentile):

    npoints = 10000
    interpfunc = interpolate.interp1d(parameter,probability, kind='linear')
    
    parRange = np.linspace(min(parameter),max(parameter),npoints)
    interProb = interpfunc(parRange)
    
    
    cumInteg = np.zeros(npoints-1)

    for i in range(1,npoints-1):
        cumInteg[i] = cumInteg[i-1] + (0.5*(interProb[i+1] + interProb[i]) * (parRange[i+1] - parRange[i]))

    cumInteg = cumInteg / cumInteg[-1]
    idx = (np.abs(cumInteg-percentile/100.)).argmin()

    return parRange[idx]


def plotContours(fig, params,MdustProb, FyoungProb, FionizedProb, correction):
    
    MdustScale     = 1.e7 # in 1e7 Msun
    LyoungScale    = 3.846e26 / (1.425e21*0.153) * 1e8 # in 1e8 Lsun
    LionizingScale = 3.53e14 # in Msun/yr
    
    MdustBestFit    = 69079833.3333     / MdustScale * correction
    FyoungBestFit   = 1.69488344353e+15 / LyoungScale
    FionizedBestFit = 3.53e+14          / LionizingScale

    p1 = MdustProb[None,:]*FionizedProb[:,None]
    p2 = FyoungProb[None,:]*FionizedProb[:,None]
    p3 = MdustProb[None,:]*FyoungProb[:,None]
    
    locplot = [[0.07,0.15,0.305,0.81],[0.375,0.15,0.305,0.81],[0.68,0.15,0.305,0.81]]
    
    fig_a = plt.axes(locplot[0])
    fig_a.set_ylabel('SFR $[M_\odot \mathrm{yr}^{-1} ]$',fontsize=18)
    fig_a.set_xlabel('M$_\mathrm{dust} [10^7 M_\odot]$',fontsize=18)
    x = np.array(params[0])/MdustScale * correction
    y = np.array(params[2])/LionizingScale
    fig_a.imshow(p1, cmap='gray', interpolation=None,
               origin='lower', extent=[x[0],x[-1],y[0],y[-1]] )
    fig_a.set_aspect('auto')

    fig_b = plt.axes(locplot[1])
    fig_b.set_ylabel('SFR $[M_\odot \mathrm{yr}^{-1} ]$',fontsize=18)
    fig_b.set_xlabel('F$^{FUV}_\mathrm{young} [10^8 L_\odot]$',fontsize=18)
    x = np.array(params[1])/LyoungScale
    y = np.array(params[2])/LionizingScale
    fig_b.imshow(p2, cmap='gray', interpolation=None,
                 origin='lower', extent=[x[0],x[-1],y[0],y[-1]] )
    fig_b.set_aspect('auto')

    fig_c = plt.axes(locplot[2])
    fig_c.set_ylabel('F$^{FUV}_\mathrm{young} [10^8 L_\odot]$',fontsize=18)
    fig_c.set_xlabel('M$_\mathrm{dust} [10^7 M_\odot]$',fontsize=18)
    x = np.array(params[0])/MdustScale * correction
    y = np.array(params[1])/LyoungScale
    fig_c.imshow(p3, cmap='gray', interpolation=None,
                 origin='lower', extent=[x[0],x[-1],y[0],y[-1]] )
    fig_c.set_aspect('auto')


def plotPDFs(fig, params,MdustProb, FyoungProb, FionizedProb, correction):
    
    MdustScale     = 1.e7 # in 1e7 Msun
    LyoungScale    = 3.846e26 / (1.425e21*0.153) * 1e8 # in 1e8 Lsun
    #LionizingScale = 3.53e14 # in Msun/yr
    LionizingScale = 3.846e26 / (1.425e21*0.153) * 1e8 # in 1e8 Lsun

    
    MdustBestFit    = 69079833.3333     / MdustScale * correction
    FyoungBestFit   = 1.69488344353e+15 / LyoungScale
    FionizedBestFit = 3.53e+14          / LionizingScale
    
    Mdust_50 = findPercentile(params[0],MdustProb, 50.) / MdustScale * correction
    Mdust_16 = findPercentile(params[0],MdustProb, 16.) / MdustScale * correction
    Mdust_84 = findPercentile(params[0],MdustProb, 84.) / MdustScale * correction
    
    Fyoung_50 = findPercentile(params[1],FyoungProb, 50.) / LyoungScale
    Fyoung_16 = findPercentile(params[1],FyoungProb, 16.) / LyoungScale
    Fyoung_84 = findPercentile(params[1],FyoungProb, 84.) / LyoungScale
    
    Fionized_50 = findPercentile(params[2],FionizedProb, 50.) / LionizingScale
    Fionized_16 = findPercentile(params[2],FionizedProb, 16.) / LionizingScale
    Fionized_84 = findPercentile(params[2],FionizedProb, 84.) / LionizingScale
    
    locplot = [[0.07,0.15,0.305,0.81],[0.375,0.15,0.305,0.81],[0.68,0.15,0.305,0.81]]

    fig_a = plt.axes(locplot[0])
    fig_a.set_ylabel('Probability',fontsize=18)
    fig_a.set_xlabel('M$_\mathrm{dust}\, [10^7 M_\odot]$',fontsize=18)
    abcissa = np.array(params[0])/MdustScale * correction
    width = 0.3
    fig_a.bar(abcissa-0.5*width, MdustProb,width=width, color='g',ec='k')
    fig_a.plot([MdustBestFit,MdustBestFit],[0,1],'k--')
    fig_a.plot([Mdust_50,Mdust_50],[0,1],'r--')
    fig_a.set_xlim(2.5,6.4)
    fig_a.set_ylim(0,0.4)

    fig_b = plt.axes(locplot[1])
    fig_b.set_ylabel('Probability',fontsize=18)
    fig_b.set_xlabel('$\lambda L_\lambda^{\mathrm{young}} \, [10^8 L_\odot]$',fontsize=18)
    abcissa = np.array(params[1])/LyoungScale
    width = 1.05
    fig_b.bar(abcissa-0.5*width, FyoungProb,width=width, color='g',ec='k')
    fig_b.plot([FyoungBestFit,FyoungBestFit],[0,1],'k--')
    fig_b.plot([Fyoung_50,Fyoung_50],[0,1],'r--')
    fig_b.set_xlim(6,19.5)
    fig_b.set_ylim(0,0.4)
    fig_b.get_yaxis().set_visible(False)

    fig_c = plt.axes(locplot[2])
    fig_c.set_ylabel('Probability',fontsize=18)
    fig_c.set_xlabel('$\lambda L_\lambda^{\mathrm{ion.}} \, [10^8 L_\odot]$',fontsize=18)
    abcissa = np.array(params[2])/LionizingScale
    width = 0.10
    fig_c.bar(abcissa-0.5*width, FionizedProb,width=width, color='g',ec='k')
    fig_c.plot([FionizedBestFit,FionizedBestFit],[0,1],'k--')
    fig_c.plot([Fionized_50,Fionized_50],[0,1],'r--')
    fig_c.set_xlim(0.001,2.9)
    fig_c.set_ylim(0,0.4)
    fig_c.get_yaxis().set_visible(False)

    print 'Parameter  50th        16th        84th percentile'
    print 'Mdust     '+str(Mdust_50)+'  '+str(Mdust_16)+'  '+str(Mdust_84)
    print 'Fyoung    '+str(Fyoung_50)+'  '+str(Fyoung_16)+'  '+str(Fyoung_84)
    print 'Fionized  '+str(Fionized_50)+'  '+str(Fionized_16)+'  '+str(Fionized_84)
    print '\nThis corresponds to the following input parameters for Mdust, Fyoung and Fionized:\n'
    print str(Mdust_50*MdustScale)+'    '+str(Fyoung_50*LyoungScale)+'    '+str(Fionized_50*LionizingScale)


def getPDFs(chi2file, parfile,dof):
    
    input = np.loadtxt(chi2file)
    chi2list = input[:,1]/dof
    
    probabilities = np.exp(-0.5*chi2list)

    params = []
    data = open(parfile)
    for line in data:
        if line[0] != '#':
            strings = line.split()
            params.append(map(float, strings[1:4]))

    params = np.array(params)

    parSets = [[]]
    parSetProbabilities = [[]]
    for i in range(0, len(params[0,:])):
        parameter = params[:,i]
        parset = list(set(parameter))
        parset.sort()

        setProbabilities = []
        for j in range(0,len(parset)):
            idx = (parameter == parset[j])
            setProbabilities.append(np.sum(probabilities[idx]))

        parSets.append(parset)
        parSetProbabilities.append(setProbabilities)

    return parSets[1:], parSetProbabilities[1:]

if __name__ == '__main__':
    main()