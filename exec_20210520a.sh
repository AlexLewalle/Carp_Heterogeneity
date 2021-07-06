#!/bin/bash

# Modified from exec_20210421.sh to include bench for initialising the mechanics simulations.


OutputDir="20210520/a"
pCamax=7
pCamin=5
dpCa=-0.1
duration=500




simendtime=$duration

for pCa1 in $(seq -f %.2f $pCamax $dpCa $pCamin)
do
	simoutput="${OutputDir}/pCa${pCa1}"
	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000
	echo $pCa1
	if [[ $pCa1==7.00 ]]
	then
		./ALC_20210520.py --duration $simendtime --ID $simoutput  --pCa ${pCa1}    --vd 0 --np 15  --savechkpt 1
	else
		./ALC_20210520.py --duration $simendtime --ID $simoutput  --pCa ${pCa1}    --vd 0 --np 15  --savechkpt 1 --loadchkpt 1
	fi
	simendtime=$(($simendtime+$duration))
done

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
	


# ./${OutputDir}/show_results.py

