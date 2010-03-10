from wsgifilter import proxyapp

vhm_template = "VirtualHostBase/%(wsgi.url_scheme)s/%(HTTP_HOST)s:%(frontend_port)s/openplans/VirtualHostRoot/"

def app_factory(global_conf,
                remote_uri=None, is_opencore=None,
                **local_conf):
    return RemoteProxy(remote_uri, is_opencore)

class RemoteProxy(object):
    def __init__(self, remote_uri=None, is_opencore=False):
        self.remote_uri = remote_uri.rstrip('/') + '/' # make sure there's a trailing slash
        self.is_opencore = is_opencore

    def __call__(self, environ, start_response):
        remote_uri = self.remote_uri
        if self.is_opencore:
            environ_copy = environ.copy()

            # With varnish on port 80 proxying to the opencore stack entrypoint,
            # HTTP_HOST doesn't include the :80 bit. (I don't know about other
            # frontends.) Just to be safe, we'll decompose HTTP_HOST into its
            # parts, and if the port information is missing, we'll set port 80.
            #
            # The virtual host monster needs this information. If it's missing,
            # opencore will generate links with the port that Zope is served on.

            parts = environ['HTTP_HOST'].split(':')
            environ_copy['HTTP_HOST'] = parts[0]
            if len(parts) > 1:
                environ_copy['frontend_port'] = parts[1]
            else:
                environ_copy['frontend_port'] = '80'
            remote_uri = remote_uri + (vhm_template % environ_copy)

        app = proxyapp.ForcedProxy(
            remote=remote_uri,
            force_host=True)

        # work around bug in WSGIFilter
        environ_copy = environ.copy()
        return app(environ_copy, start_response)
