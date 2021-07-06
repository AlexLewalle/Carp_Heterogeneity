#!/bin/bash

MyDate="20210324"
pCa=(7.00) # 6.75  6.50 6.25 6.00 5.75 5.50 5.25 5.00 4.75 4.50 4.25 4.00)

magnitude=50.

for pCa1 in ${pCa[@]}
do
	(simoutput="${MyDate}/ALC_${MyDate}_out_pCa_${pCa1}_init" && \
	./ALC_20210324.py --duration 10 --ID $simoutput  --maxstretch $magnitude --pCa ${pCa1}   --ifinit init  && \
	meshtool extract surface \
	 -msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	  -op=$simoutput/basal_dbc \
	-ofmt=vtk && \
	~/meshtool/standalones/reaction_force \
	 -msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	-stress=$simoutput/stressTensor.igb \
	    -out=$simoutput/basal_force  )   # && \
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


