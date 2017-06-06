from celery import Celery
import subprocess
from subprocess import Popen, PIPE
from flansible import api, app, celery, task_timeout
import time
import re
import redis

rdis = redis.StrictRedis(host='localhost', port=6379, db=0)

@celery.task(bind=True, soft_time_limit=task_timeout, time_limit=(task_timeout+10))
def do_long_running_task(self, cmd, type='Ansible'):
    with app.app_context():
        
        has_error = False
        result = None
        output = ''
        self.update_state(state='PROGRESS',
                          meta={'output': output, 
                                'description': "",
                                'returncode': None})
        print(str.format("About to execute: {0}", cmd))
        proc = Popen([cmd], stdout=PIPE, stderr=subprocess.STDOUT, shell=True)

        started = 0
        totaltime = 0

        # task name match
        tmatch = ''
        taskName = re.compile('TASK \[(\w+[\s+\w+]+)]')

        for line in iter(proc.stdout.readline, ''):
            #print(str(line))
            if re.match('^TASK', line):
                started = "{:0.2f}".format( time.time())
                p = taskName.match(line)
                if p:
                    # Check for previous runtime in rdis
                    tmatch = p.group(1)
                    print(tmatch)
                    if rdis.exists(tmatch):
                        avg =  "{:0.2f}".format( float(rdis.get(tmatch)))
                        line = line.replace('\n', '')
                        line = str.format("{0} (Avg {1} secs) \n", line, avg)

            if re.match('^[ok|changed|fatal]', line):
                totaltime  =  "{:0.2f}".format(time.time() - float(started))

                if not rdis.exists(tmatch):
                    rdis.set(tmatch, totaltime)

                ttime = "{:0.2f}".format(float(rdis.get(tmatch)))
                
                # remove last new line
                line = line.replace('\n', '')

                diffsign = ''
                diffval = 0

                if ttime < totaltime :
                    diffsign = "+"
                    diffval = float(ttime) - float(totaltime )

                elif ttime > totaltime :
                    diffsign = "-"
                    diffval = float(totaltime ) - float(ttime)
                

                line = str.format("{0} : <strong>{1} seconds</strong>  (diff {2}{3} secs)\n", line, totaltime , diffsign, diffval)
               # print(line)
            output = output + line
            #output.append(line)
            self.update_state(state='PROGRESS', meta={'output': output, 'description': "", 'returncode': None})

        return_code = proc.poll()
        if return_code is 0:
            meta = {'output': output, 
                        'returncode': proc.returncode,
                        'description': ""
                    }
            self.update_state(state='FINISHED',
                              meta=meta)
        elif return_code is not 0:
            #failure
            meta = {'output': output, 
                        'returncode': return_code,
                        'description': str.format("Celery ran the task, but {0} reported error", type)
                    }
            self.update_state(state='FAILED',
                          meta=meta)
        if len(output) is 0:
            output = "no output, maybe no matching hosts?"
            meta = {'output': output, 
                        'returncode': return_code,
                        'description': str.format("Celery ran the task, but {0} reported error", type)
                    }
        return meta
