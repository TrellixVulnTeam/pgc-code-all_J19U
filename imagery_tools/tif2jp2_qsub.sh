#!/bin/bash

#PBS -m n
#PBS -k oe
#PBS -j oe

module load gdal/2.1.3

src=$p1
dst=${src%%.tif}.jp2
localsrc=/local/${src##*/}
localdst=${localsrc%%.tif}.jp2

echo $src
echo $dst
echo $localsrc
echo $localdst
cmd="gdal_translate -of JP2OpenJPEG ${localsrc} ${localdst}"

if [ ! -e ${dst} ]
then
	cp -v $src $localsrc
	echo $cmd
	$cmd
	cp -v ${localdst} ${dst}
	rm -v $localsrc ${localdst}
fi

echo "done"
