from selection_utils.db_utils import Postgres, generate_sql
from selection_utils.danco_utils import xtrack_noh_sql, create_cid_noh_where


xtrack_layer = 'dg_imagery_index_xtrack_cc20'
perc_ovlp = 'perc_ovlp'
limit = 75_000

with Postgres('danco.footprint') as db:
    cols = db.get_layer_columns(xtrack_layer)
    # sql = xtrack_noh_sql()
    print(cols)
    where = create_cid_noh_where(['catalogid1', 'catalogid2'], xtrack_layer)
    where += ' AND perc_ovlp > 0.90'
    sql = 'SELECT catalogid1, catalogid2 FROM {} WHERE {} LIMIT {}'.format(xtrack_layer,
                                                                           where,
                                                                           limit)
    gdf = db.sql2df(sql=sql)

ids1 = set(list(gdf['catalogid1']))
ids2 = set(list(gdf['catalogid2']))

ids1.update(ids2)

with open(r'E:\disbr007\imagery_orders\PGC_order_2020jul21_global_xtrack_cc20\selected_cids.txt', 'w') as src:
    for i in ids1:
        src.write(i)
        src.write('\n')
