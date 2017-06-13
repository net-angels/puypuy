import lib.record_rate
import lib.pushdata
import lib.commonclient
import lib.puylogger
import lib.getconfig
import datetime
import json


hbase_region_url = lib.getconfig.getparam('HBase-Region', 'jmx')
cluster_name = lib.getconfig.getparam('SelfConfig', 'cluster_name')
check_type = 'hbase'

def runcheck():
    try:
        stats_json = json.loads(lib.commonclient.httpget(__name__, hbase_region_url))
        stats_keys = stats_json['beans']
        node_rated_keys=('totalRequestCount','readRequestCount','writeRequestCount', 'Delete_num_ops', 'Mutate_num_ops', 'FlushTime_num_ops',
                         'GcTimeMillis','compactedCellsCount', 'majorCompactedCellsCount', 'compactedCellsSize', 'majorCompactedCellsSize',
                         'blockCacheHitCount', 'blockCacheMissCount', 'blockCacheEvictionCount')
        node_stuck_keys=('GcCount','HeapMemoryUsage', 'OpenFileDescriptorCount', 'blockCacheCount')
        rate=lib.record_rate.ValueRate()
        jsondata=lib.pushdata.JonSon()
        jsondata.prepare_data()
        timestamp = int(datetime.datetime.now().strftime("%s"))

        for stats_x in range(0, len(stats_keys)):
            for k, v in enumerate(('java.lang:type=GarbageCollector,name=ConcurrentMarkSweep', 'java.lang:type=GarbageCollector,name=ParNew')):
                if v in stats_keys[stats_x]['name']:
                    if k is 0:
                        cms_key='hregion_heap_cms_lastgcinfo'
                        cms_value=stats_keys[stats_x]['LastGcInfo']['duration']
                        jsondata.gen_data(cms_key, timestamp, cms_value, lib.pushdata.hostname, check_type, cluster_name)
                    if k is 1:
                        parnew_key='hregion_heap_parnew_lastgcinfo'
                        parnew_value=stats_keys[stats_x]['LastGcInfo']['duration']
                        jsondata.gen_data(parnew_key, timestamp, parnew_value, lib.pushdata.hostname, check_type, cluster_name)

        for stats_x in range(0, len(stats_keys)):
            for k, v in enumerate(('java.lang:type=GarbageCollector,name=G1 Young Generation', 'java.lang:type=GarbageCollector,name=G1 Old Generation')):
                if v in stats_keys[stats_x]['name']:
                    if k is 0:
                        g1_young_key='hregion_heap_g1_young_lastgcinfo'
                        g1_young_value=stats_keys[stats_x]['LastGcInfo']['duration']
                        jsondata.gen_data(g1_young_key, timestamp, g1_young_value, lib.pushdata.hostname, check_type, cluster_name)
                    if k is 1:
                        if stats_keys[stats_x]['LastGcInfo'] is not None:
                            g1_old_key='hregion_heap_g1_old_lastgcinfo'
                            g1_old_value=stats_keys[stats_x]['LastGcInfo']['duration']
                            jsondata.gen_data(g1_old_key, timestamp, g1_old_value, lib.pushdata.hostname, check_type, cluster_name)
                        else:
                            g1_old_key='hregion_heap_g1_old_lastgcinfo'
                            g1_old_value=0
                            jsondata.gen_data(g1_old_key, timestamp, g1_old_value, lib.pushdata.hostname, check_type, cluster_name)

        for stats_index in range(0, len(stats_keys)):
            for values in node_rated_keys:
                if values in stats_keys[stats_index]:
                    if values in node_rated_keys:
                        myvalue=stats_keys[stats_index][values]
                        values_rate=rate.record_value_rate('hregion_'+values, myvalue, timestamp)
                        if values_rate >= 0:
                            jsondata.gen_data('hregion_node_'+values.lower(), timestamp, values_rate, lib.pushdata.hostname, check_type, cluster_name, 0, 'Rate')

            for values in node_stuck_keys:
                if values in stats_keys[stats_index]:
                    if values == 'HeapMemoryUsage':
                        heap_metrics=('max', 'init', 'committed', 'used')
                        for heap_values in heap_metrics:
                            jsondata.gen_data('hregion_heap_'+heap_values.lower(), timestamp, stats_keys[stats_index][values][heap_values], lib.pushdata.hostname, check_type, cluster_name)
                    elif values == 'GcCount':
                        jsondata.gen_data('hregion_node_' + values.lower(), timestamp, stats_keys[stats_index][values], lib.pushdata.hostname, check_type, cluster_name, -3)
                    else:
                        jsondata.gen_data('hregion_node_'+values.lower(), timestamp, stats_keys[stats_index][values], lib.pushdata.hostname, check_type, cluster_name)

        jsondata.put_json()
    except Exception as e:
        lib.puylogger.print_message(__name__ + ' Error : ' + str(e))
        pass
