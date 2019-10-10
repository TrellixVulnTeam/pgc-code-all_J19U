# sql = (acq_time LIKE '%-04-%') OR (acq_time LIKE '%-05-%') OR (acq_time LIKE '%-07-%') OR (acq_time LIKE '%-10-%') OR (acq_time LIKE '%-01-%') 

acq_time = '2010-08-25T03:59:00+00:00'

month = acq_time.split('-')[1]

print(month)