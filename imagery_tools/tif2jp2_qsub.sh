#!/bin/bash

FS="$@"
for F in $FS
do

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
