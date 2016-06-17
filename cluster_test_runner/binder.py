import itertools
import yaml

class BinderParamater(object):
    def __init__(self, name, values, cost=1):
        self.name = name
        self.values = values
        self.cost = cost

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.name)

    def __call__(self):
        for v in self.values:
            yield (self.name, v)

class BinderPlaybook(object):
    def __init__(self, path, static_vars):
        self.path = path
        self.static_vars = static_vars

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.path)


class Binder(object):
    def __init__(self, playbooks, global_static_vars, paramaters):
        self.playbooks = playbooks
        self.global_static_vars = global_static_vars

        assert len(paramaters) == len(set(p.name for p in paramaters)), \
            "Paramater names must be unique!"

        self.global_paramaters = paramaters

        # TODO: transform yaml dict into tuple of tuples
        self.exclude = []

    def __repr__(self):
        return ("%s<playbooks=%s, paramaters=%s>" %
                (self.__class__.__name__, len(self.playbooks),
                 len(self.global_paramaters)))

    def __call__(self):
        for paramater_list in itertools.product(
                *[p() for p in sorted(self.global_paramaters,
                                      key=lambda p: p.cost, reverse=True)]):

            if tuple(paramater_list) not in self.exclude:
                for playbook in self.playbooks:
                    extra_vars = {}

                    extra_vars.update(self.global_static_vars)

                    extra_vars.update(playbook.static_vars)

                    extra_vars.update(dict(paramater_list))
                    # TODO: add inventory where None is
                    yield playbook.path, None, extra_vars

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
