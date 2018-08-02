#!/usr/bin/env python3


import collections
import csv
import glob
import json
import os
import re
import subprocess
import sys


cmd = '/opt/MegaRAID/storcli/storcli64'


def run_subprocess(cmd):
    retval = subprocess.check_output(cmd.split(' '))
    return retval.decode('utf-8')


def get_lsi_cards():


    def run_storcli_show():
       return run_subprocess('sudo {} show'.format(cmd))


    def strip_value(line):
        value = line.split('=')[1]
        return value.strip()


    def format_pci_addr(pci_address):
        split_addr = re.split('(:|\.)', pci_address)
        if len(split_addr) == 7:
            pci_nums = [str(int(split_addr[i])) for i in [0,2,4,6]]
            return '{}:{}:{}.{}'.format(pci_nums[0].rjust(4,'0'), pci_nums[1].rjust(2,'0'), pci_nums[2].rjust(2,'0'), pci_nums[3].rjust(1,'0'))
        return pci_address


    # execute the command
    cmd_output = run_storcli_show().splitlines()

    # get info from command output
    status_code = strip_value(cmd_output[0])
    status = strip_value(cmd_output[1])
    hostname = strip_value(cmd_output[5])

    # get info on attached card(s)

    # find table boundaries in the command output
    table_boundaries = [i for i, line in enumerate(cmd_output) if line == '-'*60]
    table = [l.split() for l in cmd_output[table_boundaries[1] + 1:table_boundaries[2]]]

    lsi_cards = []
    for row in table:
        ctl = row[0]
        model = row[1]
        pci_addr = format_pci_addr(row[6])
        lsi_cards.append(dict(zip(('ctl','model','pci_addr',),(ctl,model,pci_addr,)))) 
 
    storcli64_show = dict(zip(('status_code', 'status', 'hostname', 'cards',),(status_code, status, hostname, lsi_cards,)))

    return storcli64_show


def unmangle_symlink(d):
    path = os.path.dirname(d)
    rel_src = os.readlink(d)
    mangled_src = os.path.join(path,rel_src)
    return os.path.abspath(mangled_src)


def main(input_filename, output_filename):
    lsi_cards = get_lsi_cards()
    #list should be order specific
    pci_busses = [l['pci_addr'] for l in lsi_cards['cards']]

    # map by-path to bays
    hdd_by_path_to_bay = []
    with open(input_filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
           hdd_by_path_to_bay.append(('/dev/disk/by-path/pci-{}-sas-phy{}-lun-0'.format(pci_busses[int(row['pci'])], row['phy']), int(row['bay'])),)

    # get all by-id devices
    ata_glob = glob.glob('/dev/disk/by-id/ata-*') 
    ata_disks = [(unmangle_symlink(d),d) for d in ata_glob]
    
    # map by path to device
    path_disks = [(unmangle_symlink(d), d) for d in list(zip(*hdd_by_path_to_bay))[0]] 
 
    # cross map and filter by-id to by-path
    ata_dict = dict(ata_disks)
    path_dict = dict(path_disks)   
    hdd_by_id_to_path = [(path_dict[k],ata_dict[k]) for k in path_dict.keys()]
    
    # map bay to by-path
    id_to_path_dict = dict(hdd_by_id_to_path)
    by_path_to_bay_dict = dict(hdd_by_path_to_bay) 
    hdd_bay_to_by_id = [(by_path_to_bay_dict[k], id_to_path_dict[k],) for k in by_path_to_bay_dict.keys()]

    with open(output_filename, 'w') as csvfile:
        fieldnames = ['bay', 'device']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for bay, device in sorted(hdd_bay_to_by_id):
            writer.writerow({'bay': bay, 'device': device})

if __name__ == '__main__':

    input_filename='/etc/opensp4000/sp4000l_bay_layout.csv'
    output_filename='/etc/opensp4000/disk_map.2.csv'

    if not os.path.isfile(input_filename):
        print('{} does not exist. Exiting.'.format(input_filename))
        sys.exit(0)
    if os.path.isfile(output_filename):
        print('{} already exists. Exiting.'.format(output_filename))
        sys.exit(0)
    if not os.path.isfile(cmd):
        print('ERROR: {} not found, please install.'.format(cmd))
        sys.exit(0)

    main(input_filename, output_filename)

