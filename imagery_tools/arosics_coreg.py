from pathlib import Path

import arosics

prj_dir = Path(r'V:\pgc\data\scratch\jeff\ms\2020aug22')
dems_dir = prj_dir / 'dems' / 'aoi1'
img_dir = prj_dir / 'img' / 'aoi1'

# Imagery is reference -> move everything to it
im_ref = img_dir / 'WV02_20180403212306_103001007A45AA00_18APR03212306-P1BS-502128082080_01_P008_u16ns3413_aoi1.tif'
# Ortho is target -> move it to imagery
im_tar = dems_dir / 'WV02_20180403_103001007A66E000_103001007A45AA00_2m_lsf_seg1_ortho_aoi1.tif'
dem_tar = dems_dir / 'WV02_20180403_103001007A66E000_103001007A45AA00_2m_lsf_seg1_dem_aoi1.tif'

global_ortho = dems_dir / 'global' / '{}_global2.tif'.format(im_tar.stem)
local_ortho = dems_dir / 'local' / '{}_local.tif'.format(im_tar.stem)
global_dem = dems_dir / 'global' / '{}_global.tif'.format(dem_tar.stem)

# Global coreg
cr = arosics.COREG(str(im_ref), str(im_tar), max_shift=100,
                   path_out=str(global_ortho))
ss = cr.calculate_spatial_shifts()
cr.correct_shifts()

# Apply to DEM
deshifter_kwargs = {
    'path_out': str(global_dem),

}

arosics.DESHIFTER(str(dem_tar), cr.coreg_info, **deshifter_kwargs).correct_shifts()


# Try local coreg
# kwargs = {
#     'grid_res': 25,
#     'window_size': (250,250),
#     'path_out': str(local_ortho),
#     'projectDir': str(prj_dir),
#     'q': False
# }
# crl = arosics.COREG_LOCAL(str(im_ref), str(im_tar), **kwargs)
# crl.correct_shifts()



'''
Try applying to other layers: 
ref = imagery
target = ortho

DESHIFTER to also align DEMs
'''
