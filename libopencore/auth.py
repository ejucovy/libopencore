class BadCookie(Exception): # XXX TODO: subclass a specific exc class, maybe RuntimeError
    pass
class NotAuthenticated(Exception): # XXX TODO: sublcass a specific exc class
    pass

import base64
import hmac
import os
from random import SystemRandom
import sha
import urllib

def generate_cookie_value(username, shared_secret):
    hash = generate_hash(username, shared_secret)
    encoded = base64.encodestring("%s\0%s" % (username, hash))
    return urllib.quote(encoded.rstrip())

def authenticate_from_cookie(cookie, shared_secret):
    try:
        username, hash = parse_cookie(cookie)
    except ValueError:
        raise BadCookie # XXX TODO: don't lose original exception info

    if hash != generate_hash(username, shared_secret):
        raise NotAuthenticated
    return username, hash
    
def generate_hash(username, shared_secret):
    return hmac.new(shared_secret, username, sha).hexdigest()

def parse_cookie(cookie_string):
    cookie_string = urllib.unquote(cookie_string)
    val = base64.decodestring(cookie_string)
    username, hash = val.split('\0')
    return (username, hash)

def get_secret(secret_filename,
               generate_random_on_failure=False):

    if generate_random_on_failure and \
            not os.path.exists(secret_filename):
        return set_secret(secret_filename)

    f = open(secret_filename)
    secret = f.readline().strip()
    f.close()
    return secret

def set_secret(secret_filename):
    #this may throw an error if the file cannot be created, but that's OK, because 
    #then users will know to create it themselves
    f = open(secret_filename, "w")
    random = SystemRandom()
    letters = [chr(ord('A') + i) for i in xrange(26)]
    letters += [chr(ord('a') + i) for i in xrange(26)]
    letters += map(str, xrange(10))
    password = "".join([random.choice(letters) for i in xrange(10)])
    f.write(password)
    f.close()
    return password

from Cookie import BaseCookie

def get_user(request, secret_filename):
    """
    Can raise IOError (in secret=, if secret_filename is not configured right)
    Can raise KeyError (in morsel=, if no cookie)
    Can raise BadCookie or NotAuthenticated
    """
    secret = get_secret(secret_filename)
    morsel = BaseCookie(request.environ['HTTP_COOKIE'])['__ac']
    username, hash = authenticate_from_cookie(morsel.value, secret)
    return username

def get_admin_info(admin_file):
    return file(admin_file).read().strip().split(":")
