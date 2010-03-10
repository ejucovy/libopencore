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
    Given a request environ, find the project context of the request,
    if there is one, using a simple regex match.

    If a project context was found, we should tell the caller how it
    can rewrite SCRIPT_NAME and PATH_INFO to make URLs look like they
    are not relative to a project. So in addition to returning the
    project name, we'll return a rewritten script_name and path_info
    that can be used to modify the environment. (Note we don't touch
    the passed-in environ itself.)

    Returns (project_name, script_name, path_info) 
    or (None, script_name, path_info) if no project was found.
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
        return project, script_name, path_info
    return None, script_name, path_info

def composite_factory(loader, global_conf, **local_conf):
    default_app = local_conf['opencore']
    default_app = loader.get_app(default_app)

    other_apps = []
    # items in other_apps are 3-tuples
    #   ('/subpath', wsgi_app, 'app_name_for_x_openplans_application_header')
    #
    # these are hardcoded in this composite_factory, because there's
    # no advantage to exposing it for configuration -- it'll just break
    # all of opencore's assumptions.
    tasktracker = local_conf.get('tasktracker')
    if tasktracker is not None:
        tasktracker = loader.get_app(tasktracker)
        other_apps.append(('/tasks', tasktracker, 'tasktracker'))

    wordpress = local_conf.get('wordpress')
    if wordpress is not None:
        wordpress = loader.get_app(wordpress)
        other_apps.append(('/blog', wordpress, 'wordpress'))

    return URLDispatcher(default_app,
                         *other_apps)

class URLDispatcher(object):
    def match_path_info(self, script_name, path_info):
        """
        Determines if the given URL matches one of the apps
        registered with the dispatcher.

        If there is a match, the caller will want to modify
        SCRIPT_NAME and PATH_INFO before passing the request
        to the matching application. So we return a rewritten
        SCRIPT_NAME and PATH_INFO that it can use.

        Returns (matching_app, app_name, new_script_name, new_path_info)
        or (None, None, script_name, path_info) if no app matches.
        """
        for path in self.apps:
            if path_info == path or path_info.startswith(path+'/'):
                script_name += path
                path_info = path_info[len(path):]
                assert not path_info or path_info.startswith('/')
                return tuple(self.apps[path]) + (script_name, path_info)

        return (None, None, script_name, path_info)

    def __init__(self, default_app, *apps):
        self.default_app = default_app
        self.apps = {}
        for path, app, app_name in apps:
            self.apps[path] = (app, app_name)

    def __call__(self, environ, start_response):

        project, new_script_name, new_path_info = parse_project(environ)
        if not project:
            # we are not in a project context, so we'll just let the
            # default app (opencore) deal with the request.
            return self.default_app(environ, start_response)

        add_request_header('HTTP_X_OPENPLANS_PROJECT', project, environ)

        app_to_dispatch_to, app_name, new_script_name, new_path_info = \
            self.match_path_info(new_script_name, new_path_info)
        if not app_to_dispatch_to:
            return self.default_app(environ, start_response)

        environ['PATH_INFO'], environ['SCRIPT_NAME'] = (
            new_path_info.lstrip('/'), new_script_name.rstrip('/'))

        # XXX TODO: look up what uses this, and, where, and how, and why, 
        #           and what it should look like
        if not environ.has_key('HTTP_X_OPENPLANS_APPLICATION'):
            add_request_header('HTTP_X_OPENPLANS_APPLICATION',
                               app_name, environ)

        return app_to_dispatch_to(environ, start_response)
