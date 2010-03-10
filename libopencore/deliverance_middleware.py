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

    def __call__(self, environ, start_response):
        req = Request(environ)

        default_theme = self.default_theme % environ

        if 'deliv_notheme' in req.GET:
            return self.app(environ, start_response)
        req.environ['deliverance.base_url'] = req.application_url
        ## FIXME: copy_get?:                                                                                                                                                                                                                                                                
        orig_req = Request(environ.copy())
        if 'deliverance.log' in req.environ:
            log = req.environ['deliverance.log']
        else:
            log = self.log_factory(req, self, **self.log_factory_kw)
            ## FIXME: should this be put in both the orig_req and this req?                                                                                                                                                                                                                 
            req.environ['deliverance.log'] = log
        def resource_fetcher(url, retry_inner_if_not_200=False):
            """                                                                                                                                                                                                                                                                             
            Return the Response object for the given URL                                                                                                                                                                                                                                    
            """
            return self.get_resource(url, orig_req, log, retry_inner_if_not_200)
        if req.path_info_peek() == '.deliverance':
            req.path_info_pop()
            resp = self.internal_app(req, resource_fetcher)
            return resp(environ, start_response)
        rule_set = self.rule_getter(resource_fetcher, self.app, orig_req)
        clientside = rule_set.check_clientside(req, log)
        if clientside and req.url in self.known_html:
            if req.cookies.get('jsEnabled'):
                log.debug(self, 'Responding to %s with a clientside theme' % req.url)
                return self.clientside_response(req, rule_set, resource_fetcher, log)(environ, start_response)
            else:
                log.debug(self, 'Not doing clientside theming because jsEnabled cookie not set')
        resp = req.get_response(self.app)
        ## FIXME: also XHTML?                                                                                                                                                                                                                                                               
        if resp.content_type != 'text/html':
            ## FIXME: remove from known_html?                                                                                                                                                                                                                                               
            return resp(environ, start_response)

        # XXX: Not clear why such responses would have a content type, but                                                                                                                                                                                                                  
        # they sometimes do (from Zope/Plone, at least) and that then breaks                                                                                                                                                                                                                
        # when trying to apply a theme.                                                                                                                                                                                                                                                     
        if resp.status_int in (301, 302, 304):
            return resp(environ, start_response)

        if resp.content_length == 0:
            return resp(environ, start_response)

        if clientside and req.url not in self.known_html:
            log.debug(self, '%s would have been a clientside check; in future will be since we know it is HTML'
                      % req.url)
            self.known_titles[req.url] = self._get_title(resp.body)
            self.known_html.add(req.url)
        resp = rule_set.apply_rules(req, resp, resource_fetcher, log,
                                    default_theme=default_theme)
        if clientside:
            resp.decode_content()
            resp.body = self._substitute_jsenable(resp.body)
        resp = log.finish_request(req, resp)

        return resp(environ, start_response)


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
