import tornado.ioloop, tornado.web
from tornado.httpserver import HTTPServer
from os import path
import os
from functools import partial
from IPython.nbformat.current import reads, NotebookNode

from script_runner import *


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class TestSetupHandler(tornado.web.RequestHandler):
    def get(self):
        import sys
        msg = 'Home: ' + os.environ["HOME"]
        msg += '      \nPath: ' + os.environ["PATH"]
        msg += '      \nPrefix: ' + sys.prefix
        msg += '      \nCurrent dir: ' + os.getcwd()
        self.write(msg)

class ScriptsRedirectHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('scripts/')

class ScriptsHandler(tornado.web.RequestHandler):
    def get(self, slug=None):
        script = slug

        if not script:
            src = os.getcwd() + '/scripts/*.ipynb'
            ipynbs = glob.glob(src)
            ipynbs = sorted(ipynbs, key=str.lower)
            configs = []
            for nb in ipynbs:
                config_dict = nb_format(nb, include_dir=False)
                if not config_dict:
                    continue
                configs.append(config_dict)

            self.render("scripts.html", configs=configs)

        else:
            ipynb = os.getcwd() + '/scripts/' + script + '.ipynb'
            config = nb_format(ipynb, include_dir=False)
            if not config:
                self.write("Invalid script name: " + ipynb)
                return

            self.render("form_viewer.html", fields=config)

    def post(self, slug=None):
        script = slug
        if not script:
            self.write('File not found: ' + script)
            return

        # authenticate
        token = self.get_argument("token", default=None)
        username = self.get_argument("username", default=None)
        password = self.get_argument("password", default=None)
        environment = self.get_argument("environment_user", default="prod")
        if token:
            environment = self.get_argument("environment_token", default="prod")

        if (not username or not password) and (not token):
            self.write('Please enter in a correct username and password combination, or a valid auth token.')
            return

        token = authenticate(token, username, password, environment)
        if not token:
            self.write('Please enter in a correct username and password combination, or a valid auth token.')
            return

        # get the config file for that script
        nb = None
        folder = os.getcwd() + '/scripts'
        ipynb_full = folder + '/' + script + '.ipynb'
        config = nb_format(ipynb_full)
        if not config:
            self.write('File not found: ' + ipynb_full)
            return

        # configure the script to download the output
        download = config.get('download')

        # read script code
        try:
            with open(ipynb_full) as f:
                nb = reads(f.read(), 'json')
        except Exception, e:
            self.write('Read ipynb: ' + e.message)
            return

        # get initial parameters
        show_code = self.get_argument('show_code', default='N')
        if show_code == 'Y':
            show_code = True
        else:
            show_code = False
        text_only = self.get_argument('text_only', default='N')
        if text_only == 'Y':
            text_only = True
        else:
            text_only = False
        init_code = format_init_code(self, config, token, environment)

        try:
            (nb, download_file) = run_notebook(nb, init_code, script, show_code=show_code, download=download)
        except Exception, e:
            self.write('Run ipynb: ' + e.message)
            return

        # write the notebook to file and produce a html page
        if text_only:
            output_url = render_notebook_text(nb)
        else:
            try:
                output_url = '/static/' + render_notebook(nb, script, folder, full_dir=False)
            except Exception, e:
                self.write('Render ipynb: ' + e.message)
                return

        # download a csv file, if the output option was chosen
        if download and download_file:
            if not path.isfile(download_file):
                self.write('File not found: ' + download_file)
                return
            
            download_url = '/static/' + download_file.split('/')[-1]            
            fields = {'output':output_url, 'download':download_url, 'script':script}
            # print output_url
            self.render("results_viewer.html", fields=fields)
            return
        # just render   
        else:
            fields = {'output':output_url, 'download':None, 'script':script}
            self.render("results_viewer.html", fields=fields)
            return


