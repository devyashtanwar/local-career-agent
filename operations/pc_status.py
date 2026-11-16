"""Read-only telemetry from fixed Linux paths and commands; no user arguments."""
import csv,datetime,io,json,math,os,shutil,subprocess
from pathlib import Path
UNITS=('career-openclaw.service','career-traefik.service','career-local-model.service','career-rootless-docker.service')
GPU_COMMAND=('/usr/bin/nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits')
SERVICE_COMMAND=('/usr/bin/systemctl','--user','is-active','--',*UNITS)
STATES={'active','inactive','failed','activating','deactivating','reloading','maintenance','unknown'}
def memory_from_text(text):
    values={}
    for line in text.splitlines():
        key,_,rest=line.partition(':')
        if key in ('MemTotal','MemAvailable'):
            try:values[key]=int(rest.strip().split()[0])
            except (ValueError,IndexError):raise ValueError('invalid memory')
    total=values.get('MemTotal',0);available=values.get('MemAvailable',-1)
    if total<=0 or not 0<=available<=total:raise ValueError('invalid memory')
    return {'total_gib':round(total/1048576,2),'available_gib':round(available/1048576,2),'used_gib':round((total-available)/1048576,2)}
def number(text):
    if text.strip() in ('N/A','[N/A]','[Not Supported]'):return None
    value=float(text)
    if not math.isfinite(value) or value<0:raise ValueError('invalid GPU reading')
    return value
def parse_gpus(text):
    if len(text)>8192:raise ValueError('oversized GPU output')
    rows=list(csv.reader(io.StringIO(text),skipinitialspace=True));devices=[]
    if not rows or len(rows)>8:raise ValueError('invalid GPU row count')
    for row in rows:
        if len(row)!=5:raise ValueError('invalid GPU columns')
        name=row[0].strip()
        if not name or len(name)>100 or any(ord(c)<32 for c in name):raise ValueError('invalid GPU name')
        used,total,utilization,temperature=map(number,row[1:])
        if total is not None and used is not None and (total<=0 or used>total):raise ValueError('invalid GPU memory')
        if utilization is not None and utilization>100:raise ValueError('invalid GPU utilization')
        if temperature is not None and temperature>150:raise ValueError('invalid GPU temperature')
        devices.append(dict(name=name,memory_used_mib=used,memory_total_mib=total,utilization_percent=utilization,temperature_c=temperature))
    return devices
def run_fixed(command):
    if command not in (GPU_COMMAND,SERVICE_COMMAND):raise ValueError('command not allowlisted')
    return subprocess.run(command,capture_output=True,text=True,timeout=3,check=False,shell=False)
def collect(run=run_fixed,read=lambda path:Path(path).read_text(),disk=shutil.disk_usage,load=os.getloadavg):
    report={'collected_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'action_authorized':False}
    for key,reader in [('memory',lambda:memory_from_text(read('/proc/meminfo'))),('uptime_seconds',lambda:float(read('/proc/uptime').split()[0])),('load_1m',lambda:float(load()[0]))]:
        try:
            value=reader()
            if isinstance(value,float) and (not math.isfinite(value) or value<0):raise ValueError('invalid host reading')
            report[key]=value
        except (OSError,ValueError,IndexError):report[key]=None
    try:
        usage=disk(Path.home())
        if not 0<=usage.free<=usage.total or usage.total<=0:raise ValueError('invalid disk reading')
        report['disk']={name:round(getattr(usage,name)/1024**3,2) for name in ('total','used','free')}
    except (OSError,ValueError):report['disk']=None
    try:
        result=run(GPU_COMMAND)
        if result.returncode!=0:raise ValueError('GPU unavailable')
        report['gpu']={'available':True,'devices':parse_gpus(result.stdout),'error':None}
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:
        report['gpu']={'available':False,'devices':[],'error':'timeout' if isinstance(error,subprocess.TimeoutExpired) else 'unavailable'}
    report['services']={unit:'unavailable' for unit in UNITS}
    try:
        states=run(SERVICE_COMMAND).stdout.splitlines()
        if len(states)!=len(UNITS) or any(s not in STATES for s in states):raise ValueError('invalid services')
        report['services']=dict(zip(UNITS,states))
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return report
def display(report):
    def v(value,suffix=''):return 'unknown' if value is None else str(value)+suffix
    uptime=report['uptime_seconds'];memory=report['memory'];disk=report['disk'];gpu=report['gpu']
    lines=['PC status (read-only)','Collected: '+report['collected_at_utc'],'Uptime: '+v(round(uptime/3600,1) if uptime is not None else None,' hours'),'CPU load (1 minute): '+v(report['load_1m'])]
    lines.append('RAM: '+(str(memory['used_gib'])+' / '+str(memory['total_gib'])+' GiB used; '+str(memory['available_gib'])+' GiB available' if memory else 'unavailable'))
    lines.append('Home filesystem: '+(str(disk['free'])+' / '+str(disk['total'])+' GiB free' if disk else 'unavailable'))
    if gpu['available']:
        for d in gpu['devices']:lines.append('GPU: '+d['name']+'; VRAM '+v(d['memory_used_mib'])+' / '+v(d['memory_total_mib'])+' MiB; use '+v(d['utilization_percent'],'%')+'; '+v(d['temperature_c'],' C'))
    else:lines.append('GPU: '+gpu['error'])
    lines.append('Services:');lines.extend(unit.removesuffix('.service')+': '+state for unit,state in report['services'].items())
    lines.append('Service state does not establish model readiness. No system changes performed.')
    return '\n'.join(lines)
if __name__=='__main__':
    report=collect();print(json.dumps({'text':display(report),'report':report,'action_authorized':False}))
