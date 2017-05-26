import datetime
import lib.getconfig
import lib.pushdata
import lib.record_rate

cluster_name = lib.getconfig.getparam('SelfConfig', 'cluster_name')
host_group = lib.getconfig.getparam('SelfConfig', 'host_group')

# ---------------------- #
rated = True
#reaction = -3
values_type = 'Percent'
warn_level = 90
crit_level = 100
# ---------------------- #

'''
0: user: normal processes executing in user mode
1: nice: niced processes executing in user mode
2: system: processes executing in kernel mode
3: idle: twiddling thumbs
4: iowait: waiting for I/O to complete
5: irq: servicing interrupts
6: softirq: servicing softirqs
'''

def runcheck():
    check_type = 'system'
    jsondata=lib.pushdata.JonSon()
    jsondata.prepare_data()
    rate=lib.record_rate.ValueRate()
    timestamp = int(datetime.datetime.now().strftime("%s"))

    cpucount = 0
    with open("/proc/stat", "r") as crn:
        cpu_stats = [float(column) for column in crn.readline().strip().split()[1:]]
        for line in crn.readlines():
            if 'cpu' in line:
                cpucount += 1
    crn.close()

    metrinames=['cpu_user', 'cpu_nice', 'cpu_system', 'cpu_idle', 'cpu_iowait', 'cpu_irq', 'cpu_softirq']

    try:
        for index in range(0, 7):
            name = metrinames[index]
            value = cpu_stats[index]
            if name == 'cpu_user' or name == 'cpu_iowait':
                reaction = 0
            else:
                reaction = -3
            if rated is True:
                values_rate = rate.record_value_rate(name, value, timestamp)/cpucount
                jsondata.gen_data(name, timestamp, values_rate, lib.pushdata.hostname, check_type, cluster_name, reaction, values_type)
            else:
                jsondata.gen_data(name, timestamp, int(value)/cpucount, lib.pushdata.hostname, check_type, cluster_name, reaction, values_type)


        jsondata.put_json()
    except Exception as e:
        lib.pushdata.print_error(__name__ , (e))
        pass
