#!/usr/bin/env python3
"""This script parses the output of Ceph swift-bench and stores the results in
Elasticsearch.

Require a file ~/.config/elasticsearch.json with the config to connect to
Elasticsearch. This file is JSON formatted and contains at least a URL field.

Optional files can be given as command line arguments, these file can be JSON
(file has a .json extension) or key values (e.g. key=value) files.
The contents of the files will be aggregated and added to every metric sent to
Elasticsearch.
"""
import datetime
import json
import os
import sys

import requests


class SB2E:
    """Swift Bench to Elastic.

    This class processes lines from Ceph swift-bench command and inserts
    the metrics into an Elasticsearch instance.
    """
    METHODS = ['GETS', 'PUTS', 'DEL']

    def __init__(self, config, extra_info):
        self._host = config['url']
        self._extra_info = extra_info
        self._zero()

    def _zero(self):
        """Write zero metrics for each method.abs.

        Writing zero metrics to indicate to elastic that this method is
        not processing data at the moment.
        """
        for method in self.METHODS:
            self.new_metric(method)

    def parse_swift_bench_line(self, line):
        """Parse a line from swift-bench."""
        line = line.strip()
        print(line)  # Print the line so we can use this in a shell pipe
        sections = line.split()
        if sections[0] == 'swift-bench':
            # _time = "T".join(sections[1:3])
            items = sections[4]
            method = sections[5]
            rate = sections[-1]
            try:
                self.new_metric(method, items=items, rate=rate)
            except Exception as error:
                print(error)

    def new_metric(self, method, items=0, rate=0):
        doc = {}
        doc.update(self._extra_info)
        if method not in self.METHODS:
            return
        items = int(items)
        if isinstance(rate, (str, bytes)):
            rate = float(rate.split('/', 1)[0])
        doc['app'] = 'swift-bench'
        doc['method'] = method
        doc['items'] = items
        doc['rate'] = rate
        self.send_metric(doc)

    def send_metric(self, document):
        """Send a metric to Elasticsearch."""
        now = datetime.datetime.utcnow()
        index = now.strftime("logstash-%Y.%m.%d")
        document['@timestamp'] = now.isoformat(sep='T') + "+00:00"
        url = "{}/{}/doc".format(self._host, index)
        headers = {"Cache-Control": "no-cache"}
        return requests.post(url, json=document, headers=headers)

    def close(self):
        self._zero()


def cleanup_value(value):
    """Try and convert the given value to a float."""
    value = value.strip()
    try:
        return float(value)
    except Exception:
        return value


def read_conf_file(filename):
    """Read the given config file and return the contents as a dict."""
    info = {}
    filename = os.path.realpath(filename)
    if os.path.isfile(filename):
        _, ext = os.path.splitext(filename)
        if ext and ext.lower() == ".json":
            with open(filename) as fh:
                info = json.load(fh)
        else:
            with open(filename) as fh:
                for line in fh.readlines():
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        info[key.strip()] = cleanup_value(value)
    return info


def parse_args():
    info = {}
    for filename in sys.argv[1:]:
        info.update(read_conf_file(filename))
    return info


if __name__ == "__main__":

    info = parse_args()
    with open(os.path.expanduser("~/.config/elasticsearch.json")) as fh:
        config = json.load(fh)
    sb2e = SB2E(config, info)
    for line in sys.stdin:
        sb2e.parse_swift_bench_line(line)
    sb2e.close()
