import logging
import yaml
logger = logging.getLogger("ctr")

class BinderPlaybook(object):
    def __init__(self, path, static_vars):
        self.path = path
        self.static_vars = static_vars

    def __repr__(self):
        return "%s(path=%s)" % (self.__class__.__name__, self.path)


class Binder(object):
    def __init__(self, playbooks, global_static_variables):
        self.playbooks = playbooks
        self.global_static_variables = global_static_variables



def _binder_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return Binder(n['playbooks'], n['vars'])

def _binderplaybook_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderPlaybook(n['path'], n['vars'])

yaml.add_constructor(u'!binder', _binder_constructor)
yaml.add_constructor(u'!playbook', _binderplaybook_constructor)
