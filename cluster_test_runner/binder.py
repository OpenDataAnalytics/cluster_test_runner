import logging
import yaml
logger = logging.getLogger("ctr")


class BinderParamater(object):
    def __init__(self, name, values, cost=1):
        self.name = name
        self.values = values
        self.cost = cost

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.name)


class BinderPlaybook(object):
    def __init__(self, path, static_vars):
        self.path = path
        self.static_vars = static_vars

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.path)


class Binder(object):
    def __init__(self, playbooks, global_static_variables, paramaters):
        self.playbooks = playbooks
        self.global_static_variables = global_static_variables
        self.global_paramaters = paramaters

    def __repr__(self):
        return ("%s<playbooks=%s, paramaters=%s>" %
                (self.__class__.__name__, len(self.playbooks),
                 len(self.global_paramaters)))


def _binder_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return Binder(n['playbooks'], n['vars'], n['paramaters'])


def _binderplaybook_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderPlaybook(n['path'], n['vars'])


def _binderparamater_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderParamater(n['name'], n['values'], n.get('cost', 1))

yaml.add_constructor(u'!binder', _binder_constructor)
yaml.add_constructor(u'!playbook', _binderplaybook_constructor)
yaml.add_constructor(u'!paramater', _binderparamater_constructor)
