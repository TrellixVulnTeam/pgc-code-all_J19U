#!/bin/bash

#PBS -l walltime=40:00:00,nodes=1:ppn=2
#PBS -m n
#PBS -k oe
#PBS -j oe

cd $PBS_O_WORKDIR

echo $PBS_JOBID
echo $PBS_O_HOST
echo $PBS_NODEFILE

echo $p1 $p2 $p3 $p4 $p5 $p6 $p7 $p8 $p9
python /mnt/pgc/data/scratch/jeff/code/pgc-code-all/obia_utils/otb_lsms.py $p1 $p2 $p3 $p4 $p5 $p6 $p7 $p8 $p9

echo Done