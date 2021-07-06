#!/bin/bash

# Modified from exec_20210521a.sh
# ALC_20210609.py allows Tref to be specified for the healthy tissue

Trefref=30

OutputDir="20210624"
nec=0.3
duration=200


# Vary necrotic Tref, keeping healthy Tref constant ###########################################################################

# Trefref=30

# for Trefnec in $(seq 0 10 $Trefref) 
# do
# 	simoutput="${OutputDir}/${i1}/Trefnec${Trefnec}"

# 	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

# 	./ALC_20210624.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Trefnec $Trefnec --Stress LandHumanStress  --fracnecrotic $nec --vd 0 --np 15

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


# Vary healthy Tref, keeping necrotic Tref constant ###########################################################################

for nec in $(seq 0.1 0.2 0.9)
do
for Trefnec in $(seq 0 5 30) 
do
for Trefref in $(seq 0 5 30) 
do
	simoutput="${OutputDir}/${i1}/fracnec${nec}_Trefref${Trefref}_Trefnec${Trefnec}"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210624.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Trefnec $Trefnec --Stress LandHumanStress  --fracnecrotic $nec --vd 0 --np 15

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
done
done


# # Test the case where there is no necrotic region. ##################################################################################

# Trefref=30

# 	simoutput="${OutputDir}/${i1}/SingleRegion"
# 	Trefnec=99999  # dummy value - doesn't get used

# 	./ALC_20210624_nonecregion.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Trefnec $Trefnec --Stress LandHumanStress  --fracnecrotic $nec --vd 0 --np 15    && \
# 	~/meshtool_new/meshtool/meshtool extract surface \
# 	-msh=$simoutput/block_i \
# 	-surf=$simoutput/basal_surf \
# 	-op=$simoutput/basal_dbc \
# 	-ofmt=vtk  && \
# 	~/meshtool/standalones/reaction_force \
# 	-msh=$simoutput/block_i \
# 	-surf=$simoutput/basal_surf \
# 	-stress=$simoutput/stressTensor.igb \
# 	-out=$simoutput/basal_force    







# ${OutputDir}/show_results.py

