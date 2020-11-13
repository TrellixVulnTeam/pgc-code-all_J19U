#!/bin/bash
cd $PBS_O_WORKDIR

echo $PBS_JOBID
echo $PBS_O_HOST
echo $PBS_NODEFILE

echo gdal_translate -of $p1 $p2 $p3

echo Done.