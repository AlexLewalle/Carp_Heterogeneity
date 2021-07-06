#!/bin/bash

pCa=(6.00)    #(7.00 6.75 6.50 6.25 6.00)
magnitude=50.

for pCa1 in ${pCa[@]}
do
	(simoutput="20210330/ALC_20210330_out_pCa_${pCa1}" && \
	 simoutput_init="${simoutput}_init" && \
	./ALC_20210330.py --duration 10 --ID $simoutput_init  --maxstretch $magnitude --pCa ${pCa1}   --ifinit init  && \
	meshtool extract surface \
	 -msh=$simoutput_init/block_i \
	-surf=$simoutput_init/basal_surf \
	  -op=$simoutput_init/basal_dbc \
	-ofmt=vtk && \
	~/meshtool/standalones/reaction_force \
	 -msh=$simoutput_init/block_i \
	-surf=$simoutput_init/basal_surf \
	 -stress=$simoutput_init/stressTensor.igb \
	    -out=$simoutput_init/basal_force  ) &  # && \
	
done


