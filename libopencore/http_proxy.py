from wsgifilter import proxyapp

vhm_template = "VirtualHostBase/%(wsgi.url_scheme)s/%(HTTP_HOST)s/openplans/VirtualHostRoot/"

def app_factory(global_conf,
                remote_uri=None, is_opencore=None,
                **local_conf):
    return RemoteProxy(remote_uri, is_opencore)

class RemoteProxy(object):
    def __init__(self, remote_uri=None, is_opencore=False):
        self.remote_uri = remote_uri
        self.is_opencore = is_opencore

    def __call__(self, environ, start_response):
        remote_uri = self.remote_uri
        if self.is_opencore:
            remote_uri = remote_uri + (vhm_template % environ)

        app = proxyapp.ForcedProxy(
            remote=remote_uri,
            force_host=True)

        # work around bug in WSGIFilter
        environ_copy = environ.copy()
        return app(environ_copy, start_response)
