from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from notebook import *
import ast
import os

app = Flask(__name__)

nb_dir = os.getcwd() + '/notebooks/'
app.config['UPLOAD_FOLDER'] = nb_dir


@app.context_processor      # this decorator makes variables available to all jinja template
def nav_data():
    config_list = nb_config_list(nb_dir)  # TODO: understand how to declare this as global variable to avoid repeated instansiations
    nav_data = [{'nb_display_name': config['nb_display_name'],
                 'nb_endpoint': config['nb_endpoint']} for config in config_list]
    return dict(nav_data=nav_data)


@app.route('/', methods=['GET'])
def homepage():
    config_list = nb_config_list(nb_dir)
    return render_template("homepage.html", notebooks=config_list)

# Self service page for users to submit their own ipython notebooks. Converts form input to nb config which is
# then used to generate the notebook UI
@app.route('/nb-submission', methods=['GET', 'POST'])
def nb_submission():
    if request.method == 'GET':
        return render_template('nb-submission.html')
    else:
        # save uploaded script
        file = request.files['nb_file']

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        form_config = request.form.to_dict()

        # build the notebook config
        nb_config = {"nb_display_name": form_config["nb_display_name"],
                     "nb_description": form_config["nb_description"],
                     "nb_filename": filename
        }

        num_params = [key[-1] for key in form_config.keys() if 'param_name' in key and form_config[key]]

        nb_config['params'] = [{key[6:-1]: form_config[key] for key in form_config.keys() if key.endswith(num)} for num
                               in num_params]

        nb_obj = NotebookObject(nb_dir + filename)

        nb_obj.insert_cell(nb_config)

        nb_obj.save(nb_dir + filename)

        return redirect(url_for('homepage'))

# the UI for each script
@app.route('/<nb_endpoint>', methods=['GET', 'POST'])
def render_ui(nb_endpoint):
    # validate that endpoint maps to known app endpoint
    config_list = nb_config_list(nb_dir)

    if nb_endpoint not in [config['nb_endpoint'] for config in config_list]:
        return "app not found"
    else:
        config_dict = [config for config in config_list if nb_endpoint == config['nb_endpoint']][0]
        ipynb = nb_dir + config_dict['nb_filename']
        nb_obj = NotebookObject(ipynb)

        if request.method == 'GET':

            # build view of notebook contents
            cell_inputs = [highlight(cell, PythonLexer(), HtmlFormatter(style='friendly')) for cell in
                           nb_obj.cells_inputs]
            return render_template('user-ui.html', results=config_dict, inputs=cell_inputs,
                                   input_css=HtmlFormatter().get_style_defs('.highlight'))
        else:
            returned_params = request.form.to_dict()

            # coerce param values into proper data types
            for param in returned_params.keys():
                for config_param in config_dict['params']:
                    if param == config_param['name']:
                        if config_param['input_type'] == 'integer':
                            returned_params[param] = int(returned_params[param])
                        elif config_param['input_type'] == 'boolean':
                            returned_params[param] = ast.literal_eval(returned_params[param])

            nb_obj.insert_nb_params(returned_params)

            nb_obj.run()

            return render_template("nb-output.html", outputs=nb_obj.cells_outputs)


if __name__ == '__main__':
    app.run(port=8004, debug=True)
    #app.run(host='10.3.64.250', port=8004, debug=True)
