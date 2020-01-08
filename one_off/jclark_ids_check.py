# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 09:54:10 2020

@author: disbr007
"""
import os

from id_parse_utils import read_ids, compare_ids
from query_danco import query_footprint

prj_dir = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056\prj_files\ids_check'
req_ids = os.path.join(prj_dir, r'requested_ids_unique.txt')
mfp_ids = os.path.join(prj_dir, r'selected_ids_mfp_selection.txt')

req_u, mfp_u, com = compare_ids(req_ids, mfp_ids, write_path=os.path.join(prj_dir))


missing_ids = query_footprint('index_dg', 
                              where="""catalogid IN ({})""".format(str(list(req_u))[1:-1]))

missing_dg = req_u - set(list(missing_ids.catalogid))
