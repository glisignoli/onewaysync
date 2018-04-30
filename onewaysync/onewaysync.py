#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''onewaysync

Usage:
  onewaysync -i INPUT_DIRECTORY -l LIST_DIRECTORY -o OUTPUT_DIRECTORY
  onewaysync -h | --help
  onewaysync --version

Options:
  -h --help     Show this screen.
  -i            Source directory
  -l            list files directory
  -o            TAR destination
  --version     Show version.
'''

from __future__ import unicode_literals, print_function
from docopt import docopt
from jsondiff import diff
import os
import sys
import hashlib
import json
import glob
import tarfile
import re

__version__ = "0.1.0"
__author__ = "Gino Lisignoli"
__license__ = "MIT"


def tarfiles(listoffiles, destination, snapshot_number):
    tar = tarfile.open(destination + '/snapshot_' + str(snapshot_number) +
                       '.tar.gz', 'w|gz')
    for name in listoffiles:
        tar.add(name)
    tar.close()


def md5sum(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def generate_list(input_dir):
    r = {}
    allfiles = [os.path.join(dirpath, filename)
                for (dirpath, dirs, files) in os.walk(input_dir)
                for filename in (dirs + files)]

    for f in allfiles:
        if os.path.isfile(f):
            r[f] = md5sum(f)
        else:
            pass
            # r[f] = 'DIRECTORY'
    return r


def generate_tar_list(snapshot_diff):
    tarlist = []
    ##DEBUG
    if '$insert' in snapshot_diff:
        for entry in snapshot_diff['$insert']:
            tarlist.append(entry)
    if '$update' in snapshot_diff:
        for entry in snapshot_diff['$update']:
            tarlist.append(entry)
    return tarlist


def main():
    '''Main entry point for the onewaysync CLI.'''
    args = docopt(__doc__, version=__version__)
    input_dir = args['INPUT_DIRECTORY']
    listfiles_dir = args['LIST_DIRECTORY']
    output_dir = args['OUTPUT_DIRECTORY']
    snapshot_number = 0

    listfiles = []

    # DEBUG
    print(args)

    # Check for source directory
    if not (os.path.isdir(input_dir) and os.path.exists(input_dir)):
        sys.exit('Source does not exist or is not a directory')

    # Check for destination directory
    if not (os.path.isdir(output_dir) and os.path.exists(output_dir)):
        sys.exit('Output does not exist or is not a directory')

    # Check for list directory
    if not (os.path.isdir(listfiles_dir) and os.path.exists(listfiles_dir)):
        sys.exit('Listfiles does not exist or is not a directory')

    # Check for inital directory listing, if not exist then generate file
    if not(os.path.exists(listfiles_dir + '/initial.json')):
        print('Generating initial list')
        initial_list = generate_list(input_dir)
        with open(listfiles_dir + '/initial.json', 'w') as outfile:
            json.dump(initial_list, outfile)
        # Because the initial listing doesn't exist, generate tar and exit
        print('Creating initial tar file')
        tarfiles(initial_list, output_dir, snapshot_number)
        sys.exit()

    # Check if initial.json is a file
    if not(os.path.isfile(listfiles_dir + '/initial.json')):
        # initial.json isn't a file
        sys.exit('Initial listfile ' + listfiles_dir +
                 '/initial.json isn\'t a file')

    # Check for incremental listing files
    listfiles = glob.glob(listfiles_dir + '/*.json')
    listfiles.remove(listfiles_dir + '/initial.json')
    if listfiles:
        # If exist then generate load initial as last snapshot listing
        listfiles.sort()

        # listfiles are named as snapshot_1.json, snapshot_2.json etc...
        # Load last snapshot json file
        snapshot = json.load(open(listfiles[-1]))

        # Update snapshot number to latest +1
        snapshot_number = int(re.findall(r'\d+', listfiles[-1])[0]) + 1

    else:
        # Use inremental listing and generate directory snapshot listing
        # load initial.json
        snapshot = json.load(open(listfiles_dir + '/initial.json'))
        print("Snapshot")
        print(snapshot)

    # Generate snapshot listing of current directory
    print('Generating new directory list')
    current_dir = generate_list(input_dir)

    # Compare against generated snapshot and generate diff
    print('Comparing')
    snapshot_diff = json.loads(diff(
        snapshot, current_dir, syntax='explicit', dump=True))

    if not snapshot_diff:
        # If no diff then exit
        print('No difference found, exiting')
        sys.exit()
    else:
        tarlist = generate_tar_list(snapshot_diff)
        print('Making tar of files')

        # Create TAR
        tarfiles(tarlist, output_dir, snapshot_number)

        if '$delete' in snapshot_diff:
            print('List of files to be deleted')
            for i in snapshot_diff['$delete']:
                print(i)

        if '$insert' in snapshot_diff:
            print('List of files to be added')
            for i in snapshot_diff['$insert']:
                print(i)

        if '$update' in snapshot_diff:
            print('List of files modified')
            for i in snapshot_diff['$update']:
                print(i)

        # Write snapshot state to list
        with open(listfiles_dir + '/snapshot_' + str(snapshot_number) +
                  '.json', 'w') as outfile:
            json.dump(current_dir, outfile)


if __name__ == '__main__':
    main()
