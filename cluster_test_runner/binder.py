import itertools
import yaml
from collections import OrderedDict


class BinderParamater(object):
    def __init__(self, name, values, cost=1, transitions=None):
        self.name = name
        self.values = values
        self.cost = cost
        self.transitions = transitions

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.name)

    def __call__(self):
        for v in self.values:
            yield (self.name, v)


class BinderPlaybook(object):
    def __init__(self, path, static_vars=None):
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

        self.global_paramaters = OrderedDict(
            [(p.name, p) for p in sorted(paramaters, key=lambda p: p.cost,
                                         reverse=True)])

        # TODO: parse excludes from the YAML file
        self.exclude = []

    def __repr__(self):
        return ("%s<playbooks=%s, paramaters=%s>" %
                (self.__class__.__name__, len(self.playbooks),
                 len(self.global_paramaters)))

    def check_transitions(self, paramater_values):
        if hasattr(self, "_last_params"):
            for p, v in (set(self._last_params) - set(paramater_values)):
                if self.global_paramaters[p].transitions is not None:
                    for playbook, inventory, extra_vars in \
                        self._merge_extra_vars(self.global_paramaters[p].transitions,
                                               self._last_params):
                        yield playbook, inventory, extra_vars
        else:
            # Create _last_params if it doesn't exist
            self._last_params = paramater_values


    def _merge_extra_vars(self, playbooks, paramater_list):
        if tuple(paramater_list) not in self.exclude:
            for playbook in playbooks:
                extra_vars = {}

                if self.global_static_vars:
                    extra_vars.update(self.global_static_vars)

                if playbook.static_vars:
                    extra_vars.update(playbook.static_vars)

                extra_vars.update(dict(paramater_list))
                # TODO: remove any variables that have a special value (e.g. 'omit')
                #       to allow for inner scopes to remove outter scope variables
                # TODO: add a template engine step here to allow for composing variables based
                #       on the values of other variables (i.e.  for creating custom app-id's)
                # TODO: add inventory where None is if exists

                yield playbook.path, None, extra_vars


    def __call__(self):
        for paramater_list in itertools.product(
                *[param() for param in self.global_paramaters.values()]):

            for p, i, ev in self.check_transitions(paramater_list):
                yield p, i, ev

            for p, i, ev in self._merge_extra_vars(self.playbooks, paramater_list):
                yield p, i, ev

            self._last_params = paramater_list

        # Run final set of transitions
        for p, i, ev in self.check_transitions((p, None) for p, v in paramater_list):
            yield p, i, ev

        # Clean up last params
        del self._last_params


def _binder_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return Binder(n['playbooks'], n.get('vars', None), n['paramaters'])


def _binderplaybook_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderPlaybook(n['path'], n.get('vars', None))


def _binderparamater_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderParamater(n['name'], n['values'],
                           n.get('cost', 1), n.get("transitions", None))


yaml.add_constructor(u'!binder', _binder_constructor)
yaml.add_constructor(u'!playbook', _binderplaybook_constructor)
yaml.add_constructor(u'!paramater', _binderparamater_constructor)
