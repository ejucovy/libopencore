from deliverance.middleware import DeliveranceMiddleware
from deliverance.security import display_local_files
from webob import exc, Response, Request
from deliverance.util.filetourl import url_to_filename
import os
import mimetypes
import urllib
from wsgiproxy.exactproxy import proxy_exact_request
class CustomDeliveranceMiddleware(DeliveranceMiddleware):
    """
    customizes the subrequest handler to copy the original request
    regardless of whether the subrequest url is within deliverance's
    url-space

    this is necessary to preserve the special headers, because we
    make an internal subrequest to opencore for the theme, which
    includes a dynamic topnav generated from the current request's
    project, application, and login status

     * HTTP_X_OPENPLANS_PROJECT: tells the downstream app what project
       context the request is for, if any. the topnav uses this to 
       figure out what title to display, and which featurelets to
       show links for in the topnav (or, if there's no project, it
       uses the global topnav)

     * HTTP_X_OPENPLANS_APPLICATION: tells the downstream app what app
       the request came in for (eg, a request to /projects/foo/tasks/
       will maintain X-Openplans-Application: tasktracker through all
       internal subrequests, even when fetching theme from opencore.
       the topnav uses this to highlight the current app's button.

     * HTTP_COOKIE: we need to send this along in the subrequests,
       so that users can remain logged in when they visit tasktracker etc.
       the topnav uses this to show login vs logout links, etc.
    """

    def default_theme(self, environ):
        """
        Let the default theme URI be a URI template
        """
        return self._default_theme % environ

    def get_resource(self, url, orig_req, log, dummy):
        """
        Gets the resource at the given url, using the original request
        `orig_req` as the basis for constructing the subrequest.
        Returns a `webob.Response` object.
        """
        assert url is not None
        if url.lower().startswith('file:'):
            if not display_local_files(orig_req):
                ## FIXME: not sure if this applies generally; some
                ## calls to get_resource might be because of a more
                ## valid subrequest than displaying a file
                return exc.HTTPForbidden(
                    "You cannot access file: URLs (like %r)" % url)
            filename = url_to_filename(url)
            if not os.path.exists(filename):
                return exc.HTTPNotFound(
                    "The file %r was not found" % filename)
            if os.path.isdir(filename):
                return exc.HTTPForbidden(
                    "You cannot display a directory (%r)" % filename)
            subresp = Response()
            type, dummy = mimetypes.guess_type(filename)
            if not type:
                type = 'application/octet-stream'
            subresp.content_type = type
            ## FIXME: reading the whole thing obviously ain't great:
            f = open(filename, 'rb')
            subresp.body = f.read()
            f.close()
            return subresp
        elif url.startswith(orig_req.application_url + '/'):
            subreq = orig_req.copy_get()
            subreq.environ['deliverance.subrequest_original_environ'] = orig_req.environ
            new_path_info = url[len(orig_req.application_url):]
            query_string = ''
            if '?' in new_path_info:
                new_path_info, query_string = new_path_info.split('?')
            new_path_info = urllib.unquote(new_path_info)
            assert new_path_info.startswith('/')
            subreq.path_info = new_path_info
            subreq.query_string = query_string
            subresp = subreq.get_response(self.app)
            ## FIXME: error if not HTML?
            ## FIXME: handle redirects?
            ## FIXME: handle non-200?
            log.debug(self, 'Internal request for %s: %s content-type: %s',
                            url, subresp.status, subresp.content_type)
            return subresp
        else:
            ## FIXME: pluggable subrequest handler?
            subreq = Request.blank(url)
            
            subreq.environ['HTTP_COOKIE'] = orig_req.environ.get('HTTP_COOKIE')
            subreq.environ['HTTP_X_OPENPLANS_APPLICATION'] = orig_req.environ.get('HTTP_X_OPENPLANS_APPLICATION')
            subreq.environ['HTTP_X_OPENPLANS_PROJECT'] = orig_req.environ.get('HTTP_X_OPENPLANS_PROJECT')
            subreq.environ['HTTP_X_OPENPLANS_DOMAIN'] = orig_req.environ.get('HTTP_X_OPENPLANS_DOMAIN')

            # there's an bug deeper in the stack which causes a link /foo/my.domain.com/bar/ 
            # to be rewritten as /foo/my.domain.com:80/bar/ if HTTP_HOST is my.domain.com:80
            # so i'll just hack around it for now
            
            # XXX FIXME: track down the bug!
            if subreq.environ['HTTP_HOST'].endswith(":80"):
                subreq.environ['HTTP_HOST'] = subreq.environ["HTTP_HOST"][:-3]

            subresp = subreq.get_response(proxy_exact_request)
            log.debug(self, 'External request for %s: %s content-type: %s',
                      url, subresp.status, subresp.content_type)
            return subresp

from deliverance.middleware import FileRuleGetter
from pkg_resources import resource_filename
import os
def filter_factory(global_conf, **local_conf):
    rule_file = resource_filename('libopencore', 'deliverance.xml')
    theme_uri = "%(wsgi.url_scheme)s://%(HTTP_HOST)s/theme.html"
    assert os.path.exists(rule_file) and os.path.isfile(rule_file)

    # make sure theme_uri ends with a trailing slash
    # since deliverance can't currently handle 3xx responses
    theme_uri = theme_uri.rstrip('/') + '/'  
    

    def filter(app):
        return CustomDeliveranceMiddleware(
            app, FileRuleGetter(rule_file),
            default_theme=theme_uri)
    return filter
