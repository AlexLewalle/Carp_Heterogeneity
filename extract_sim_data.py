#!/usr/bin/env python

import matplotlib.pyplot as plt
import numpy as np
import os
from carputils.carpio import igb

pCa_list = [-7, -6.75, -6.5, -6.25, -6, -5.75, -5.5, -5.25, -5] #[-7, -6.5] #['-7', '-5', '-3', '-1']

def extract_motion(SimOutput, Nodes, Times=-1):
	
	#os.system('/home/al12/Carp/bin/meshalyzer ' + SimOutput+'/block_i ' + SimOutput+'/Ca_i.igb ' + SimOutput+'/x.dynpt wedge_Cai.mshz')


	with open(SimOutput+'/block_i.pts', 'r') as MeshFile:
		NumNodes = int(MeshFile.readline())

	F = igb.IGBFile(SimOutput+'/x.dynpt')
	D = F.data()

	A = np.reshape(D, (-1,NumNodes,3) )
	print(A.shape)

	print(A[0,0,:])

	x = A[:,:,0]
	y = A[:,:,1]
	z = A[:,:,2]

	if Times==-1:
		y1 = y[:, Nodes]
	else:
		y1 = y[Times, Nodes]

	return y1







if __name__ == "__main__":
	
	for pCa1 in pCa_list:
		plt.figure(1) #(pCa1)
		plt.subplot(1,3,1)
		plt.plot(extract_motion('ALC_20210312_out_pCa_'+str(pCa1)+'_init', 1701),   label='pCai='+str(-pCa1))
		plt.legend(loc='upper left')
		
		plt.subplot(1,3,2)
		y = extract_motion('ALC_20210312_out_pCa_'+str(pCa1), 1701)
		y = y[0:51]
		plt.plot(y)
		y_low, y_high = plt.ylim()
		plt.subplot(1,3,1)
		plt.ylim((y_low,y_high))

		plt.subplot(1,3,3)
		i1 = np.where(np.array(y)>30000)[0][0]

		#import pdb; pdb.set_trace()
		
		print('pCa = {}: Initial length at index {}'.format(pCa1, i1))
		T = np.arange(0, 51)
		print( 'len y = {}'.format(len(y)))
		print( 'len T = {}'.format(len(T)))
		plt.plot(y[i1:min(len(y), len(T))], T[i1:min(len(y), len(T))])
		


	plt.show()
