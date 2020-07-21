from selection_utils.db_utils import Postgres, encode_geom_sql
from selection_utils.query_danco import query_footprint

footprint_db = 'danco.footprint'
dg_imagery_index_stereo = 'dg_imagery_index_stereo'
pgc_imagery_catalogids = 'pgc_imagery_catalogids'
dg_imagery_index_xtrack_cc20 = 'dg_imagery_index_xtrack_cc20'

cid_col = 'catalogid'
stp_col = 'stereopair'

# where = "acqdate > '2019-06-01'"
#
# class Footprint():
#     def __init__(self):
#         self.db_name = 'danco.footprint'


def get_stereo_ids(where=None):
    sql = "SELECT {}, {} FROM {}".format(cid_col, stp_col, dg_imagery_index_stereo)
    if where:
        sql += " WHERE {}".format(where)

    with Postgres(footprint_db) as db_src:
        # cols = db_src.get_layer_columns(dg_imagery_index_stereo)
        # stereo_tbl_ct = db_src.get_sql_count(sql)
        stereo_tbl = db_src.sql2df(sql=sql)

    stereo_ids = set(list(stereo_tbl[cid_col]) + list(stereo_tbl[stp_col]))

    return stereo_ids


def create_cid_noh_where(cid_cols, tbl):
    wheres = ['catalog_id = {}.{}'.format(tbl, c) for c in cid_cols]
    wheres_str = ' OR '.join(wheres)
    not_exists_where = """NOT EXISTS(SELECT FROM {} WHERE {})""".format(pgc_imagery_catalogids, wheres_str)

    return not_exists_where


def xtrack_noh_sql(where=None, cols=None):
    not_exists_where = create_cid_noh_where(['catalogid1', 'catalogid2'], dg_imagery_index_xtrack_cc20)

    if where:
        where = "{} {}".format(where, not_exists_where)
    else:
        where = not_exists_where

    geom_sql = encode_geom_sql(geom_col='shape', encode_geom_col='geom')

    if cols:
        cols_str = str(cols)[1:-1].replace("'", "")
    else:
        cols_str = '*'

    sql_noh = ("""SELECT {0}, {1} FROM {2} 
                  WHERE {3} 
                  LIMIT 100""").format(geom_sql, cols_str,
                                       dg_imagery_index_xtrack_cc20,
                                       where)

    return sql_noh
