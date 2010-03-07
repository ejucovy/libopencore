"""
forked from
 https://svn.openplans.org/svn/build/openplans_hooks/
"""

def add_request_header(header_name, value, environ):
    environ[header_name] = value
    # make sure it propagates to subrequests
    if 'paste.recursive.include' in environ:
        orig = environ['paste.recursive.include'].original_environ
        orig[header_name] = value

import re

# XXX TODO: this regex is too permissive i think
_project_regex = re.compile(r'/projects/+([^/]+)')

def parse_project(environ):
    """
    For the main site, find the project name and put the
    /projects/PROJECTNAME portion of the path onto SCRIPT_NAME
    """
    path_info = environ.get('PATH_INFO', '')
    script_name = environ.get('SCRIPT_NAME', '')
    match = _project_regex.search(path_info)
    if match:
        script_name += match.group(0)
        project = match.group(1)

        # XXX TODO: no need for this here i think?
        #if not path_info[match.end():] and environ['REQUEST_METHOD'] in ('GET', 'HEAD'):
        #    # No trailing slash, i.e., "/project/foo"
        #    new_url = construct_url(environ, path_info=environ['PATH_INFO']+'/')
        #    raise httpexceptions.HTTPMovedPermanently(
        #        headers=[('Location', new_url)])

        path_info = '/' + path_info[match.end():].lstrip('/')
        return project, path_info, script_name
    return None, path_info, script_name

class App(object):
    def __init__(self, app, header):
        self.app = app
        self.header = header

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

    def __repr__(self):
        return self.header

from deliverance.middleware import FileRuleGetter    
from libopencore.deliverance_middleware import CustomDeliveranceMiddleware

def factory(loader, global_conf, **local_conf):
    default_app = local_conf['opencore']
    default_app = loader.get_app(default_app)
    default_app = App(default_app, '')

    tasktracker = local_conf['tasktracker']
    tasktracker = loader.get_app(tasktracker)

    deliverance_ruleset = local_conf['.deliverance_rule_file']
    theme_uri = local_conf['.theme_uri']

    tasktracker = CustomDeliveranceMiddleware(
        tasktracker,
        FileRuleGetter(deliverance_ruleset),
        default_theme=theme_uri)

    tasktracker = App(tasktracker, 'tasktracker')

    wordpress = local_conf['wordpress']
    wordpress = loader.get_app(wordpress)
    wordpress = CustomDeliveranceMiddleware(
        wordpress,
        FileRuleGetter(deliverance_ruleset),
        default_theme=theme_uri)
    wordpress = App(wordpress, 'wordpress')

    other_apps = [('/tasks', tasktracker),
                  ('/blog', wordpress)]

    return URLDispatcher(default_app,
                         *other_apps)

class URLDispatcher(object):
    def match_path_info(self, path_info, script_name):
        for path in self.apps:
            if path_info == path or path_info.startswith(path+'/'):
                script_name += path
                path_info = path_info[len(path):]
                assert not path_info or path_info.startswith('/')
                return (self.apps[path], path_info, script_name)

        return (False, path_info, script_name)

    def __init__(self, default_app, *apps):
        self.default_app = default_app
        self.apps = {}
        for path, app in apps:
            self.apps[path] = app

    def __call__(self, environ, start_response):
        project, new_path_info, new_script_name = parse_project(environ)
        if not project:
            return self.default_app(environ, start_response)

        add_request_header('HTTP_X_OPENPLANS_PROJECT', project, environ)

        app_to_dispatch_to, new_path_info, new_script_name = \
            self.match_path_info(new_path_info, new_script_name)
        if not app_to_dispatch_to:
            return self.default_app(environ, start_response)

        environ['PATH_INFO'], environ['SCRIPT_NAME'] = (
            new_path_info, new_script_name)

        # XXX TODO: look up what uses this, and, where, and how, and why, 
        #           and what it should look like
        if not environ.has_key('HTTP_X_OPENPLANS_APPLICATION'):
            add_request_header('HTTP_X_OPENPLANS_APPLICATION',
                               app_to_dispatch_to.header,
                               environ)

        return app_to_dispatch_to(environ, start_response)

from wsgifilter import proxyapp

def proxy_factory(global_conf,
                  remote_uri=None, remote_uri_template=None,
                  **local_conf):
    return RemoteProxy(remote_uri, remote_uri_template)

class RemoteProxy(object):
    def __init__(self, remote_uri=None, remote_uri_template=None):
        if remote_uri:
            self.template = False
            self.remote_uri = remote_uri
        elif remote_uri_template:
            file = open(remote_uri_template)
            remote_uri_template = file.read().strip()
            file.close()
            self.template = True
            self.remote_uri_template = remote_uri_template
        else:
            raise AssertionError

    def __call__(self, environ, start_response):
        if self.template:
            template = self.remote_uri_template
            remote_uri = template % environ
        else:
            remote_uri = self.remote_uri

        app = proxyapp.ForcedProxy(
            remote=remote_uri,
            force_host=True)

        return app(environ, start_response)
