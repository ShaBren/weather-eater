from collections import namedtuple

DataPoint = namedtuple( 'DataPoint', [ 'id', 'name', 'units', 'hidden' ] )

DataType = {}

DataType[ 'stationtype' ] = DataPoint( 'stationtype', 'Station Type', 'string', False )
DataType[ 'PASSKEY' ] = DataPoint( 'PASSKEY', 'Station MAC Address', 'string', True )
DataType[ 'baromabsin' ] = DataPoint( 'baromabsin', 'Barometer (Absolute)', 'inHg', False )
DataType[ 'batt2' ] = DataPoint( 'batt2', 'Battery Status (Bedroom)', 'batt', False )
DataType[ 'batt_co2' ] = DataPoint( 'batt_co2', 'Battery Status (Unknown)', 'batt', False )
DataType[ 'battout' ] = DataPoint( 'battout', 'Battery Status (Outdoor)', 'batt', False )
DataType[ 'dailyrainin' ] = DataPoint( 'dailyrainin', 'Rain (Daily)', 'inch', False )
DataType[ 'dateutc' ] = DataPoint( 'dateutc', 'Time of Measurement', 'time', False )
DataType[ 'eventrainin' ] = DataPoint( 'eventrainin', 'Rain (Event)', 'inch', False )
DataType[ 'hourlyrainin' ] = DataPoint( 'hourlyrainin', 'Rain (Hourly)', 'inch', False )
DataType[ 'humidity' ] = DataPoint( 'humidity', 'Humidity (Outdoor)', 'percentage', False )
DataType[ 'humidity2' ] = DataPoint( 'humidity2', 'Humidity (Bedroom)', 'percentage', False )
DataType[ 'humidityin' ] = DataPoint( 'humidityin', 'Humidity (Office)', 'percentage', False )
DataType[ 'maxdailygust' ] = DataPoint( 'maxdailygust', 'Max Wind Gust (Today)', 'mph', False )
DataType[ 'monthlyrainin' ] = DataPoint( 'monthlyrainin', 'Rain (Montly)', 'inch', False )
DataType[ 'solarradiation' ] = DataPoint( 'solarradiation', 'Solar Radiation', 'w/m^2', False )
DataType[ 'tempf' ] = DataPoint( 'tempf', 'Temperature (Outdoor)', 'degF', False )
DataType[ 'temp2f' ] = DataPoint( 'temp2f', 'Temperature (Bedroom)', 'degF', False )
DataType[ 'tempinf' ] = DataPoint( 'tempinf', 'Temperature (Office)', 'degF', False )
DataType[ 'totalrainin' ] = DataPoint( 'totalrainin', 'Rain (Total)', 'inch', False )
DataType[ 'uv' ] = DataPoint( 'uv', 'UV Index', 'int', False )
DataType[ 'weeklyrainin' ] = DataPoint( 'weeklyrainin', 'Rain (Weekly)', 'inch', False )
DataType[ 'winddir' ] = DataPoint( 'winddir', 'Wind Direction', 'deg', False )
DataType[ 'windgustmph' ] = DataPoint( 'windgustmph', 'Wind Gusts', 'mph', False )
DataType[ 'windspeedmph' ] = DataPoint( 'windspeedmph', 'Wind Speed', 'mph', False )

def degree_to_dir( degree ):
	if degree <= 11 or degree > 349:
		return 'N'
	elif degree <= 34:
		return 'NNE'
	elif degree <= 56:
		return 'NE'
	elif degree <= 79:
		return 'ENE'
	elif degree <= 101:
		return 'E'
	elif degree <= 124:
		return 'ESE'
	elif degree <= 146:
		return 'SE'
	elif degree <= 169:
		return 'SSE'
	elif degree <= 191:
		return 'S'
	elif degree <= 214:
		return 'SSW'
	elif degree <= 236:
		return 'SW'
	elif degree <= 259:
		return 'WSW'
	elif degree <= 281:
		return 'W'
	elif degree <= 304:
		return 'WNW'
	elif degree <= 326:
		return 'NW'
	elif degree <= 349:
		return 'NNW'

def to_unit_string( unit, value ):
	if unit == 'inch':
		return "{} inch{}".format( value, "es" if float( value ) > 1 else "" )
	elif unit == 'string':
		return value
	elif unit == 'batt':
		return 'Good' if value == '1' else 'Low'
	elif unit == 'int':
		return value
	elif unit == 'deg':
		return '{}° {}'.format( value, degree_to_dir( int( value ) ) )
	elif unit == 'degF':
		return '{} °F'.format( value )
	elif unit == 'time':
		return value
	elif unit == 'percentage':
		return '{}%'.format( value )
	elif unit == 'inHg':
		return '{} inHg'.format( value )
	elif unit == 'mph':
		return '{} MPH'.format( value )
	elif unit == 'w/m^2':
		return '{} w/m^2'.format( value )
	else:
		return value
	
