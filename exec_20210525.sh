#!/bin/bash

# Modified from exec_20210421.sh to include bench for initialising the mechanics simulations.


OutputDir="20210525"
necmin=0.10
necmax=0.90
dnec=0.1
duration=80 #200


for nec1 in  0.01 #$(seq -f %.2f $necmin $dnec $necmax) 0.99
do
	simoutput="${OutputDir}/necr${nec1}"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210525.py --duration $duration --ID ${simoutput}  --EP TT2  --Stress LandHumanStress  --fracnecrotic $nec1 --vd 0 --np 15

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

# ${OutputDir}/show_results.py

