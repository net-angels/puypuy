import datetime
import lib.getconfig
import lib.pushdata

cluster_name = lib.getconfig.getparam('SelfConfig', 'cluster_name')
host_group = lib.getconfig.getparam('SelfConfig', 'host_group')

reaction = -3
warn_level = 90
crit_level = 100

def runcheck():

    cpucount = 0
    procstats = open("/proc/stat", "r")
    for line in procstats.xreadlines():
        if 'cpu' in line:
            cpucount += 1
    cpucount -= 1
    procstats.close()
    check_type = 'system'
    jsondata=lib.pushdata.JonSon()
    jsondata.prepare_data()
    timestamp = int(datetime.datetime.now().strftime("%s"))

    try:
        loadavg = open("/proc/loadavg", "r")
        proc_loadavg = loadavg.readline().split()

        def send_special():
            curr_level = float(proc_loadavg[0]) * 100 / cpucount
            if curr_level < warn_level:
                health_value = 0
                err_type = 'OK'
            if curr_level >= warn_level < crit_level:
                health_value = 8
                err_type = 'WARNING'
            if curr_level >= crit_level:
                health_value = 16
                err_type = 'ERROR'
            health_message = err_type + ': System Load average is at ' + str(curr_level) + ' percent of available  resources'
            jsondata.send_special("Load-Average", timestamp, health_value, health_message, err_type)
        send_special()

        jsondata.gen_data('sys_load_1', timestamp, proc_loadavg[0], lib.pushdata.hostname, check_type, cluster_name)
        jsondata.gen_data('sys_load_5', timestamp, proc_loadavg[1], lib.pushdata.hostname, check_type, cluster_name, reaction)
        jsondata.gen_data('sys_load_15', timestamp, proc_loadavg[2], lib.pushdata.hostname, check_type, cluster_name, reaction)

        jsondata.put_json()
        loadavg.close()

    except Exception as e:
        lib.pushdata.print_error(__name__ , (e))
        pass