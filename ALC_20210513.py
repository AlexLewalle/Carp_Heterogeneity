#!/usr/bin/env python

import os
import numpy as np
import matplotlib.pyplot as plt


NumStim = 1 #10
Tfinal = 250 #NumStim * 1000

StressModel = 'LandHumanStress'


def RunpCa(pCa=7.0, StressModel='LandStress'):
	CaiClamp = 0
	CaiSET = 10**-pCa * 1000
	caistring = "CaiClamp=1" if CaiClamp==1 else f"CaiSET={CaiSET},CaiClamp=0" 
	
	OutputDir = '20210513/'
	OutputTrace = 'Trace_0.dat'
	OutputSV = 'TT2_Cai_LandStress_{}ms.sv'.format(Tfinal)
	cmd=f"bench --load-module ~/Carp/MyModels/TT2_Cai.so --numstim {NumStim}" + f" --imp-par=\"{caistring}\" " +  f"--dt 0.01 --stim-curr 50 --bcl 1000 -F '{OutputSV}' -O S {Tfinal} --plug-in {StressModel} " 
	print(cmd)
	os.system(cmd)
	# cmd = "bench --load-module ~/Carp/MyModels/TT2_Cai.so --numstim 3 --imp-par CaiClamp=1 --dt 0.01 --stim-curr 50 --bcl 1000 -F '20210513/TT2_Cai_LandStress_3000msTEST.sv' -S 3000 --plug-in LandStress"

fig, ax = plt.subplots(nrows=1, ncols=2)

pCa_list = np.arange(7,4.75,-0.05) #np.arange(7, 4.75, -0.25) # [7, 6.75, 6.5, 6.25, 6, 5.75, 5.5, 5.25, 5] 

Fss = []
for pCa in pCa_list:
	RunpCa(pCa)
	# Data = np.loadtxt('Trace_0.dat')
	# ax[0,0].plot(Data[:,0], Data[:,3], label=f"pCa={pCa}")
	# ax[0,0].set_ylabel('[Ca$^{2+}$]')
	Data = np.loadtxt('BENCH_REG.txt')
	ax[0].plot(Data[:,0], Data[:,4])
	ax[0].set_ylabel('Tension')
	Fss.append([Data[-1,4]])

# ax[0,0].elgend(loc=(0))
ax[1].plot(pCa_list, Fss)
ax[1].set_ylabel('Tension')
ax[1].set_xlabel('pCa')
ax[1].set_title(StressModel)
ax[1].invert_xaxis()
# fig.delaxes(ax[0,1])
fig.tight_layout()
plt.show()