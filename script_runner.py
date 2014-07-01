import json, time, requests, subprocess, os, glob, shutil
from os import path
from Queue import Empty
from IPython.nbformat.current import reads, NotebookNode
try:
    from IPython.kernel import KernelManager
except ImportError:
    # IPython 0.13
    from IPython.zmq.blockingkernelmanager import BlockingKernelManager as KernelManager


def authenticate(token, user, passw, env='prod'):
    ''' Checks the validity of the authentication token. Returns None if not valid 
    Production env only for now '''
    
    if env == 'prod' or env == 'dw_prod':
        base = 'https://api.appnexus.com'
    elif env == 'sand' or env == 'dw_sand':
        base = 'http://sand.api.appnexus.com'
    elif env == 'ctest' or env == 'dw_ctest':
        base = 'http://api-console.client-testing.adnxs.net'
    elif env == 'stage' or env == 'dw_stage':
        base = 'http://dw-api.stage.adnxs.net'

    elif env == 'api_prod':
        base = 'http://api.adnxs.com'
    elif env == 'api_sand':
        base = 'http://api.sand-08.adnxs.net'
    elif env == 'api_ctest':
        base = 'http://api-impbus.client-testing.adnxs.net'
    elif env == 'api_stage':
        base = 'http://ib.stage.adnxs.net'

    else:
        return None

    if token:
        url = base + '/user?current'
        headers = {'Authorization':  token}
        
        try:
            # resp = anx_get('dw-prod','user?current', token=token)
            resp = requests.get(url, headers=headers)
            resp = json.loads(resp.text)['response']
        except Exception, e:
            return None
        else:
            if resp.get('error_id') in ['UNAUTH', 'NOAUTH']:
                return None
            if resp['status'] == 'OK':
                return token
            else:
                return None
    
    if user and passw:
        query = {"auth":{"username":user,"password":passw}}
        url = base + '/auth'
        
        try:
            resp = requests.post(url, data=json.dumps(query))
            resp = json.loads(resp.text)['response']
        except Exception, e:
            return None
        else:
            if resp.get('error_id') == 'UNAUTH':
                return None

            if resp['status'] == 'OK':
                token = str(resp['token'])
                return token
            else:
                return None
    return None


def nb_format(ipynb, include_dir=True):
    ''' Takes in the full file location of the ipython notebook config file 
    and returns configuration dict for the input form '''
    script = ipynb.split('/')
    script = script[len(script)-1][:-6]
    if include_dir:
        script = 'scripts/' + script

    config_dict = {'link':script, 'params':[]}
    nb_json = None

    try:
        with open(ipynb, 'r+') as file:
            nb_json = file.read()
    except IOError:
        return None
    if not nb_json:
        return None
    nb_dict = json.loads(nb_json)

    nb_dict = nb_dict['worksheets'][0]['cells'][0]
    if not 'source' in nb_dict:
        return None
    rawlist = nb_dict['source']
    # pre-process
    for i,row in enumerate(rawlist):
        if row[-1] == '\n':
            rawlist[i] = rawlist[i][:-1]

    # list of raw text
    for row in rawlist:
        words = row.split('|')
        if words[0] == 'title':
            config_dict['title'] = words[1]
        elif words[0] == 'wiki':
            config_dict['wiki'] = words[1]
        elif words[0] == 'description':
            config_dict['description'] = words[1]
        elif words[0] == 'team':
            config_dict['team'] = words[1]
        elif words[0] == 'category':
            config_dict['category'] = words[1]
        elif words[0] == 'download':
            config_dict['download'] = words[1]
        else:
            if len(words) > 2:
                param = {'key':words[0], 'type':words[1], 'label':words[2]}
            else:
                continue

            if len(words) > 3:
                param['value'] = words[3]

            config_dict['params'].append(param)

    return config_dict


