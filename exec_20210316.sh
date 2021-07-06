#!/bin/bash

pCa=(7 6.75 6.5 6.25 6 5.75 5.5 5.25 5)
magnitude=50.

for pCa1 in ${pCa[@]}
do
	(simoutput="20210316/ALC_20210316_out_pCa_${pCa1}" && \
	 simoutput_init="${simoutput}_init" && \
	./ALC_20210316.py --duration 70 --ID $simoutput_init  --maxstretch $magnitude --pCa ${pCa1}   --ifinit init  && \
	meshtool extract surface \
	 -msh=$simoutput_init/block_i \
	-surf=$simoutput_init/basal_surf \
	  -op=$simoutput_init/basal_dbc \
	-ofmt=vtk && \
	~/meshtool/standalones/reaction_force \
	 -msh=$simoutput_init/block_i \
	-surf=$simoutput_init/basal_surf \
	 -stress=$simoutput_init/stressTensor.igb \
	    -out=$simoutput_init/basal_force  ) & # && \
	# ./ALC_20210316.py --duration 200 --ID $simoutput  --maxstretch $magnitude --pCa ${pCa1}   --ifinit r &&
	# meshtool extract surface \
	#  -msh=$simoutput/block_i \
	# -surf=$simoutput/basal_surf \
	#   -op=$simoutput/basal_dbc \
	# -ofmt=vtk && \
	# ~/meshtool/standalones/reaction_force \
	#  -msh=$simoutput/block_i \
	# -surf=$simoutput/basal_surf \
	#  -stress=$simoutput/stressTensor.igb \
	#     -out=$simoutput/basal_force  ) &
done


