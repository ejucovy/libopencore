A small library of functions useful for integration with opencore.

Contents:

libopencore.auth
================

 * get_secret(filename)

   Get a shared secret to be used in cookie parsing & construction.

 * generate_cookie_value(username, shared_secret)
   
   Use this to set a cookie so that opencore will recognize the user
   as logged in.

 * authenticate_from_cookie(cookie_string, shared_secret)

   Returns (username, hash) for the user identified by the cookie.
   Throws a BadCookie exception if the cookie is malformed, or a
   NotAuthenticated exception if the cookie is well-formed but not
   using the correct shared secret.

libopencore.deliverance_middleware
==================================

 * filter_factory / CustomDeliveranceMiddleware

   A subclass of Deliverance middleware (v0.3) that carries along
   the original request's HTTP_X_OPENPLANS_*  headers and cookie,
   when making external subrequests. This allows external applications
   to properly respect login and context information.

   It also hard-codes the necessary Deliverance ruleset, and theme uri.

   The theme is served by opencore itself, at a @@theme.html view registered
   on the portal. Here, it is fetched by making an external request to the
   front of the OpenCore stack, to guarantee that links in the theme are
   correct.

libopencore.wsgi
================

 * composite_factory / URLDispatcher

   A paste.composite_factory that will dispatch requests to
   opencore and to other applications (tasktracker and wordpress)
   based on the URL.

   It will add the necessary request headers before making
   subrequests.

libopencore.http_proxy
======================

 * app_factory / RemoteProxy

   A paste.app_factory that will proxy requests to external HTTP
   calls.  Pass a ``remote_uri`` with the base href for the app.

   If ``is_opencore`` is set, it will rewrite the request to tell
   Zope's VirtualHostMonster how links in the response should look.

