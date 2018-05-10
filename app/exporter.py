#!/usr/bin/python

import json
import time
import urllib2
from prometheus_client import start_http_server
from prometheus_client.core import CounterMetricFamily, REGISTRY
import argparse
import yaml
from objectpath import Tree
import logging
import re
import boto3
from botocore.compat import json, six, total_seconds

DEFAULT_PORT=9158
DEFAULT_LOG_LEVEL='info'

class EnhancedRDSCollector(object):
  def __init__(self, config, metrics):
    self._config = config
    self._metrics = metrics
    self.aws_region = config['aws_region']
    self.client = boto3.client('logs', region_name=self.aws_region)

  def uptime_to_num(self, str):
    split = str.split(', ')
    if len(split) == 2:
      time_split = split[1].split(':')
      time = (int(time_split[0]) * 60 * 60) + (int(time_split[1]) * 60) + int(time_split[2])
      seconds = (int(re.findall('\d+',split[0])[0]) * 24 * 60 * 60) + time
    elif len(split) == 1:
      time_split = split[0].split(':')
      seconds = (int(time_split[0]) * 60 * 60) + (int(time_split[1]) * 60) + int(time_split[2])
    return seconds

  def collect(self):
    config = self._config
    metrics = self._metrics
    for db_config in config['db_resources']:
      kwargs = {'logGroupName': 'RDSOSMetrics', 'limit': 1, 'logStreamName': db_config}
      response = self.client.get_log_events(**kwargs)
      message = json.loads(response['events'][0]['message'])
      result_tree = Tree(message)
      instance_id = message['instanceID']
      engine = message['engine']

      # Parse uptime to a number and produce a metric
      logging.info(message['uptime'])
      uptime = self.uptime_to_num(message['uptime'])
      c = CounterMetricFamily('rds_enhanced_uptime', 'RDS uptime in seconds', labels=['db','engine'])
      c.add_metric([instance_id,engine], uptime)
      yield c

      logging.info(instance_id)
      for metric_config in metrics['metrics'][engine]:
        metric_description = metric_config.get('description', '')
        metric_path = metric_config['path']
        value = result_tree.execute(metric_path)
        logging.info("metric_name: {}, value for '{}' : {}".format(metric_config['name'], metric_path, value))
        c = CounterMetricFamily(metric_config['name'], metric_description, labels=['db','engine'])
        c.add_metric([instance_id,engine], value)
        yield c

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Config options')
  parser.add_argument('config_file_path', help='Path of the main config file')
  parser.add_argument('metrics_file_path', help='Path of the metrics config file')
  args = parser.parse_args()
  with open(args.metrics_file_path) as metrics_file:
    metrics = yaml.load(metrics_file)
  with open(args.config_file_path) as config_file:
    config = yaml.load(config_file)
    log_level = config.get('log_level', DEFAULT_LOG_LEVEL)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.getLevelName(log_level.upper()))
    exporter_port = config.get('exporter_port', DEFAULT_PORT)
    logging.debug("Config %s", config)
    logging.info('Starting server on port %s', exporter_port)
    start_http_server(exporter_port)
    REGISTRY.register(EnhancedRDSCollector(config,metrics))
  while True: time.sleep(1)
