from flask_restful import Resource, Api
from flask_restful_swagger import swagger
from flask import render_template, make_response, Response
from flansible import app
from flansible import api, app, celery, auth
from ModelClasses import AnsibleCommandModel, AnsiblePlaybookModel, AnsibleRequestResultModel, AnsibleExtraArgsModel
import celery_runner
import time

class AnsibleTaskOutput(Resource):
    @swagger.operation(
    notes='Get the output of an Ansible task/job',
    nickname='ansibletaskoutput',
    parameters=[
        {
        "name": "task_id",
        "description": "The ID of the task/job to get status for",
        "required": True,
        "allowMultiple": False,
        "dataType": 'string',
        "paramType": "path"
        }
    ])
    @auth.login_required
    def get(self, task_id):
        title = "Playbook Results"
        task = celery_runner.do_long_running_task.AsyncResult(task_id)
        count = 0
        def inner():
            while task.state != 'PENDING':
                if len(task.info['output']) > 0:
                    result = task.info['output'].pop(0)
                    result = result.replace('\n', '<br>\n')
                    time.sleep(1)
                    yield result
                yield ''
                

        return Response(inner(), mimetype='text/html')
        # if task.state == 'PENDING':
        #     result = "Task not found"
        #     resp = app.make_response((result, 404))
        #     return resp
        # if task.state == "PROGRESS":
        #     result = task.info['output']
        # else:
        #     result = task.info['output']
        # result = result.replace('\n', '<br>\n')

        
        #refresh = 5

        if "RECAP" in result or "ERROR" in result:
            # disable refresh in template
            refresh = 1000

        response = make_response(render_template('status.j2', title=title, status=result, refresh=refresh))
        response.headers['Content-Type'] = 'text/html'
        return response

api.add_resource(AnsibleTaskOutput, '/api/ansibletaskoutput/<string:task_id>')
