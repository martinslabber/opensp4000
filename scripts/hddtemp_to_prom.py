#!/usr/bin/env python3

import os
import argparse
import stat
import time
import subprocess
import tempfile
import csv


def get_hddtemp(device):
    temperature = None
    cmd = ['hddtemp', '-n', '--unit=C', device]
    try:
        temperature = int(subprocess.check_output(cmd))
    except Exception:
        temperature = None

    return temperature


def prom_metric(metric_name, label_values, value, timestamp=True):
    if value is None:
        value = 'Nan'
    # How to escape '{' in format string??
    labels = ', '.join(['{}="{}"'.format(k, v)
                        for k, v in label_values.items()])
    metric_str = "{}{}{}{} {}".format(metric_name, '{', labels, '}', value)
    if timestamp:
        metric_str += " {}".format(int(time.time() * 1e6))
    return metric_str


def hddtemp_to_prometheus_textfile(path, disk_map):

    fh, temp_file = tempfile.mkstemp(text=True)
    with open(temp_file, 'w') as fh:
        for bayno, disk_path in disk_map.items():
            abs_path = os.path.realpath(os.path.abspath(disk_path))
            temperature = get_hddtemp(abs_path)
            labels = {'bayno': bayno, 'device': abs_path}
            fh.write(prom_metric('node_disk_temperature', labels, temperature))
            fh.write('\n')
    os.chmod(temp_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.rename(temp_file, os.path.join(path, 'hdd_temp.prom'))
    return None


def read_drive_map(map_file):

    drive_map = {}
    # with open(map_file, newline='') as csvfile:
    reader = csv.DictReader(map_file)
    for row in reader:
        drive_map[int(row['bay'].strip())] = row['device'].strip()

    return drive_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mapfile', nargs=1, type=argparse.FileType('r'),
                        help="Device to bay map file. (CSV)")
    parser.add_argument('prometheus_textfile_path', nargs=1, type=str,
                        help="Path where prometheus textfile plugin expect"
                             "metrics files.")
    args = parser.parse_args()
    path = args.prometheus_textfile_path[0]
    assert os.path.isdir(path), "Prometheus path do not exists."

    bays = read_drive_map(args.mapfile[0])
    hddtemp_to_prometheus_textfile(path, bays)
