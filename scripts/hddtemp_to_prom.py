#!/usr/bin/python3

"""Collect harddrive temperatures and write it to Prometheus textfile."""

import argparse
import csv
import datetime
import glob
import json
import os
import stat
import subprocess
import tempfile
import time

METRIC = "node_disk_temperature_celsius"


def get_hddtemp(device):
    """Get the temperature of a drive."""
    temperature = None
    cmd = ['/usr/sbin/hddtemp', '-n', '--unit=C', device]
    try:
        temperature = int(subprocess.check_output(cmd))
    except Exception:
        temperature = None

    return temperature


def prom_metric(metric_name, label_values, value, timestamp=False):
    if value is None:
        value = 'Nan'
    # How to escape '{' in format string??
    labels = ', '.join(
        ['{}="{}"'.format(k, v) for k, v in label_values.items() if v is not None])
    metric_str = "{}{}{}{} {}".format(metric_name, '{', labels, '}', value)
    if timestamp:
        metric_str += " {}".format(int(time.time() * 1e6))
    return metric_str


def create_labels(config, **kwargs):
    labels = dict(kwargs)
    position = config.get('position')
    if position:
        labels['rack_position'] = position

    name = config.get('rack', {}).get('name')
    if name:
        labels['rack_name'] = name

    return labels


def hddtemp_to_prometheus_textfile(path, disk_map, config):

    fh, temp_file = tempfile.mkstemp(text=True)
    with open(temp_file, 'w') as fh:
        fh.write("# " + datetime.datetime.now().isoformat() + "\n")
        fh.write("# HELP " + METRIC + " HDD monitor for temperature "
                 "(input)\n")
        fh.write("# TYPE " + METRIC + " gauge\n")
        for disk_path, bayno in disk_map.items():
            abs_path = os.path.realpath(os.path.abspath(disk_path))
            temperature = get_hddtemp(abs_path)
            labels = create_labels(config, bayno=bayno, device=abs_path)
            fh.write(prom_metric(METRIC, labels, temperature))
            fh.write('\n')
    os.chmod(temp_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.rename(temp_file, os.path.join(path, 'hdd_temp.prom'))
    return None


def read_drive_map(map_file):

    drive_map = {}
    reader = csv.DictReader(map_file)
    for row in reader:
        drive_map[row['device'].strip()] = int(row['bay'].strip())

    return drive_map


def create_config():
    """Collects system information."""
    data = {}
    for filename in sorted(glob.glob('/etc/hardware/*.json')):
        try:
            with open(filename) as fh:
                file_data = json.load(fh)
                data.update(file_data)
        except Exception as error:
            print(error)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'mapfile',
        nargs=1,
        type=argparse.FileType('r'),
        help="Device to bay map file. (CSV)")
    parser.add_argument(
        'prometheus_textfile_path',
        nargs=1,
        type=str,
        help="Path where prometheus textfile plugin expect"
        "metrics files.")
    args = parser.parse_args()
    path = args.prometheus_textfile_path[0]
    assert os.path.isdir(path), "Prometheus path do not exists."

    bays = read_drive_map(args.mapfile[0])
    config = create_config()
    hddtemp_to_prometheus_textfile(path, bays, config)
