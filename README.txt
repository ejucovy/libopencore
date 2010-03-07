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
