#!/bin/bash

# Identical as exec_20210621.sh, except that this performs the same experiment with a 1D necrotic tissue distribution (i.e. by calling ALC_20210628.py)

Trefref=30

OutputDir="20210628"
fracnec=0.1

necr_s=13000 # um
# necr_r=1000 

duration=200

rmin=1000
rmax=10000
dr=1500

for i1 in $(seq 1 1 5)
do

for necr_r in $(seq $rmin $dr $rmax) 
do
	simoutput="${OutputDir}/${i1}/fracnec${fracnec}_s${necr_s}_r${necr_r}"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210628.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Stress LandHumanStress  --fracnecrotic $fracnec --necr_s $necr_s --necr_r $necr_r --randseed $i1 --vd 0 --np 15

	mv NecrElem_frac${fracnec}_s${necr_s}_r${necr_r}.regele ${simoutput}

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


# ${OutputDir}/show_results.py

