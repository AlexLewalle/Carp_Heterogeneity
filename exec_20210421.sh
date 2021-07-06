#!/bin/bash

OutputDir="20210421/free"
pCamax=7
pCamin=5
dpCa=-0.25
duration=70


for pCa1 in $(seq -f %.2f $pCamax $dpCa $pCamin)
do
	(simoutput="${OutputDir}/pCa${pCa1}" && \
	./ALC_20210421.py --duration $duration --ID $simoutput  --pCa ${pCa1}   && \
	meshtool extract surface \
	 -msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	  -op=$simoutput/basal_dbc \
	-ofmt=vtk && \
	~/meshtool/standalones/reaction_force \
	 -msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	 -stress=$simoutput/stressTensor.igb \
	    -out=$simoutput/basal_force  )  # && \
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

# ./${OutputDir}/show_results.py

