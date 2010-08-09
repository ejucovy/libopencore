from wsgifilter import proxyapp

vhm_template = "VirtualHostBase/%(wsgi.url_scheme)s/%(HTTP_HOST)s:%(frontend_port)s/openplans/VirtualHostRoot/"

def app_factory(global_conf,
                remote_uri=None,
                is_opencore=False,
                is_twirlip=None,
                **local_conf):
    assert remote_uri is not None
    remote_uris = [i.strip() for i in remote_uri.split()
                   if i.strip()]
    
    app = RemoteProxy(remote_uris, is_opencore)
    if is_twirlip is None:
        return app
    # if we're proxying to twirlip we need to wrap this in
    # eyvind's middleware which transforms REMOTE_USER 
    # into a signed HTTP header that can be passed to twirlip
    from eyvind.lib.authmiddleware import make_auth_middleware
    app = fixer(app)
    app = make_auth_middleware(app, local_conf)
    return app

class fixer(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        p = environ['PATH_INFO'] 
        p = p.lstrip('/')
        environ['PATH_INFO'] = p
        return self.app(environ, start_response)

from random import randint
class RemoteProxy(object):
    def __init__(self, remote_uris=None, is_opencore=False):
        remote_uris = remote_uris or []

        # make sure there's a trailing slash
        self.remote_uris = [
            remote_uri.rstrip('/') + '/' 
            for remote_uri in remote_uris
            ]
        
        self.is_opencore = is_opencore

    def pick_remote_uri(self):
        i = randint(0, len(self.remote_uris)-1)
        return self.remote_uris[i]


    def __call__(self, environ, start_response):
        remote_uri = self.pick_remote_uri()

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

        environ['HTTP_X_OPENPLANS_DOMAIN'] = environ['HTTP_HOST'].split(':')[0]

        app = proxyapp.ForcedProxy(
            remote=remote_uri,
            force_host=True)

        # work around bug in WSGIFilter
        environ_copy = environ.copy()

        
        return app(environ_copy, start_response)
