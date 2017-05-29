from flask import render_template, request, url_for, redirect
from flansible import api, app, playbook_root, auth
from run_ansible_playbook import runPlaybook
import simplejson as json
import requests
import yaml
import re
import os

def FetchYamlVars(yamlfile):
    # Read variable list  directly from playbook file
    # Inserts 'host' as first variable
    f = open(playbook_root + yamlfile)
    ymldata = yaml.safe_load(f)
    f.close()
    pbVars = ymldata[0]['vars'].keys()
    pbVars.insert(0,'host')
    return pbVars

@auth.login_required
def index():
    # Get list of allowed playbooks
    yamlfiles = []
    for root, dirs, files in os.walk(playbook_root):
        for name in files:
            if name.endswith((".yaml", ".yml")):
                yamlfiles.append(name)
    playbooks = sorted(yamlfiles)
    title = 'Choose Playbook'
    return render_template('index.j2', title=title, varlist=playbooks)

@auth.login_required
def variables():
    curPB = request.form['pbradio']
    pbVars = FetchYamlVars(curPB)

    title = 'Enter required variable values'
    return render_template('variables.j2', title=title, curPB=curPB, varlist=pbVars)

@auth.login_required
def submitPlaybook():
    # selected playbook
    curPB = request.form['playbook']
    varlist = FetchYamlVars(curPB)

    vars = {}

    # Playbook variables
    for val in varlist:
        vars[val] = request.form[val]

    pbmessage = {
        'playbook': curPB ,
        'playbook_dir': playbook_root,
        'extra_vars': vars
    }

    # Runtime variables
    try:
        inventory = request.form['inventory']
    except:
        inventory = None
    try:
        become = request.form['become']
    except:
        become = None

    if inventory:
        pbmessage['inventory'] = inventory
    if become:
        pbmessage['become'] = become
    curr_user = auth.username()
    cmdres = runPlaybook(False, curr_user, pbmessage['playbook_dir'], pbmessage['playbook'], inventory, pbmessage['extra_vars'], 1, become)
    
    if isinstance(cmdres, dict):
        if 'task_id' in cmdres:
            return redirect('/api/ansibletaskoutput/' + cmdres['task_id'])
        
    return cmdres
    #     status = requests.get('/api/ansibletaskoutput/' + taskid)

    #    # return redirect('/status/' + taskid)
    #dump message on failure
    #return json.dumps(pbmessage)


# @auth.login_required
# @app.route('/status/<taskid>')
# def get_status(taskid):
#     # Proxy and reformat execution status based on task id
#     refresh = 10
#     title = "Playbook Results"
#     status = requests.get(app.config['PBSTATUS_URL'] + taskid, auth=(app.config['PB_POST_USER'], app.config['PB_POST_PASSWD']))
#     formatted = re.sub(r"\s+TASK", "<br>TASK", status.text)

#     # playbook execution finished
#     if "RECAP" in formatted or "ERROR" in formatted:
#         # disable refresh in template
#         refresh = 1000
#     return render_template('status.j2', title=title, status=formatted, refresh=refresh)


app.add_url_rule('/', 'index', index)
app.add_url_rule('/config', 'variables', variables, methods=['POST'])
app.add_url_rule('/doit', 'submitPlaybook', submitPlaybook, methods=['POST'])
