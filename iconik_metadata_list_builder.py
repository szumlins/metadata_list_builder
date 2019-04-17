import json
import requests
import argparse
import csv
import os 
import unicodedata
import re 

#command line argument parsing
parser = argparse.ArgumentParser(description='Batch update values in iconik metadata fields')
parser.add_argument('-u','--appId',dest='appId',metavar="appId",type=str,help="iconik AppID",required=True)
parser.add_argument('-s','--authToken',dest='authToken',metavar="Auth Token",type=str,help="iconik Auth Token",required=True)
parser.add_argument('-f','--field',dest='field',metavar="FIELD",help="iconik metadata field key",required=True)
parser.add_argument('-a','--address',dest='address',default='https://app.iconik.io',help="iconik URL (default is https://app.iconik.io)")
parser.add_argument('-i','--input-file',metavar="FILE_PATH",dest='input_file',help="Key/Value input file (line delimited values or csv key/value pairs)",required=True)
cli_args = parser.parse_args()

#define which field types this script works on
safe_field_types = ['drop_down']

def slugify(s):
	#slugify function to remove special characters from value strings
	s = s.lower()
	for c in [' ', '-', '.', '/']:
		s = s.replace(c, '_')
	s = re.sub('\W', '', s)
	s = s.replace('_', ' ')
	s = re.sub('\s+', ' ', s)
	s = s.strip()			
	s = s.replace(' ', '-')
	return s
def get_field_data(fieldname):
	#get all information about a field
	r = requests.get(cli_args.address + '/API/metadata/v1/fields/' + fieldname + '/',headers={'App-ID':cli_args.appId,'Auth-Token':cli_args.authToken})
	return r.json()
def get_file_values(input_file):
	#return json object of all key/value pairs of a field for non lookups
	if os.path.exists(input_file):
		try:
			with open(input_file, 'r') as csvfile:
				options_obj = csv.reader(csvfile, delimiter=',', quotechar='"')
				values = []		
				#this isn't a lookup, so we formulate JSON key/value pairs
				for row in options_obj:
					if len(row) == 2:
						values.append({"label":slugify(row[0]),"value":row[1].rstrip()})
					elif len(row) == 1:
						values.append({"label":slugify(row[0]),"value":row[0].rstrip()})
					else:
						print("Too many options for CSV file, should have two per line")
						exit()													
		except Exception as e:
			print("Error trying to parse input file: " + str(e))
			exit()
	else:
		print("File " + input_file + " doesn't exist")
		exit()
	return values
def unicode_list(list):
	new_list = []
	for pair in list:
		unidict = dict((k.decode('utf8'), v.decode('utf8')) for k, v in pair.items())
		new_list.append(unidict)
	return new_list

#get all the data about a field
field_data = get_field_data(cli_args.field)

#check if our initial call returned good data
if field_data != None:
	#check if our field is an acceptable field
	if field_data['field_type'] in safe_field_types:
		# get back options for non lookup fields
		new_values = get_file_values(cli_args.input_file) + field_data['options']
		#add existing values to new text file values, sort, and remove duplicates
		sorted_set = [dict(t) for t in set([tuple(sorted(d.items())) for d in new_values])]	
		#format data for posting back			
		new_field_data = {}
		new_field_data['options'] = sorted_set						
		r = requests.patch(cli_args.address + '/API/metadata/v1/fields/' + cli_args.field + '/',headers={'App-ID':cli_args.appId,'Auth-Token':cli_args.authToken},data=json.dumps(new_field_data))			
		r.raise_for_status()
	else:
		print("Can't use this field type with this script. Exiting.")
		exit()
else:
	print("Error finding field " + cli_args.field)
	exit()