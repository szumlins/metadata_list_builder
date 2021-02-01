from __future__ import print_function

import json
import sys

import requests
import argparse
import csv
import os
import unicodedata
import re


# define which field types this script works on
safe_field_types = ['dropdown', 'checkbox', 'radio', 'workstep', 'lookup']


def parse_args():
    # command line argument parsing
    parser = argparse.ArgumentParser(description='Batch update values in Portal metadata fields')
    parser.add_argument('-u', '--username', dest='username', metavar="USERNAME", type=str,
                        help="Portal username, uses \"admin\" if not set", default="admin")
    parser.add_argument('-p', '--password', dest='password', metavar="PASSWORD", type=str, help="Portal password",
                        required=True)
    parser.add_argument('-a', '--address', dest='address', metavar="ADDRESS", type=str,
                        help="IP Address or DNS name of Portal server", required=True)
    parser.add_argument('-f', '--field', dest='field', metavar="FIELD", help="Portal metadata field", required=True)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--input-file', metavar="INPUT_FILE_PATH", dest='input_file',
                        help="Key/Value input file (line delimited values or csv key/value pairs)")
    group.add_argument('-e', '--export-file', metavar="OUTPUT_FILE_PATH", dest='output_file',
                       help='Key/Value output file (csv file)')

    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()


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
    r = session.get(session.address + 'metadata-field/' + fieldname, headers={'accept': 'application/json'},
                     params={'data': 'all'})
    for d in r.json().get('data', []):
        if d['key'] == 'extradata':
            return json.loads(str(d['value']))
        else:
            return []


def get_field_document(fieldname, session):
    # get all information about a field
    r = session.get(session.address + 'metadata-field/' + fieldname, headers={'accept': 'application/json'},
                     params={'data': 'all'})
    return r.json()


def get_lookup_values(fieldname, session):
    # return json object of all key/value pairs of a field for lookups.  If the field values list is empty, just return an empty list
    r = session.get(session.address + 'metadata-field/' + fieldname + '/values', headers={'accept': 'application/json'})
    try:
        return r.json()['field']
    except:
        return []


def write_file_values(output_file, values):
    with open(output_file, 'w') as csvfile:
        csvwriter = csv.DictWriter(csvfile, fieldnames=['key', 'value'], delimiter=',', quotechar='"')
        csvwriter.writerows(values)


def get_file_values(input_file):
    # return json object of all key/value pairs of a field for non lookups
    if os.path.exists(input_file):
        try:
            with open(input_file, 'r') as csvfile:
                options_obj = csv.reader(csvfile, delimiter=',', quotechar='"')
                values = []
                # this isn't a lookup, so we formulate JSON key/value pairs
                for row in options_obj:
                    if len(row) == 2:
                        values.append({"key": slugify(row[0]), "value": row[1].rstrip()})
                    elif len(row) == 1:
                        values.append({"key": slugify(row[0]), "value": row[0].rstrip()})
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


    # format our URL as a shortcut
    portal_url = 'http://' + cli_args.address + ':8080/API/'

    session = requests.Session()
    session.auth = (cli_args.username, cli_args.password)
    session.address = portal_url

    # get all the data about a field
    field_data = get_field_data(cli_args.field, session)
    field_document = get_field_document(cli_args.field, session)

    #import ipdb; ipdb.set_trace()

    # check if our initial call returned good data
    if field_data != None:
        # check if our field is an acceptable field
        if field_data['type'] in safe_field_types:
            # check what type of field and process
            if field_data['type'] != 'lookup':

                if cli_args.output_file:
                    write_file_values(cli_args.output_file, field_data['values'])
                else:
                    # get back options for non lookup fields
                    new_values = get_file_values(cli_args.input_file) + field_data['values']
                    # add existing values to new text file values, sort, and remove duplicates
                    sorted_set = [dict(t) for t in set([tuple(sorted(d.items())) for d in new_values])]
                    # format data for posting back
                    field_data['values'] = sorted_set
                    # find our extradata index in the data object
                    extradata_index = next(index for (index, d) in enumerate(field_document['data']) if d['key'] == 'extradata')
                    # update that index's value with our new updated field data
                    field_document['data'][extradata_index]['value'] = json.dumps(field_data)
                    # put back data to field
                    r = session.put(session.address + 'metadata-field/' + cli_args.field,
                                     headers={'accept': 'application/json', 'content-type': 'application/json'},
                                     data=json.dumps(field_document))
                    r.raise_for_status()
            else:
                existing_values = get_lookup_values(cli_args.field, session)

                if cli_args.output_file:
                    write_file_values(cli_args.output_file, existing_values)
                else:
                    # get back options for lookup fields
                    new_values = get_file_values(cli_args.input_file) + existing_values
                    # add existing values to new text file values, sort, and remove duplicates
                    sorted_set = [dict(t) for t in set([tuple(sorted(d.items())) for d in new_values])]
                    # format data for posting back
                    lookup_data = {'field': sorted_set}
                    # format as XML since VS is broken for posting JSON right now
                    metadata_doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><SimpleMetadataDocument xmlns="http://xml.vidispine.com/schema/vidispine">'
                    for pair in lookup_data['field']:
                        metadata_doc = metadata_doc + '<field><key>' + pair['key'] + '</key><value>' + pair[
                            'value'] + '</value></field>'
                    metadata_doc = metadata_doc + '</SimpleMetadataDocument>'
                    # put back data to field
                    r = session.put(session.address + 'metadata-field/' + cli_args.field + '/values',
                                     headers={'accept': 'application/json', 'content-type': 'application/xml'},
                                     data=metadata_doc.encode('utf-8'))
                    r.raise_for_status()

        else:
            print("Can't use this field type with this script. Exiting.")
            exit()
    else:
        print("Error finding field " + cli_args.field)
        exit()


if __name__ == '__main__':
    main()