class APIScriptsAllHandler(tornado.web.RequestHandler):
    def get(self):
        src = os.getcwd() + '/scripts/*.ipynb'
        ipynbs = glob.glob(src)
        ipynbs = sorted(ipynbs, key=str.lower)
        configs = []
        for nb in ipynbs:
            config_dict = nb_format(nb, include_dir=True)
            if not config_dict:
                continue
            configs.append(config_dict)
        self.write(format_response({'configs':configs}))
        return

class APIScriptsHandler(tornado.web.RequestHandler):
    def get(self, slug=None):
        script = slug
        if not script:
            self.write(format_response(None, message='No script found'))
        else:
            ipynb = os.getcwd() + '/scripts/' + script + '.ipynb'
            config = nb_format(ipynb, include_dir=False)
            if not config:
                self.write(format_response(None, message='No script found'))
                return
            self.write(format_response({'config':config}))

    def post(self, slug=None):
        script = slug
        if not script:
            self.write(format_response(None, message='Did not specify scipt name on POST call'))
            return

        # authenticate
        token = self.get_argument("token", default=None)
        username = self.get_argument("username", default=None)
        password = self.get_argument("password", default=None)
        environment = self.get_argument("environment", default="prod")
        if (not username or not password) and (not token):
            self.write(format_response(None, message='NOAUTH: no credentials found'))
            return

        token = authenticate(token, username, password, environment)
        if not token:
            self.write(format_response(None, message='UNAUTH: bad token or bad user/pass'))
            return

        # get the config file for that script
        nb = None
        folder = os.getcwd() + '/scripts'
        ipynb_full = folder + '/' + script + '.ipynb'
        config = nb_format(ipynb_full)
        if not config:
            self.write(format_response(None, message='Script not found'))
            return

        # configure the script to download the output
        download = config.get('download')

        # read script code
        try:
            with open(ipynb_full) as f:
                nb = reads(f.read(), 'json')
        except Exception, e:
            self.write(format_response(None, message='Script not properly formatted'))
            return

        # get initial parameters
        show_code = self.get_argument('show_code', default='N')
        if show_code == 'Y':
            show_code = True
        else:
            show_code = False
        text_only = self.get_argument('text_only', default='N')
        if text_only == 'Y':
            text_only = True
        else:
            text_only = False
        init_code = format_init_code(self, config, token, environment)

        try:
            (nb, download_file) = run_notebook(nb, init_code, script, show_code=show_code, download=download)
        except Exception, e:
            self.write(format_response(None, message='Error during execution'))
            return

        # write, render notebook
        if text_only:
            output = render_notebook_text(nb)
            output_url = json.dumps(output)
        else:
            try:
                output = render_notebook(nb, script, folder, full_dir=False)
            except Exception, e:
                self.write(format_response(None, message='Error during rendering'))
                return
            output_url = '/static/' + output

        # download a csv file, if the output option was chosen
        if download and download_file:
            if not path.isfile(download_file):
                self.write(format_response(None, message='Download not found'))
                return
            
            download_url = '/static/' + download_file.split('/')[-1]
            fields = {'output':output_url, 'download':download_url, 'script':script}
            self.write(format_response({'results':fields}))
            return
            
        else:
            fields = {'output':output_url, 'download':None, 'script':script}
            self.write(format_response({'results':fields}))
            return


handlers = [
    (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.getcwd() + '/public/static'}),
    (r"/", MainHandler),
    (r"/test", TestSetupHandler),
    (r"/scripts", ScriptsRedirectHandler),
    (r"/scripts/([^/]*)", ScriptsHandler),
    # API url routes
    (r"/api/v1/scripts", APIScriptsAllHandler),
    (r"/api/v1/scripts/", APIScriptsAllHandler),
    (r"/api/v1/scripts/([^/]*)", APIScriptsHandler),
]

settings = dict(
        template_path = os.getcwd() + '/templates',
)               

application = tornado.web.Application(handlers, **settings)


if __name__ == "__main__":
    # application.listen(8888)
    # tornado.ioloop.IOLoop.instance().start()
    
    port = 16024
    server = HTTPServer(application)
    server.bind(port)
    print "Listening on port %s" % port
    server.start(8)
    tornado.ioloop.IOLoop.instance().start()

    exit(0)
