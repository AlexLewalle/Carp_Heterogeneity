#!/usr/bin/env python

# Generate random element selection files for 


import ALCarpLib as ALC
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import inspect
import os

print(os.path.abspath(inspect.getfile(ALC.MakePoissonClusters)))

fracnec = 0.1
s = 15000
r = [1000, 3000, 10000]

fig, ax = plt.subplots(nrows=1, ncols=len(r))
plt.ion()
MyDir = '/home/al12/Carp/Heterogeneity/20210609/Trefref_30/1/necr0.25/'
# MyDir = '/home/al12local/Carp2/Data/necr0.00/'
MeshBase = MyDir + 'block_i'

A = np.loadtxt(MeshBase+'.pts', skiprows=1)
E = pd.read_csv(MeshBase+'.elem', header=0, delimiter='\s+', names=['trash','a','b','c','d','trash2'])
E = E.drop(['trash', 'trash2'], 'columns')
E = E.values.tolist() 

Lx = max(A[:,0]) - min(A[:,0])
Ly = max(A[:,1]) - min(A[:,1]) 
Lz = max(A[:,2]) - min(A[:,2])
num_parents = (Lx*Ly*Lz)/s**3   #s = (Lx*Ly*Lz/num_parents) **(1/3)

# import pdb; pdb.set_trace()

for i1, r1 in enumerate(r):

    j_nec = ALC.MakePoissonClusters(MyDir+'block_i', fracnec, s, r1, OutputFile=f'/home/al12/Carp/Heterogeneity/NecrElem_frac{fracnec}_s{s}_r{r1}.regele', randseed=10)
    COM=[]
    for i2, j_nec1 in enumerate(j_nec):
        com1 = (A[E[j_nec1][0],:] + A[E[j_nec1][1],:] + A[E[j_nec1][2],:] + A[E[j_nec1][3],:] )/4
        COM.append(com1.tolist())
    COM_ = np.array(COM)

    plt.ion()
    ax[i1].plot(COM_[:,0], COM_[:,1], '.', markersize=1)
    ax[i1].set(xlim=(-Lx/2,+Lx/2), ylim=(-Ly/2,+Ly/2))
    ax[i1].set_aspect('equal', 'box')
    ax[i1].set_title('r={}'.format(r1))
    
fig.tight_layout()
plt.show(block=True)