#!/bin/bash

#PBS -m n
#PBS -k oe
#PBS -j oe

module load gdal/2.1.3

src=$p1
dst=$p2
fmt=$p3

echo $src
echo $dst

cmd="gdal_translate -of ${fmt} ${src} ${dst}"

if [ ! -e ${dst} ]
then
	echo $cmd
	$cmd
fi

echo "done"
