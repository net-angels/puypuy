import lib.record_rate
import lib.pushdata
import urllib2
import os, sys
import ConfigParser
import datetime
import socket
import json


config = ConfigParser.RawConfigParser()
config.read(os.path.split(os.path.dirname(__file__))[0]+'/conf/config.ini')
config.read(os.path.split(os.path.dirname(__file__))[0]+'/conf/bigdata.ini')


riak_url = config.get('Riak', 'stats')
hostname = socket.getfqdn()
cluster_name = config.get('SelfConfig', 'cluster_name')
check_type = 'riak'


def runcheck():
    try:
        riak_stats = urllib2.urlopen(riak_url, timeout=5).read()
        sys.path.append(os.path.split(os.path.dirname(__file__))[0]+'/lib')
        jsondata=lib.pushdata.JonSon()
        jsondata.prepare_data()
        stats_json = json.loads(riak_stats)
        metrics= ('sys_process_count', 'memory_processes', 'memory_processes_used', 'node_gets', 'node_puts', 'vnode_gets', 'vnode_puts')
        for metric in metrics:
            timestamp = int(datetime.datetime.now().strftime("%s"))
            if metric is 'node_gets':
                myvalue = stats_json[metric]/60
            elif metric is 'node_puts':
                myvalue = stats_json[metric]/60
            elif metric is 'vnode_gets':
                myvalue = stats_json[metric]/60
            elif metric is 'vnode_puts':
                myvalue = stats_json[metric]/60
            else:
                myvalue = stats_json[metric]
            jsondata.gen_data('riak_'+metric, timestamp, myvalue, lib.pushdata.hostname, check_type, cluster_name)
        jsondata.put_json()
    except Exception as e:
        lib.pushdata.print_error(__name__ , (e))
        pass


