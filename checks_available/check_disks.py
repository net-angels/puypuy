import lib.getconfig
import lib.pushdata
import lib.record_rate
import subprocess
import datetime
import os
import re

cluster_name = lib.getconfig.getparam('SelfConfig', 'cluster_name')
check_type = 'system'

reaction = -3
warn_percent = 80
rated = True
io_warning_percent = 40


def runcheck():
    local_vars = []
    jsondata = lib.pushdata.JonSon()
    jsondata.prepare_data()
    rate = lib.record_rate.ValueRate()
    timestamp = int(datetime.datetime.now().strftime("%s"))
    devices_blocks = {}
    try:
        for device in os.listdir('/sys/block'):
            if 'ram' not in device and 'loop' not in device:
                devblk = open('/sys/block/'+device+'/queue/hw_sector_size', 'r')
                devices_blocks[device] = devblk.readline().rstrip('\n')
                devblk.close()

        for key, value in list(devices_blocks.items()):
            statsfile = open('/sys/block/' + key + '/stat', 'r')
            stats = statsfile.readline().split()
            read_bytes = int(stats[2]) * int(value)
            write_bytes = int(stats[6]) * int(value)
            reads = 'drive_' + key + '_bytes_read'
            writes = 'drive_' + key + '_bytes_write'
            if rated is True:
                read_rate = rate.record_value_rate(reads, read_bytes, timestamp)
                write_rate = rate.record_value_rate(writes, write_bytes, timestamp)
                local_vars.append({'name': reads, 'timestamp': timestamp, 'value': read_rate, 'reaction': reaction})
                local_vars.append({'name': writes, 'timestamp': timestamp, 'value': write_rate, 'reaction': reaction})

            else:
                local_vars.append({'name': reads, 'timestamp': timestamp, 'value': read_bytes, 'reaction': reaction})
                local_vars.append({'name': writes, 'timestamp': timestamp, 'value': write_bytes, 'reaction': reaction})

            statsfile.close()

        d = []
        mount = open('/proc/mounts', 'r')

        for l in mount:
            if l[0] == '/':
                l = l.split()
                d.append(l[1])

        mount.close()

        def disk_usage(path):
            st = os.statvfs(path)
            free = st.f_bavail * st.f_frsize
            total = st.f_blocks * st.f_frsize
            used = (st.f_blocks - st.f_bfree) * st.f_frsize
            du = '{:.2f}'.format(used * 100 / float(total))
            return total, used, free, du

        for u in d:
            mrtrics = disk_usage(u)
            if u == '/':
                name = '_rootfs'
            else:
                name = u.replace('/', '_')

            local_vars.append({'name': 'drive' + name + '_bytes_used', 'timestamp': timestamp, 'value': mrtrics[1], 'reaction': reaction})
            local_vars.append({'name': 'drive' + name + '_bytes_available', 'timestamp': timestamp, 'value': mrtrics[2], 'reaction': reaction})
            local_vars.append({'name': 'drive' + name + '_percent_used','timestamp': timestamp, 'value': mrtrics[3], 'chart_type': 'Percent'})
            # print(disk_usage(u))


        proc_stats = open('/proc/diskstats')
        for line in proc_stats:
            if "loop" not in line:
                fields = line.strip().split()
                name = 'drive_'+fields[2]+'_io_percent'
                regexp = re.compile(r'\d')
                if regexp.search(name) is None:
                    value = fields[12]
                    reqrate = rate.record_value_rate(name, value, timestamp)
                    if isinstance(reqrate, int):
                        diskrate = reqrate/10
                        local_vars.append({'name': name, 'timestamp': timestamp, 'value': diskrate,  'chart_type': 'Percent'})
        proc_stats.close()
        return  local_vars
    except Exception as e:
        lib.pushdata.print_error(__name__ , (e))
        pass


