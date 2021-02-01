import json
import sys

import requests
import argparse
import csv
import os
import unicodedata
import re


def parse_args():
    # command line argument parsing
    parser = argparse.ArgumentParser(description='Batch update values in iconik metadata fields')
    parser.add_argument('-u', '--appId', dest='appId', metavar="appId", type=str, help="iconik AppID", required=True)
    parser.add_argument('-s', '--authToken', dest='authToken', metavar="Auth Token", type=str, help="iconik Auth Token",
                        required=True)
    parser.add_argument('-f', '--field', dest='field', metavar="FIELD", help="iconik metadata field key", required=True)
    parser.add_argument('-a', '--address', dest='address', default='https://app.iconik.io',
                        help="iconik URL (default is https://app.iconik.io)")
    parser.add_argument('-i', '--input-file', metavar="FILE_PATH", dest='input_file',
                        help="Key/Value input file (line delimited values or csv key/value pairs)", required=True)
    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()


# define which field types this script works on
safe_field_types = ['drop_down']


def slugify(s):
    # slugify function to remove special characters from value strings
    s = s.lower()
    for c in [' ', '-', '.', '/']:
        s = s.replace(c, '_')
    s = re.sub('\W', '', s)
    s = s.replace('_', ' ')
    s = re.sub('\s+', ' ', s)
    s = s.strip()
    s = s.replace(' ', '-')
    return s


def get_field_data(fieldname, session):
    # get all information about a field
    url = session.address + '/API/metadata/v1/fields/' + fieldname + '/'
    r = session.get(url)
    r.raise_for_status()
    return r.json()


def get_file_values(input_file):
    # return json object of all key/value pairs of a field for non lookups
    if os.path.exists(input_file):
        try:
            with open(input_file, 'r') as csvfile:
                options_obj = csv.reader(csvfile, delimiter=',', quotechar='"')
                values = []
                #  this isn't a lookup, so we formulate JSON key/value pairs
                for row in options_obj:
                    if len(row) == 2:
                        values.append({"label": slugify(row[0]), "value": row[1].rstrip()})
                    elif len(row) == 1:
                        values.append({"label": slugify(row[0]), "value": row[0].rstrip()})
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


def main():
    if sys.version_info.major < 3:
        print("This script requires python 3 or greater. If you are running this on a portal system, "
              "you can use /opt/cantemo/python/bin/python")

    cli_args = parse_args()

    if cli_args.debug:
        import http.client
        import logging
        http.client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    session = requests.Session()
    session.headers.update({
        'App-ID': cli_args.appId,
        'Auth-Token': cli_args.authToken
    })

    session.address = cli_args.address

    #  get all the data about a field
    field_data = get_field_data(cli_args.field, session)

    #  check if our initial call returned good data
    if field_data is not None:
        #  check if our field is an acceptable field
        if field_data['field_type'] in safe_field_types:
            #  get back options for non lookup fields
            new_values = get_file_values(cli_args.input_file) + field_data['options']
            #  add existing values to new text file values, sort, and remove duplicates
            sorted_set = [dict(t) for t in set([tuple(sorted(d.items())) for d in new_values])]
            #  format data for posting back
            new_field_data = {}
            new_field_data['options'] = sorted_set
            url = session.address + '/API/metadata/v1/fields/' + cli_args.field + '/'
            r = session.patch(url, data=json.dumps(new_field_data))
            r.raise_for_status()
        else:
            print("Can't use this field type with this script. Exiting.")
            exit()
    else:
        print("Error finding field " + cli_args.field)
        exit()


if __name__ == '__main__':
    main()
