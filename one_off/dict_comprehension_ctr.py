# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 15:42:07 2019

@author: disbr007
"""
import os

src = r'C:\temp'
groups = True
dstdir = r'C:\temp\icesat'

for root,dirs,files in os.walk(src):
    for f in files:
        if f.endswith(('.txt', '.tot')):
            srcfp = os.path.join(root,f)
            regfp = srcfp.replace('dem.tif','reg.txt').replace('matchtag.tif','reg.txt').replace('ortho.tif','reg.txt')
            if not os.path.isfile(regfp):
                print('no reg')
#                logger.info("No regfile found for {}".format(srcfp))
            else:
                if dstdir:
                    if groups:
                        subdir = os.path.basename(os.path.split(srcfp)[0])
                    else:
                        subdir = ''
                    outdir = os.path.join(dstdir, subdir)
                    if not os.path.exists(outdir):
                        os.mkdir(outdir)
                    dstfp = "{}_reg.tif".format(outdir, os.path.basename(os.path.splitext(srcfp)[0]))
                else:
                    dstfp = "{}_reg.tif".format(os.path.splitext(srcfp)[0])
                    
            print(dstfp)
            
            
                    if args.groups:
                        subdir = os.path.basename(os.path.split(srcfp)[0])
                    else:
                        subdir = ''
                    outdir = os.path.join(args.dstdir, subdir)
                    if not os.path.exists(outdir):
                        os.mkdir(outdir)
                    dstfp = "{}_reg.tif".format(os.path.join(outdir, os.path.basename(os.path.splitext(srcfp)[0])))