from IPython.nbformat.current import reads, read
from runipy.notebook_runner import NotebookRunner
import json
import ast
import os


def convert_to_endpoint(string, is_filename=True):
    # remove extension
    if is_filename:
        string = string.partition('.')[0]

    ''.join(e for e in string if e.isalnum())

    string = string.replace('_', '-').lower()
    string = string.replace(' ', '-').lower()

    return string


def nb_config_list(nb_dir):
    # get list of available notebooks to populate navbar

    config_list = []
    for nb_filename in os.listdir(nb_dir):
        if '.ipynb' in nb_filename and 'ipynb_checkpoints' not in nb_filename:
            nb = NotebookObject(nb_dir + nb_filename)
            config_dict = nb.get_nb_config()
            if config_dict:
                config_dict['nb_endpoint'] = convert_to_endpoint(config_dict['nb_filename'])
                config_list.append(config_dict)

    return config_list


class NotebookObject(object):
    """
    Represents a ipython notebook (.ipynb file)
    """

    def __init__(self, nb_file):
        self.nb_file = nb_file
        self.nb_obj = read(open(nb_file), 'json')

        NotebookObject.refresh(self)

    def save(self, save_path=None):
        """
        Saves the notebook to a given path
        """

        with open(save_path, "w") as f:
            f.write(json.dumps(self.nb_obj))

    def refresh(self):
        """
        Updates the nb object after any modifications
        """
        self.cells = self.nb_obj['worksheets'][0]['cells']

        self.cells_inputs = []
        for cell in self.cells:
            try:
                self.cells_inputs.append(cell['input'])
            except KeyError:
                self.cells_inputs.append(cell['source'])

        self.cells_outputs = []
        for cell in self.cells:
            try:
                if cell['outputs']:
                    if len(cell['outputs']) > 1:    # sloppy way to infer that cell output is a plot
                        self.cells_outputs.append('<img src="data:image/png;base64,' + cell['outputs'][1]['png'] + '"/>')
                    else:
                        try:
                            self.cells_outputs.append(cell['outputs'][0]['text'])
                        except KeyError:
                            self.cells_outputs.append("Error: {}: {}".format(cell['outputs'][0]['ename'],
                                                                             cell['outputs'][0]['evalue']))
            except KeyError:
                continue

    def get_nb_config(self):
        """
        Checks first cell to see if nb_config is present. Will return None if not
        """
        nb_config = self.cells[0]['input']

        try:
            self.config_dict = ast.literal_eval(nb_config)
        except SyntaxError:
            self.config_dict = None

        if not isinstance(self.config_dict, dict):
            self.config_dict = None

        return self.config_dict

    def insert_cell(self, content, cell_position=0):

        insert_dict = {
            u'cell_type': u'code',
            u'input': unicode(content),
            u'language': u'python',
            u'outputs': []
        }

        self.cells.insert(cell_position, insert_dict)
        self.nb_obj['worksheets'][0]['cells'] = self.cells
        self.nb_obj = reads(json.dumps(self.nb_obj), 'json')
        self.cells_inputs = [cell['input'] for cell in self.cells]

    def insert_nb_params(self, params):
        """
        Inserts params required to execute the nb
        :param params: list of dicts, where dict is {'param_name':'param_value'}

        ie: [{'member_id':1234}, {'campaign_id':987654}]
        """
        param_str = ''

        for key in params.keys():
            if isinstance(params[key], basestring):
                param_str += '{} = "{}"\n'.format(key, params[key])
            else:
                param_str += '{} = {}\n'.format(key, params[key])

        NotebookObject.insert_cell(self, param_str, cell_position=1)

    def run(self):
        r = NotebookRunner(self.nb_obj, pylab=True)
        r.run_notebook()
        self.nb_obj = r.nb
        NotebookObject.refresh(self)
