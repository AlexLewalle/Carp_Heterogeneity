#!/bin/bash

# Modified from exec_20210421.sh to include bench for initialising the mechanics simulations.


OutputDir="20210520"
pCamax=7
pCamin=5
dpCa=-0.1
duration=100


for pCa1 in $(seq -f %.2f $pCamax $dpCa $pCamin)
do
	simoutput="${OutputDir}/pCa${pCa1}"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210520.py --duration $duration --ID $simoutput  --pCa ${pCa1}    --vd 0 #--np 15

	~/meshtool_new/meshtool/meshtool extract surface \
	-msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	-op=$simoutput/basal_dbc \
	-ofmt=vtk 
	~/meshtool/standalones/reaction_force \
	-msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	-stress=$simoutput/stressTensor.igb \
	-out=$simoutput/basal_force    
	
done

# ./${OutputDir}/show_results.py

