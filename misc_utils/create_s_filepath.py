
def create_s_filepath(scene_id, strip_id, acqdate, prod_code):
	base = r'V:/pgc/data/sat/orig'
	sensor = scene_id[:4]
	pd = prod_code[1:3]
	year = acqdate[:4]
	month_num = acqdate[5:7]
	month_names = {'01':'jan',
				   '02':'feb',
				   '03':'mar',
				   '04':'apr',
				   '05':'may',
				   '06':'jun',
				   '07':'jul',
				   '08':'aug',
				   '09':'sep',
				   '10':'oct',
				   '11':'nov',
				   '12':'dec'}
	month = '{}_{}'.format(month_num, month_names[month_num])

	s_filepath = '/'.join([base, sensor, pd, year, month, strip_id, '{}.ntf'.format(scene_id)])
	return s_filepath
