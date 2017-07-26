# Cantemo Portal Metadata List Builder

This script can populate or update the values in Portal metadata fields with "choices" options.  Input files can be either flat text files with a single value (choice) per line, or a csv file where the first column are keys, second column are values.  All keys will be slugified first before being added

## Prerequisites

  - Cantemo Portal
  - Python
  - requests

## Installing

After having the prerequisites in place this script requests be installed. You can
install requests with pip.

```
pip install -r requirements.txt
```

## Usage

```
metadata_list_builder.py [-h] [-u USERNAME] -p PASSWORD -a ADDRESS -f
                                FIELD -i FILE_PATH
```

### Options overview

| short flag | long flag | description |
| ------ | ------ | ------ |
|  `-h` | `--help`  | show this help message and exit |
|  `-u <USENAME>` | `--username <USERNAME>` | Portal username, uses "admin" if not set |
|  `-p <PASSWORD>` | `--password <PASSWORD>` | Portal password |
|  `-a <ADDRESS>` | `--address <ADDRESS>` | IP Address or DNS name of Portal server|
|  `-f <FIELD>` | `--field <FIELD>` | Portal metadata field |
|  `-i <FILE_PATH>` | `--input-file <PATH>` | Key/Value input file (line delimited values or csv key/value pairs)|

### Example Syntax

`python ./metadata_list_builder.py -p password -a 192.168.10.10 -i ~/Desktop/listfile.txt -f portal_mf257027`

### Input file Syntax

The input files can be a simple list of values:

```value 1
value 2
value 3```

In this case, the keys will be slugified versions of the values, so `value-1 , value 1`.

It can be a CSV file with two columns:

```key1,value 1
key2,value 2
key3,value 3```

or 

```"key1","value 1"
"key2","value 2"
"key3","value 3"```

This will also slugify keys but leave values intact.

Or it can be a mix of both:

```value 1
key2, value 2
"key 3","value 3"```
