#!/bin/bash

pCa=(-7 -6.75 -6.5 -6.25 -6 -5.75 -5.5 -5.25 -5)

for pCa1 in ${pCa[@]}
do
	(./ALC_20210312.py --duration 100 --ID ALC_20210312_out_pCa_${pCa1}_init  --maxpressure 0 --pCa ${pCa1}   --ifinit init  && \
	 ./ALC_20210312.py --duration 200 --ID ALC_20210312_out_pCa_${pCa1}       --maxpressure 100 --pCa ${pCa1}  --ifinit r  ) &
done


