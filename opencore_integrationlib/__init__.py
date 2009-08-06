def make_authenticated_request(url, username, pw):

    import httplib2

    h = httplib2.Http()
    # because of some zope silliness we have to do this as a POST instead of basic auth
    data = {"__ac_name":username, "__ac_password":pw}
    body = urlencode(data)
    resp, content = h.request(url, method="POST", body=body, redirections=0)
    return resp, content
#

class ProjectNotFoundError(Exception): pass

from topp.utils import memorycache

@memorycache.cache(120)
def get_users_for_project(project, server, admin_info):

    import elementtree.ElementTree as etree

    resp, content = make_authenticated_request("%s/projects/%s/members.xml" % (
            server, project), *admin_info)
    
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

@memorycache.cache(120)
def get_info_for_project(project, server, admin_info,
                         looking_for=None):

    import elementtree.ElementTree as etree

    # temporary BBB
    if looking_for is None:
        looking_for = 'tasks'

    resp, content = make_authenticated_request("%s/projects/%s/info.xml" % (
            server, project), *admin_info)
#    h = httplib2.Http()
#    resp, content = h.request("%s/projects/%s/info.xml" % (server, project), "GET")
    if resp['status'] == '404':
        raise ProjectNotFoundError #don't let this be cached
    if resp['status'] != '200':
        raise ValueError("Error retrieving project %s: status %s" % (project, resp['status']))
    tree = etree.fromstring(content)
    policy = tree[0]
    assert policy.tag == "policy", ("Bad info from project info getter")

    featurelets = tree[1]
    installed = False
    for flet in featurelets:
        if flet.text == looking_for:
            installed = True
            break

    info = dict(policy=policy.text, installed=installed)
    return info
