#!/bin/bash

# Modified from exec_20210421.sh to include bench for initialising the mechanics simulations.


OutputDir="20210521/1"
duration=150


simoutput="${OutputDir}"

# bench --load-module ~/Carp/MyModels/TT2_Cai.so --plug-in LandHumanStress --numstim 1 --imp-par='CaiClamp=0,CaiSET=${pCa1}' --dt 0.01 --stim-curr 100 --bcl 1000

./ALC_20210521.py --duration $duration --ID $simoutput  --EP TT2  --Stress LandHumanStress  --vd 0 --np 15

meshalyzer ${simoutput}/block_i ${simoutput}/x.dynpt ${simoutput}/Tension.igb wedge_tension.mshz

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

