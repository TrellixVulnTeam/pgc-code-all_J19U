import datetime
import os

from tqdm import tqdm


ordered_dir = r'E:\disbr007\imagery_orders'
last_update = datetime.datetime(2020, 2, 11)

for root, dirs, files in os.walk(ordered_dir):
    for f in files:
        if f.endswith(('.csv', '.txt', '.xls', '.xlsx')):
            fname = os.path.join(root, f)
            if datetime.datetime.fromtimestamp(os.stat(fname).st_ctime) > last_update:
                print(f)


