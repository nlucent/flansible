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
        output = []
        self.update_state(state='PROGRESS',
                          meta={'output': output, 
                                'description': "",
                                'returncode': None})
        print(str.format("About to execute: {0}", cmd))
        proc = Popen([cmd], stdout=PIPE, stderr=subprocess.STDOUT, shell=True)

        started = 0
        ended= 0

        tname = ''
        taskName = re.compile('TASK \[(\w+[\s+\w+]+)]')

        for line in iter(proc.stdout.readline, ''):
            #print(str(line))
            if re.match('^TASK', line):
                started = "{:0.2f}".format( time.time())
                p = taskName.match(line)
                if p:
                    # Check for previous runtime in rdis
                    tname = p.group(1)
                    if rdis.get(tname):
                        line = line.replace('\n', '')
                        line = str.format("{0} (Avg {1} secs) \n", line, rdis.get(tname))

            if re.match('^[ok|changed|fatal]', line):
                ended = time.time() - float(started)
                ended = "{:0.2f}".format(ended)
                ttime = rdis.get(tname)
                if not ttime:
                    ttime = ended
                    rdis.set(tname, ttime)
                # remove last new line
                line = line.replace('\n', '')

                diffsign = ''
                diffval = 0

                if ttime < ended:
                    diffsign = "+"
                    diffval = float(ttime) - float(ended)

                elif ttime > ended:
                    diffsign = "-"
                    diffval = float(ended) - float(ttime)
                

                line = str.format("{0} : <strong>{1} seconds</strong>  (diff {2}{3} secs)\n", line, ended, diffsign, diffval)
               # print(line)
            #output = output + line
            output.append(line)
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
