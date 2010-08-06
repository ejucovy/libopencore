import socket
import time
from paste.httpexceptions import HTTPGatewayTimeout

class SocketErrorToHTTPServerException(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except socket.error, e:
            raise HTTPGatewayTimeout("Socket error %d - %r" % e.args)

class RetryOnceOnSocketError(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except socket.error:
            # Give the remote service a second to restart, etc.
            time.sleep(1)
            return self.app(environ, start_response)

from paste.httpexceptions import HTTPException
from paste.httpexceptions import HTTPExceptionHandler
from paste.util.quoting import strip_html, html_quote, no_quote
import os

TEMPLATE = """\
<html>\r
  <head><title>%(title)s</title></head>\r
  <body>\r
    <h1>OpenPlans</h1>\r
    <h1>%(title)s</h1>\r
    <p>%(body)s</p>\r
    <hr noshade>\r
    <div align="right">%(server)s</div>\r
  </body>\r
</html>\r
"""

class CustomErrorHTTPException(HTTPException):
    def __init__(self, exception, dir):
        self.code = exception.code
        self.title = exception.title
        self.explanation = exception.explanation
        self.headers = exception.headers
        self.detail = exception.detail
        self.comment = exception.comment
        self.template = exception.template
        self.required_headers = exception.required_headers
        self.dir = dir

    def html(self, environ):
        """ text/html representation of the exception """
        body = self.make_body(environ, self.template, html_quote, no_quote)

        error_template = TEMPLATE
        template_file = None

        try:
            template_file = open(os.path.join(self.dir, str(self.code) + '.html'), 'r')
        except IOError:
            try:
                template_file = open(os.path.join(self.dir, 'error.html'), 'r')
            except IOError:
                pass

        if template_file:
            try:
                error_template = template_file.read()
                template_file.close()
            except IOError:
                template_file.close()

        return error_template % {
                   'title': self.title,
                   'code': self.code,
                   'server': 'OpenCore WSGI Server',
                   'explanation': self.explanation,
                   'detail': self.detail,
                   'comment': self.comment,
                   'body': body }


class CustomErrorHTTPExceptionHandler(HTTPExceptionHandler):
    """
    catches exceptions and turns them into proper HTTP responses

    Attributes:

       ``warning_level``
           This attribute determines for what exceptions a stack
           trace is kept for lower level reporting; by default, it
           only keeps stack trace for 5xx, HTTPServerError exceptions.
           To keep a stack trace for 4xx, HTTPClientError exceptions,
           set this to 400.

    This middleware catches any exceptions (which are subclasses of
    ``HTTPException``) and turns them into proper HTTP responses.
    Note if the headers have already been sent, the stack trace is
    always maintained as this indicates a programming error.
    """
    def __init__(self, application, dir, warning_level=None):
        HTTPExceptionHandler.__init__(self, application, warning_level)
        self.dir = dir

    def __call__(self, environ, start_response):
        environ['paste.httpexceptions'] = self
        environ.setdefault('paste.expected_exceptions',
                           []).append(HTTPException)
        try:
            return self.application(environ, start_response)
        except HTTPException, exc:
            CustomErrorException = CustomErrorHTTPException(exc, self.dir)
            return CustomErrorException(environ, start_response)


import transcluder
from transcluder.middleware import TranscluderMiddleware


def create_transcluder(global_conf, **app_conf):
    ok_hosts = app_conf.get('transcluder_ok_hosts')

    if not ok_hosts or ok_hosts == 'all':
        transcluder_ok_hosts = transcluder.helpers.all_urls
    elif ok_hosts == 'none':
        transcluder_ok_hosts = transcluder.helpers.no_urls
    elif ok_hosts == 'localhost':
        transcluder_ok_hosts = transcluder.helpers.localhost_only
    else:
        transcluder_ok_hosts = transcluder.helpers.make_regex_predicate(ok_hosts)

    transcluder_deptracker = transcluder.deptracker.DependencyTracker()

    poolsize = int(app_conf.get('transcluder_pool_size', 0))
    transcluder_pool = transcluder.tasklist.TaskList(poolsize=poolsize)

    def filter(app):
        app = TranscluderMiddleware(app,
                                    deptracker=transcluder_deptracker,
                                    tasklist=transcluder_pool,
                                    include_predicate=transcluder_ok_hosts,
                                    recursion_predicate=transcluder_ok_hosts)
        app = RetryOnceOnSocketError(app)
        app = SocketErrorToHTTPServerException(app)
    
        return app
    return filter

