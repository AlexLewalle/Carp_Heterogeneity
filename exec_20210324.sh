#!/bin/bash

Date="20210324"

pCa=(10.00 9.00 8.00 7.00 6.75  6.50 6.25 6.00 5.75 5.50 5.25 5.00 4.75 4.50 4.25 4.00)

duration=70
tend=$duration
siminit="none"


# simoutput="ALC20210324pCa7p00"
# ./ALC_20210324.py --duration 10 --ID $simoutput --pCa 7.00 --initfile "none"
# meshtool extract surface -msh=${simoutput}/block_i -surf=${simoutput}/basal_surf -op=${simoutput}/basal_dbc -ofmt=vtk
# ~/meshtool/standalones/reaction_force -msh=${simoutput}/block_i  -surf=${simoutput}/basal_surf -stress=${simoutput}/stressTensor.igb -out=${simoutput}/basal_force


# mkdir ${Date}
for pCa1 in ${pCa[@]}
do	
	simoutput="${Date}/ALC_${Date}_out_pCa_${pCa1}_init"  
	./ALC_${Date}.py --duration $tend --ID ${simoutput}  --pCa ${pCa1}    --initfile $siminit  
	meshtool extract surface \
	 -msh=${simoutput}/block_i \
	-surf=${simoutput}/basal_surf \
	  -op=${simoutput}/basal_dbc \
	-ofmt=vtk
	~/meshtool/standalones/reaction_force \
	 -msh=${simoutput}/block_i \
	-surf=${simoutput}/basal_surf \
	 -stress=${simoutput}/stressTensor.igb \
	    -out=${simoutput}/basal_force 
	siminit="${simoutput}/state.${tend}.0"      # Save steady state for next iteration
	let "tend += duration" 

done


