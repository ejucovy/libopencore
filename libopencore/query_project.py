from urllib import quote, unquote, urlencode

import httplib2
import elementtree.ElementTree as etree

import libopencore.auth

def admin_post(url, username, pw):
    h = httplib2.Http()
    # because of some zope silliness we have to do this as a POST instead of basic auth
    data = {"__ac_name":username, "__ac_password":pw}
    body = urlencode(data)
    resp, content = h.request(url, method="POST", body=body, redirections=0)
    return resp, content

class ProjectNotFoundError(Exception): pass

#from topp.utils import memorycache
#@memorycache.cache(120)
def get_users_for_project(project, server, admin_info):
    resp, content = admin_post("%s/projects/%s/members.xml" % (server, project), *admin_info)
    
    #404 means the project isn't fully initialized.
    if resp['status'] == '404':
        raise ProjectNotFoundError

    if resp['status'] != '200':
        if resp['status'] == '302':
            # redirect probably means auth failed
            extra = '; did your admin authentication fail?'
        elif resp['status'] == '400':
            # Probably Zope is gone
            extra = '; is Zope started?'
        else:
            extra = ''
            
        raise ValueError("Error retrieving project %s: status %s%s" 
                         % (project, resp['status'], extra))

    tree = etree.fromstring(content)
    members = []
    for member in tree:
        m = {}
        m['username'] = member.find('id').text.lower()
        m['roles'] = []
        for role in member.findall('role'):
            m['roles'].append(role.text)
        members.append(m)
    return members
