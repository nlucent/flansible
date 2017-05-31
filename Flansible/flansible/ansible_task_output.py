from flask_restful import Resource, Api
from flask_restful_swagger import swagger
from flask import render_template, make_response
from flansible import app
from flansible import api, app, celery, auth
from ModelClasses import AnsibleCommandModel, AnsiblePlaybookModel, AnsibleRequestResultModel, AnsibleExtraArgsModel
import celery_runner

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
        task = celery_runner.do_long_running_task.AsyncResult(task_id)
        if task.state == 'PENDING':
            result = "Task not found"
            resp = app.make_response((result, 404))
            return resp
        if task.state == "PROGRESS":
            result = task.info['output']
        else:
            result = task.info['output']
        #result_out = task.info.replace('\n', "<br>")
        result = result.replace('\n', '<br>')
        #return result, 200, {'Content-Type': 'text/html; charset=utf-8'}

        title = "Playbook Results"
        refresh = 5

        if "RECAP" in result or "ERROR" in result:
            # disable refresh in template
            refresh = 1000

        response = make_response(render_template('status.j2', title=title, status=result, refresh=refresh))
        response.headers['Content-Type'] = 'text/html'
        return response
        # return render_template('status.j2',  {'Content-Type': 'text/html'}, title=title, status=task.info['output'], refresh=refresh)
        # resp = app.make_response((result, 200))
        # resp.headers['content-type'] = 'text/plain'
        # return resp

api.add_resource(AnsibleTaskOutput, '/api/ansibletaskoutput/<string:task_id>')