def run_notebook(nb, init_code, script, show_code=False, download=None):
    ''' Run the ipython notebook code, with the initializing lines of code determined by the 
    config cell. Download is the name of a list, dict, or dataFrame that will be downloaded as a csv file. '''
    # adapted from : https://github.com/ipython/ipython/wiki/Cookbook%3a-Notebook-utilities

    km = KernelManager()
    kernelid = km.start_kernel(extra_arguments=['--pylab=inline'], stderr=open(os.devnull, 'w'))

    try:
        kc = km.client()
        kc.start_channels()
        iopub = kc.iopub_channel
    except AttributeError:
        # IPython 0.13
        kc = km
        kc.start_channels()
        iopub = kc.sub_channel
    shell = kc.shell_channel

    # run %pylab inline, because some notebooks assume this
    # even though they shouldn't
    msgid = shell.execute("pass")
    m = shell.get_msg(block=True, timeout=2) # hangs forever

    clear_outputs = False
    cells_ = 0
    
    while True:
        try:
            iopub.get_msg(timeout=1)
        except Empty:
            break

    # assemble the initial parameters + link config
    init_code.insert(0, "# Inital parameters")
    init_code.append('# auto-import Link')
    init_code.append('from link import Link')
    init_code.append('lnk = Link("'+ os.getcwd() +'/.link/link.config")')
    init_code = '\n'.join(init_code)
    init_cell = {
        'cell_type':'code',
        'collapsed':'false',
        'input':init_code,
        'language':'python',
        'metadata':{},
        'outputs':[]
    }
    init_cell['outputs'] = run_cell(shell, iopub, init_cell)

    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type != 'code':
                continue
            if clear_outputs:
                cell.outputs = []
                continue

            try:
                cell.outputs = run_cell(shell, iopub, cell)
                cells_ += 1
            except Exception as e:
                cell.outputs =  "failed to run cell: " + repr(e)
                clear_outputs = True
                continue

    # print "Executed notebook %s" % nb.metadata.name
    # print "    %3i cells successfully run" % cells_
    nb.worksheets[0].cells[0] = init_cell

    # add code to download the variable to a csv file
    download_file = None
    if download and not clear_outputs:
        stamp = time.time()
        download_file = os.getcwd() + '/public/static/' + script + str(stamp) + '_tmp.csv'
        end_code = [
            "# Extra code to download the result as a csv file",
            "",
            "try:",
            "    "+ download +"",
            "except NameError:",
            "    "+ download +" = None",
            "",
            "from pandas import *",
            "if isinstance("+ download +", list):",
            "    "+ download +" = DataFrame("+ download +")",
            "elif isinstance("+ download +", dict):",
            "    "+ download +" = DataFrame(["+ download +"])",
            "elif isinstance("+ download +", basestring):",
            "    "+ download +" = DataFrame([ str("+ download +") ])",
            "",
            "if not isinstance("+ download +", DataFrame):",
            "    "+ download +" = DataFrame(['Variable not found or wrong type'])",
            "",
            ""+ download +".to_csv('"+ download_file +"')",
            "import IPython.core.display as d",
            "print 'This is a preview. For the full results, please click the download button in the upper right corner.'",
            "d.HTML( "+ download +".head().to_html() )"
        ]
        end_code = '\n'.join(end_code)

        end_cell = {
            'cell_type':'code',
            'collapsed':'false',
            'input':end_code,
            'language':'python',
            'metadata':{},
            'outputs':[]
        }
        end_cell['outputs'] = run_cell(shell, iopub, end_cell)
        nb.worksheets[len(nb.worksheets) - 1].cells.append(end_cell)

    kc.stop_channels()
    km.shutdown_kernel()
    del km

    if not show_code:
        nb = nb_scrubber(nb)

    return (nb, download_file)


def run_cell(shell, iopub, cell):
    # print cell.input
    shell.execute(cell['input'])
    # wait for finish, maximum 30s
    shell.get_msg(timeout=30)
    outs = []
    
    while True:
        try:
            msg = iopub.get_msg(timeout=0.2)
        except Empty:
            break
        msg_type = msg['msg_type']
        if msg_type in ('status', 'pyin'):
            continue
        elif msg_type == 'clear_output':
            outs = []
            continue
        
        content = msg['content']
        # print msg_type, content
        out = NotebookNode(output_type=msg_type)
        
        if msg_type == 'stream':
            out.stream = content['name']
            out.text = content['data']
        elif msg_type in ('display_data', 'pyout'):
            out['metadata'] = content['metadata']
            for mime, data in content['data'].iteritems():
                attr = mime.split('/')[-1].lower()
                # this gets most right, but fix svg+html, plain
                attr = attr.replace('+xml', '').replace('plain', 'text')
                setattr(out, attr, data)
            if msg_type == 'pyout':
                out.prompt_number = content['execution_count']
        elif msg_type == 'pyerr':
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']
        else:
            raise Exception("unhandled iopub msg: " + msg_type)
        
        outs.append(out)
    return outs


