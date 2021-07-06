#!/bin/bash

# Modified from exec_20210521a.sh
# ALC_20210609.py allows Tref to be specified for the healthy tissue

Trefref=30

OutputDir="20210623"
fracnec=0.1

necr_s=13000 # um
# necr_r=1000 


duration=200

rmin=1000
rmax=10000
dr=1500

amin=1.0
amax=1.5
da=0.1

for irun in 1 # $(seq 1 1 5)
do

for necr_a in $(seq -f %.1f $amin $da $amax)
do

for necr_r in $(seq $rmin $dr $rmax) 
do
	simoutput="${OutputDir}/${irun}/fracnec${fracnec}_s${necr_s}_r${necr_r}_a${necr_a}"

	# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

	./ALC_20210623.py --duration $duration --ID ${simoutput}  --EP TT2_Cai  --pCa 5.0 --Tref $Trefref --Guccione_necr_a ${necr_a} --Stress LandHumanStress  --fracnecrotic $fracnec --necr_s $necr_s --necr_r $necr_r --randseed $irun --vd 0 --np 15

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

done
# ${OutputDir}/show_results.py

