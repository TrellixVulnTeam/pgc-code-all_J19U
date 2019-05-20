# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""

def read_ids(txt_file, sep=None):
    '''reads ids, one per line, from a text file and returns a list of ids'''
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            if sep:
                # Assumes id is first
                the_id = line.split(sep)[0]
                the_id = the_id.strip()
            else:
                the_id = line.strip()
            ids.append(the_id)
    return ids


def write_ids(ids, out_path, header=None):
    with open(out_path, 'w') as f:
        if header:
            f.write('{}\n'.format(header))
        for each_id in ids:
            f.write('{}\n'.format(each_id))


def date_words(date=None, today=False):
    '''get todays date and convert to '2019jan07' style for filenaming'''
    from datetime import datetime, timedelta
    if today == True:
        date = datetime.now() - timedelta(days=1)
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    year = date.strftime('%Y')
    month = date.strftime('%b').lower()
    day = date.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date

#
#def ge_id_to_dg(ge_ids, sensor, only_orderable=False, return_not_found=False):
#    '''
#    takes a list of Geo-Eye archive ids and converts them to Digital Globe ids
#    ge_ids:    list of old ids
#    sensor:    IK01 or GE01
#    '''
#    from query_danco import query_footprint
#    # Look up table names on danco
#    luts = {
#            'GE01': 'index_dg_catalogid_to_ge_archiveid_ge01',
#            'IK01': 'index_dg_catalogid_to_ge_archiveid_ik'
#            }
#    
#    # Verify sensor
#    if sensor in luts:
#        pass
#    else:
#        print('{} look up table not found. Sensor must be in {}'.format(sensor, luts.keys()))
#    
#    # Deal with orderable
#    if only_orderable == True:
#        where = "orderable = 'Yes'"
#    else:
#        where = None
#    ## Look up old value
#    lut = query_footprint(layer=luts[sensor], where=where, table=True)
#    lut.set_index('crssimageid', inplace=True)
#    
#    dg_ids = []
#    not_transfered = []
#    
#    for ge_id in ge_ids:
#        dg_id = lut.get_value(ge_id, 'catalog_identifier')
#        # If there are multiple matches, append each seperately 
#        if len(dg_id > 1):
#            for i in dg_id:
#                        
#                if dg_id == 'Not Transfered':
#                    not_transfered.append(ge_id)
#                else:
#                    dg_ids.append(dg_id)
#        else:
#            if dg_id == 'Not Transfered':
#                not_transfered.append(ge_id)
#            else:
#                dg_ids.append(dg_id)
#    
#    # Print results
#    print('DG catalogids found: {}\nNote: some archive ids may have more than one match.'.format(len(dg_ids)))
#    print("Not transfered' ids found: {}".format(len(not_transfered)))
#
#    if return_not_found:
#        return dg_ids, not_transfered
#    else:
#        return dg_ids


def archive_id_lut(sensor):

    # Look up table names on danco
    luts = {
            'GE01': 'index_dg_catalogid_to_ge_archiveid_ge01',
            'IK01': 'index_dg_catalogid_to_ge_archiveid_ik'
            }
    
    # Verify sensor
    if sensor in luts:
        pass
    else:
        print('{} look up table not found. Sensor must be in {}'.format(sensor, luts.keys()))
    
    lu_df = query_footprint(layer=luts[sensor], table=True)
    lu_dict = dict(zip(lu_df.crssimageid, lu_df.catalog_identifier))

    return lu_dict    
    

    
    
    
    
    
    
    
    
    