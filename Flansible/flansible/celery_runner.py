from celery import Celery
import subprocess
from subprocess import Popen, PIPE
from flansible import api, app, celery, task_timeout
import time
import re


@celery.task(bind=True, soft_time_limit=task_timeout, time_limit=(task_timeout+10))
def do_long_running_task(self, cmd, type='Ansible'):
    with app.app_context():
        
        has_error = False
        result = None
        output = ""
        self.update_state(state='PROGRESS',
                          meta={'output': output, 
                                'description': "",
                                'returncode': None})
        print(str.format("About to execute: {0}", cmd))
        proc = Popen([cmd], stdout=PIPE, stderr=subprocess.STDOUT, shell=True)

        started = 0
        ended= 0

        for line in iter(proc.stdout.readline, ''):
            print(str(line))
            if re.match('^TASK', line):
                started = time.time()
            if re.match('^[ok|changed|fatal]', line):
                ended = time.time() - started
                # remove last new line
                line = line.replace('\n', '')
                #output = output[:-1] + str.format(" # {0} seconds\n", ended)
                line = str.format("{0} : {1} seconds \n", line, ended)

            output = output + line
            self.update_state(state='PROGRESS', meta={'output': output,'description': "",'returncode': None})

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
