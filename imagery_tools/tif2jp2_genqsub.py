#tif2jp2_genqsub.py

import os,sys,string,subprocess

if len(sys.argv) != 3:
    print "Script requires 2 arguments (srcdir, qsubscript)"
else:
    srcdir = os.path.abspath(sys.argv[1])
    qsubscript = sys.argv[2]
    print srcdir
    print qsubscript

    for root,dirs,files in os.walk(srcdir):
        for f in files:
            #print f
            if f.endswith('.tif'):
                ofp = os.path.join(root,f[:-4]+".jp2")
                if not os.path.isfile(ofp):
                
                    cmd = 'qsub -l walltime=4:00:00 -l nodes=1:ppn=4 -v p1=%s %s' %(os.path.join(root,f),qsubscript)
                    print cmd
                    # subprocess.call(cmd,shell=True)

