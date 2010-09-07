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

    _preserve_headers = ["HTTP_COOKIE", 
                         "HTTP_X_OPENPLANS_APPLICATION",
                         "HTTP_X_OPENPLANS_PROJECT",
                         "HTTP_X_OPENPLANS_DOMAIN",
                         ]

    def default_theme(self, environ):
        """
        Let the default theme URI be a URI template
        """
        return self._default_theme % environ

    def notheme_request(self, req):
        if DeliveranceMiddleware.notheme_request(self, req):
            return True
        if req.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        
    def build_external_subrequest(self, url, orig_req, log):
        """
        We need to carry through certain headers into external 
        subrequests so that the downstream applications know
        what project context the request is within, what primary
        application the request is handled by, what domain the
        request is coming from; and login status must be retained
        """
        subreq = DeliveranceMiddleware.build_external_subrequest(
            self, url, orig_req, log)
        for header in self._preserve_headers:
            value = orig_req.environ.get(header)
            if value is None: continue
            subreq.environ[header] = value
        return subreq

    def get_resource(self, url, orig_req, log, retry_inner_if_not_200=False):
        """
        Gets the resource at the given url, using the original request
        `orig_req` as the basis for constructing the subrequest.
        Returns a `webob.Response` object.

        We want to never retry_inner_if_not_200.
        """
        retry_inner_if_not_200 = False
        return DeliveranceMiddleware.get_resource(self, url, orig_req, log,
                                                  retry_inner_if_not_200)


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
