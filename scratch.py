from misc_utils.id_parse_utils import read_ids, write_ids, mfp_ids
from selection_utils.db import Postgres
from tqdm import tqdm
import numpy as np

print('loading pgc ids...')
tbl = 'mfp_v7'
sql = "SELECT catalog_id FROM {} WHERE status <> 'offline'".format(tbl)
with Postgres('sandwich-pool.dgarchive') as db_src:
    pgc_ids_dgarchive = db_src.sql2df(sql)
    pgc_ids = set(list(pgc_ids_dgarchive['catalog_id']))

print('reading nasa ids...')
nasa_ids = set(read_ids(r'E:\disbr007\imagery_orders\NASA_order_2020dec17_'
                    r'adapt_replenish\SSAr2.2_all_zones_missing_ntflist_ids.txt'))

print('finding nasa ids not at PGC...')
# reorder = []
# for n in tqdm(nasa_ids):
#     if n not in set(list(pgc_ids_dgarchive['catalog_id'])):
#         reorder.append(n)

# reorder = [n for n in nasa_ids if n not in set(list(pgc_ids_dgarchive['catalog_id']))]

reorder = nasa_ids.difference(pgc_ids)
print('writing ids...')
write_ids(reorder, r'E:\disbr007\imagery_orders\NASA_order_2020dec17_'
                    r'adapt_replenish\reorder_ids.txt')