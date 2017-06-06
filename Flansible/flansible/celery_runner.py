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

        playstarted = 0
        taskstarted = 0
        totalTaskTime = 0

        # task name match
        tmatch = ''
        taskName = re.compile('TASK \[(\w+[\s+\w+]+)]')
        playName = re.compile('PLAY \[(\w+[\s+\w+]+)]')

        for line in iter(proc.stdout.readline, ''):
            #print(str(line))
            if re.match('^TASK', line):
                taskstarted = "{:0.2f}".format( time.time())
                p = taskName.match(line)
                if p:
                    # Check for previous runtime in rdis
                    tmatch = p.group(1)
                    print(tmatch)
                    # found previous runtime
                    if rdis.exists(tmatch):
                        # number of times run
                        countkey = tmatch + "_count"
                        rdis.incr(countkey)

                        avg =  "{:0.2f}".format( float(rdis.get(tmatch)) / float(rdis.get(countkey)))
                        line = line.replace('\n', '')
                        line = str.format("{0} (Avg {1} secs, {2} runs) \n", line, avg, rdis.get(countkey))

            if re.match('^[ok|changed|fatal]', line):
                totalTaskTime  =  float("{:0.2f}".format((time.time() - float(taskstarted))))

                if not rdis.exists(tmatch):
                    rdis.set(tmatch, float(totalTaskTime))

                # Update rdis task total time
                ttime = float("{:0.2f}".format(float(rdis.get(tmatch))))
                rdis.set(tmatch, float(ttime) + float(totalTaskTime) )

                # remove last new line
                line = line.replace('\n', '')

                diffsign = ''
                diffval = 0

                avgtime = ttime / float(rdis.get(countkey))

                if avgtime < totalTaskTime :
                    diffsign = "+"
                    diffval =  float("{:0.2f}".format( (totalTaskTime - avgtime) ))

                elif avgtime > totalTaskTime :
                    diffsign = "-"
                    diffval =  float("{:0.2f}".format((avgtime - totalTaskTime)))
                

                line = str.format("{0} : <strong>{1} seconds</strong>  ({2}{3} secs)\n", line, totalTaskTime , diffsign, diffval)
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
