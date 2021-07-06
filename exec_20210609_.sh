#!/bin/bash

# Modified from exec_20210521a.sh
# ALC_20210609.py allows Tref to be specified for the healthy tissue

Trefref=30

OutputDir="20210609/Trefref_${Trefref}"
necmin=0.00
necmax=0.90
dnec=0.05
duration=200


# for i1 in 1 2 3 4 5
# do

# for nec1 in  $(seq -f %.2f $necmin $dnec $necmax) 
# do
# 	simoutput="${OutputDir}/${i1}/necr${nec1}"

# 	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

# 	./ALC_20210609.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Stress LandHumanStress  --fracnecrotic $nec1 --vd 0 --np 15

# 	~/meshtool_new/meshtool/meshtool extract surface \
# 	-msh=$simoutput/block_i \
# 	-surf=$simoutput/basal_surf \
# 	-op=$simoutput/basal_dbc \
# 	-ofmt=vtk 
# 	~/meshtool/standalones/reaction_force \
# 	-msh=$simoutput/block_i \
# 	-surf=$simoutput/basal_surf \
# 	-stress=$simoutput/stressTensor.igb \
# 	-out=$simoutput/basal_force    
	
# done

# done

################################# Tref #################################################

for Tref1 in 30 # $(seq -f %.2f $Trefref -5 0) 
do
	simoutput="${OutputDir}/Tref${Tref1}_"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210609_.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Tref1 --Stress LandHumanStress  --fracnecrotic 0.0 --vd 0 --np 15

	~/meshtool_new/meshtool/meshtool extract surface \
	-msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \                     # output surface 
	-op=$simoutput/basal_dbc \
	-ofmt=vtk 
	~/meshtool/standalones/reaction_force \
	-msh=$simoutput/block_i \
	-surf=$simoutput/basal_surf \
	-stress=$simoutput/stressTensor.igb \
	-out=$simoutput/basal_force    
	
done



# ${OutputDir}/show_results.py