def format_init_code(obj, config, token, env):
    ''' Format the initializing code based off of the page request, 
        config dict, auth token, and the API environment '''
    init_code = []

    # api.appnexus.com sand.api.appnexus.com api-console.client-testing.adnxs.net 
    # api.adnxs.com api.sand-08.adnxs.net api-impbus.client-testing.adnxs.net
    if env == 'prod' or env == 'dw_prod':
        anxpy_env = 'api.appnexus.com'
        anxapi_env = 'dw-prod'
    elif env == 'sand' or env == 'dw_sand':
        anxpy_env = 'sand.api.appnexus.com'
        anxapi_env = 'dw-sand'
    elif env == 'ctest' or env == 'dw_ctest':
        anxpy_env = 'api-console.client-testing.adnxs.net'
        anxapi_env = 'dw-clienttesting'
    elif env == 'stage' or env == 'dw_stage':
        anxpy_env = 'dw-api.stage.adnxs.net'
        anxapi_env = 'dw-stage'

    elif env == 'api_prod':
        anxpy_env = 'api.adnxs.com'
        anxapi_env = 'ib-prod'
    elif env == 'api_sand':
        anxpy_env = 'api.sand-08.adnxs.net'
        anxapi_env = 'ib-sand'
    elif env == 'api_ctest':
        anxpy_env = 'api-impbus.client-testing.adnxs.net'
        anxapi_env = 'ib-clienttesting'
    elif env == 'api_stage':
        anxpy_env = 'ib.stage.adnxs.net'
        anxapi_env = 'ib-stage'
    else:
        anxpy_env = ''
        anxapi_env = ''


    init_code.append("token = '" + str(token) + "'")
    init_code.append("anxpy_env = '" + str(anxpy_env) + "'")
    init_code.append("anxapi_env = '" + str(anxapi_env) + "'")

    for key in obj.request.arguments:
        if key == 'username' or key == 'password':
            continue

        value = obj.get_argument(key)
        for param in config['params']:
            if param['key'] == key:
                if param['type'] == 'number':
                    init_code.append(key + " = " + str(value))
                else:
                    init_code.append(key + " = '" + str(value) + "'")
                break

    return init_code


def render_notebook(nb, script, folder, full_dir=True):
    ''' Write the ipython notebook json to file, render it as a html page,
    and delete the notebook '''
    # adapted from : http://ipython.org/ipython-doc/stable/interactive/nbconvert.html#nbconvert

    cdir = os.getcwd()
    # write to tmp file
    stamp = time.time()
    tmp_full = path.join(folder, script + str(stamp) + '_tmp.ipynb')
    output = script + str(stamp) + '_tmp.html'
    output_full = path.join(cdir, output)
    
    with open(tmp_full, 'w+') as f:
        nb_json = json.dumps(nb, indent=1)
        f.write(nb_json)

    # ipython nbconvert --to html --template full test.ipynb
    args = ['ipython', 'nbconvert', '--to', 'html', '--template', 'full', tmp_full]
    result = subprocess.call(args)
    # s = subprocess.Popen(args, stdout=subprocess.PIPE)
    
    if not path.isfile(output_full):
        raise Exception('html failed to generate')
    # remove temporary ipynb file
    try:
        os.remove(tmp_full)
    except OSError:
        pass
    # move the html file to public/static
    shutil.move(output_full, os.getcwd() + '/public/static/')

    if full_dir:
        return os.getcwd() + '/public/static/' + output
    else:
        return output


def render_notebook_text(nb):
    ''' Aggregate all of the output results in an ipython notebook '''
    outputs = {}
    row = 0
    for ws in nb.worksheets:
        for cell in ws.cells:
            row += 1
            if cell.get('cell_type') == 'code':
                if cell['outputs']:
                    output_text = []
                    for output_row in cell['outputs']:
                        output_text.extend(output_row['text'])
                    outputs[row] = output_text

    return outputs



def format_response(data, message=None):
    ''' Format the json Rest API resonse '''
    if data:
        response = {
            "status": "success",
            "data": data,
            "message": message
        }
    else:
        response = {
            "status": "error",
            "data": None,
            "message": message
        }
    return json.dumps(response)


def nb_scrubber(nb):
    ''' Remove all code inputs from an ipython notebook '''
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.get('cell_type') == 'code':
                cell['input'] = []

    return nb

