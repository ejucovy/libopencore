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

    this is necessary to preserve the special headers
     * HTTP_X_OPENPLANS_PROJECT: tells the downstream app what project
       context the request is for

     * HTTP_X_OPENPLANS_APPLICATION: tells the downstream app what app
       the request came in for (eg, a request to /projects/foo/tasks/
       will maintain X-Openplans-Application: tasktracker through all
       internal subrequests, even if there's an internal request to, say,
       wordpress for the latest blog posts related to the task[*])

       [*] we don't do this but it would be kinda cool, wouldn't it?

     * HTTP_COOKIE: we need to send this along in the subrequests,
       so that users can remain logged in when they visit tasktracker etc.
    """

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

            subresp = subreq.get_response(proxy_exact_request)
            log.debug(self, 'External request for %s: %s content-type: %s',
                      url, subresp.status, subresp.content_type)
            return subresp

from deliverance.middleware import FileRuleGetter    
def filter_factory(global_conf, rule_file=None, theme_uri=None, **local_conf):
    def filter(app):
        return CustomDeliveranceMiddleware(
            app, FileRuleGetter(rule_file),
            default_theme=theme_uri)
    return filter
