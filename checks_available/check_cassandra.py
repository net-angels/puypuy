import datetime
import json
import lib.pushdata
import lib.getconfig
import lib.commonclient
import lib.puylogger

jolokia_url = lib.getconfig.getparam('Cassandra', 'jolokia')
cluster_name = lib.getconfig.getparam('SelfConfig', 'cluster_name')
check_type = 'cassandra'
reaction = -3

def runcheck():
    local_vars = []
    try:
        rate = lib.record_rate.ValueRate()
        timestamp = int(datetime.datetime.now().strftime("%s"))

        jolo_mbeans = ('java.lang:type=Memory', 'org.apache.cassandra.db:type=Caches',
                     'org.apache.cassandra.transport:type=Native-Transport-Requests',
                     'org.apache.cassandra.request:type=*',
                     'org.apache.cassandra.metrics:type=Compaction,name=*',
                     'org.apache.cassandra.internal:type=GossipStage')
        for beans in jolo_mbeans:
            jolo_json = json.loads(lib.commonclient.httpget(__name__, jolokia_url+'/'+beans))
            jolo_keys = jolo_json['value']
            if beans == 'org.apache.cassandra.metrics:type=Compaction,name=*':
                mon_values = jolo_keys['org.apache.cassandra.metrics:name=PendingTasks,type=Compaction']['Value']
                name = 'cassa_pending_compactions'
                local_vars.append({'name': name.lower(), 'timestamp': timestamp, 'value': mon_values, 'check_type': check_type})

            elif beans == 'org.apache.cassandra.db:type=Caches':
                needed_stats=('RowCacheHits','KeyCacheHits','RowCacheRequests','KeyCacheRequests')
                for my_name in jolo_keys:
                    my_value = jolo_keys[my_name]
                    if my_name in needed_stats and my_value > 0:
                        name = 'cassa_' + my_name
                        value_rate = rate.record_value_rate(name, my_value, timestamp)
                        local_vars.append({'name': name.lower(), 'timestamp': timestamp, 'value': value_rate, 'check_type': check_type, 'chart_type': 'Rate'})
            request_keys = ('RequestResponseStage','ReadStage','MutationStage')
            if beans == 'org.apache.cassandra.request:type=*':
                for key in request_keys:
                    name = 'cassa_' + key.lower()
                    value = jolo_keys['org.apache.cassandra.request:type='+key]['CompletedTasks']
                    value_rate = rate.record_value_rate(name, value, timestamp)
                    local_vars.append({'name': name.lower(), 'timestamp': timestamp, 'value': value_rate, 'check_type': check_type, 'chart_type': 'Rate'})
            if beans == 'org.apache.cassandra.transport:type=Native-Transport-Requests':
                name = 'cassa_native_transport_requests'
                value = jolo_json['value']['CompletedTasks']
                value_rate = rate.record_value_rate(name, value, timestamp)
                local_vars.append({'name': name.lower(), 'timestamp': timestamp, 'value': value_rate, 'check_type': check_type, 'chart_type': 'Rate'})

        data_dict = json.loads(lib.commonclient.httpget(__name__, jolokia_url + '/java.lang:type=GarbageCollector,name=*'))
        ConcurrentMarkSweep = 'java.lang:name=ConcurrentMarkSweep,type=GarbageCollector'
        G1Gc = 'java.lang:name=G1 Young Generation,type=GarbageCollector'

        if ConcurrentMarkSweep in data_dict['value']:
            CMS = True
            G1 = False
        elif G1Gc in data_dict['value']:
            CMS = False
            G1 = True
        else:
            CMS = False
            G1 = False

        heam_mem = 'java.lang:type=Memory'
        jolo_json = json.loads(lib.commonclient.httpget(__name__, jolokia_url + '/' + heam_mem))
        jolo_keys = jolo_json['value']
        metr_name = ('used', 'committed', 'max')
        heap_type = ('NonHeapMemoryUsage', 'HeapMemoryUsage')
        for heap in heap_type:
            for metr in metr_name:
                if heap == 'NonHeapMemoryUsage':
                    key = 'cassa_nonheap_' + metr
                    mon_values = jolo_keys[heap][metr]
                    if metr == 'used':
                        local_vars.append({'name': key, 'timestamp': timestamp, 'value': mon_values, 'check_type': check_type})
                    else:
                        local_vars.append({'name': key, 'timestamp': timestamp, 'value': mon_values, 'check_type': check_type, 'reaction': reaction})
                else:
                    key = 'cassa_heap_' + metr
                    mon_values = jolo_keys[heap][metr]
                    if metr == 'used':
                        local_vars.append({'name': key, 'timestamp': timestamp, 'value': mon_values, 'check_type': check_type})
                    else:
                        local_vars.append({'name': key, 'timestamp': timestamp, 'value': mon_values, 'check_type': check_type, 'reaction': reaction})
        if CMS is True:
            collector = ('java.lang:name=ParNew,type=GarbageCollector', 'java.lang:name=ConcurrentMarkSweep,type=GarbageCollector')
            for coltype in collector:
                beans = json.loads(lib.commonclient.httpget(__name__, jolokia_url + '/' + coltype))
                if beans['value']['LastGcInfo']:
                    LastGcInfo = beans['value']['LastGcInfo']['duration']
                CollectionCount = beans['value']['CollectionCount']
                CollectionTime = beans['value']['CollectionTime']

                def push_metrics(preffix):
                    local_vars.append({'name': 'cassa_' + preffix + '_collection_count', 'timestamp': timestamp, 'value': CollectionCount, 'check_type': check_type})
                    CollectionTime_rate = rate.record_value_rate('cassa_' + preffix + '_collection_time', CollectionTime, timestamp)
                    local_vars.append({'name': 'cassa_' + preffix + '_collection_time', 'timestamp': timestamp, 'value': CollectionTime_rate, 'check_type': check_type, 'chart_type': 'Rate'})
                    if 'LastGcInfo' in locals():
                        local_vars.append({'name': 'cassa_' + preffix + '_lastgcinfo', 'timestamp': timestamp, 'value': LastGcInfo, 'check_type': check_type})

                if coltype == 'java.lang:name=ConcurrentMarkSweep,type=GarbageCollector':
                    push_metrics(preffix='cms')
                if coltype == 'java.lang:name=ParNew,type=GarbageCollector':
                    push_metrics(preffix='parnew')

        if G1 is True:
            gc_g1 = ('/java.lang:name=G1%20Old%20Generation,type=GarbageCollector', '/java.lang:name=G1%20Young%20Generation,type=GarbageCollector')

            def check_null(value):
                if value is None:
                    value = 0
                    return value
                else:
                    return value

            for k, v in enumerate(gc_g1):
                j = json.loads(lib.commonclient.httpget(__name__, jolokia_url + v))
                name = 'LastGcInfo'
                if k is 0:
                    try:
                        value = j['value'][name]['duration']
                        v = check_null(value)
                    except:
                        v = 0
                        pass
                    m_name = 'cassa_G1_old_LastGcInfo'
                if k is 1:
                    value = j['value'][name]['duration']
                    v = check_null(value)
                    m_name = 'cassa_G1_young_LastGcInfo'
                local_vars.append({'name': m_name, 'timestamp': timestamp, 'value': v, 'check_type': check_type})

            metr_keys = ('CollectionTime', 'CollectionCount')
            for k, v in enumerate(gc_g1):
                j = json.loads(lib.commonclient.httpget(__name__, jolokia_url + v))
                if k is 0:
                    type = '_old_'
                if k is 1:
                    type = '_young_'
                for ky, vl in enumerate(metr_keys):
                    if ky is 0:
                        value = j['value'][vl]
                        v = check_null(value)
                        rate_key = vl + type
                        CollectionTime_rate = rate.record_value_rate('cassa_' + rate_key, v, timestamp)
                        local_vars.append({'name': 'cassa_g1' + type + vl, 'timestamp': timestamp, 'value': vl, 'check_type': check_type})
                    if ky is 1:
                        value = j['value'][vl]
                        v = check_null(value)
                        local_vars.append({'name': 'cassa_g1' + type + vl, 'timestamp': timestamp, 'value': v, 'check_type': check_type})
        jolo_threads = 'java.lang:type=Threading'
        jolo_tjson = json.loads(lib.commonclient.httpget(__name__, jolokia_url + '/' + jolo_threads))
        thread_metrics = ('TotalStartedThreadCount', 'PeakThreadCount', 'ThreadCount', 'DaemonThreadCount')
        for thread_metric in thread_metrics:
            name = 'cassa_' + thread_metric.lower()
            vlor = jolo_tjson['value'][thread_metric]
            local_vars.append({'name': name, 'timestamp': timestamp, 'value': vlor, 'check_type': check_type})

        return local_vars

    except Exception as e:
        lib.puylogger.print_message(__name__ + ' Error : ' + str(e))
        pass

