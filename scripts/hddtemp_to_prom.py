#!/usr/bin/env python3

import os
import argparse
import stat
import time
import subprocess
import tempfile
import csv
import datetime
import configparser

METRIC = "node_disk_temperature_celsius"

def get_hddtemp(device):
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
    labels = ', '.join(['{}="{}"'.format(k, v)
                        for k, v in label_values.items()])
    metric_str = "{}{}{}{} {}".format(metric_name, '{', labels, '}', value)
    if timestamp:
        metric_str += " {}".format(int(time.time() * 1e6))
    return metric_str


def create_labels(config, **kwargs):
    labels = dict(kwargs)
    for key in ['rack-name', 'rack-u']:
        value = config.get(key)
        if value:
            labels[key] = value
    return labels


def hddtemp_to_prometheus_textfile(path, disk_map, config):

    fh, temp_file = tempfile.mkstemp(text=True)
    with open(temp_file, 'w') as fh:
        fh.write("# " + datetime.datetime.now().isoformat() + "\n")
        fh.write("# HELP " + METRIC + " HDD monitor for temperature "
                 "(input)\n")
        fh.write("# TYPE " + METRIC + " gauge\n")
        for bayno, disk_path in disk_map.items():
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
    # with open(map_file, newline='') as csvfile:
    reader = csv.DictReader(map_file)
    for row in reader:
        drive_map[int(row['bay'].strip())] = row['device'].strip()

    return drive_map


def create_config():
    """Collects some system information."""
    data = {}
    if os.path.isfile('/etc/hardware/rack'):
        config = configparser.ConfigParser()
        config.read_file(open('/etc/hardware/rack'))

        for section, key in [('rack', 'name'), ('rack', 'u')]:
            value = config.get(section, key, fallback=None)
            if value:
                data[section + '-' + key] = value

    return data


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
    config = create_config()
    hddtemp_to_prometheus_textfile(path, bays, config)
