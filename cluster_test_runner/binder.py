import itertools
import yaml
from collections import OrderedDict
import logging
import sys
from dauber import Playbook, Inventory
import os
import hashlib
from jinja2 import Template
from utils import recursive_hash

logger = logging.getLogger('cluster_test_runner')

PLAY_STATUS = ["RUNNING", "COMPLETE", "ERROR"]

class BinderParamater(object):
    def __init__(self, name, values, pegged_vars=None, cost=1, transitions=None):
        self.name = name
        self.values = values
        self.cost = cost
        self.transitions = transitions

        self.pegged_vars = pegged_vars if pegged_vars else {}

        for k, values in self.pegged_vars.items():
            assert len(self.values) == len(values), \
                "Paramater vars must have the same length as paramater values."


    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.name)

    def __call__(self):
        for v in self.values:
            yield (self.name, v)

    def get_pegged_vars(self, param):
        idx = self.values.index(param)
        return {k: v[idx] for k, v in self.pegged_vars.items()}


class YamlBinderPlaybook(object):
    def __init__(self, path, static_vars=None):
        self.path = path
        self.static_vars = static_vars

    def __repr__(self):
        return "%s<\"%s\">" % (self.__class__.__name__, self.path)


class BinderPlaybook(Playbook):
    root_cache_dir = ".test_cache"
    root_playbook_dir = ""

    def __init__(self, playbook, *args, **kwargs):
        super(BinderPlaybook, self).__init__(playbook, *args, **kwargs)

        self.playbook = self.playbook if playbook.startswith("/") else \
            os.path.join(self.root_playbook_dir, playbook)

        if self.inventory is None:
            self.inventory = Inventory(['localhost'])

    def run(self):
        self.set_status("RUNNING")

        code = super(BinderPlaybook, self).run()

        if code == 0:
            self.set_status("COMPLETE")
        else:
            self.set_status("ERROR")

        return code

    @property
    def extra_vars(self):
        return reduce(lambda a, b: a.update(b) or a, self._extra_vars, {})

    def get_hash(self):
        m = hashlib.md5()
        m.update(self.playbook)
        if self.tags:
            m.update(self._tags_as_csv(None).next())
        m.update(str(recursive_hash(self.extra_vars)))
        return m.hexdigest()

    def cache_dir(self):
        return os.path.join(self.root_cache_dir, self.get_hash())

    def get_status(self):
        for status in PLAY_STATUS:
            if os.path.exists(os.path.join(self.cache_dir(), status)):
                return status
        return None

    def mkcache_dir(self):
        try:
            os.makedirs(self.cache_dir())
        except OSError:
            pass
        self.logger.debug("Created {}".format(self.cache_dir()))

    def set_status(self, status):
        assert status in PLAY_STATUS, \
            "status must be one of %s" % ", ".join(PLAY_STATUS)

        self.mkcache_dir()

        for _status in PLAY_STATUS:
            try:
                os.remove(os.path.join(self.cache_dir(), _status))
            except OSError:
                pass

        with open(os.path.join(self.cache_dir(), status), "wb") as fh:
            fh.write(status + "\n")

        return status


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
                    for playbook in self._merge_extra_vars(self.global_paramaters[p].transitions,
                                                           self._last_params):
                        yield playbook
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

                # Add paramaters and any pegged variables
                for param, value in paramater_list:
                    extra_vars[param] = value
                    extra_vars.update(self.global_paramaters[param].get_pegged_vars(value))


                # TODO: remove any variables that have a special value (e.g. 'omit')
                #       to allow for inner scopes to remove outter scope variables
                # TODO: add a template engine step here to allow for composing variables based
                #       on the values of other variables (i.e.  for creating custom app-id's)

                # TODO: add inventory if it exists
                # TODO: add tags if it exists
                # TODO: add env if it exists

                yield BinderPlaybook(playbook.path, inventory=None,
                                     env=None, tags=None, extra_vars=extra_vars)


    def __call__(self):
        for paramater_list in itertools.product(
                *[param() for param in self.global_paramaters.values()]):

            for playbook in self.check_transitions(paramater_list):
                yield playbook

            for playbook in self._merge_extra_vars(self.playbooks, paramater_list):
                yield playbook

            self._last_params = paramater_list

        # Run final set of transitions
        for playbook in self.check_transitions((p, None) for p, v in paramater_list):
            yield playbook

        # Clean up last params
        del self._last_params


def get_binder(input_binder_path):
    try:
        with open(input_binder_path, "rb") as fh:
            binder_list = yaml.load(fh.read())

        if len(binder_list) > 1:
            logger.warn("More than one binder detected. Dropping all but first binder.")

        return binder_list[0]

    except IOError:
        logger.error("Could not read %s" % input_binder_path)
        sys.exit(1)
    except yaml.scanner.ScannerError:
        logger.error("Could not parse %s" % input_binder_path)
        sys.exit(1)


def parse_binder(input_binder_path):
    return get_binder(input_binder_path)()



def _binder_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return Binder(n['playbooks'], n.get('vars', None), n['paramaters'])


def _binderplaybook_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return YamlBinderPlaybook(n['path'], n.get('vars', None))


def _binderparamater_constructor(loader, node):
    n = loader.construct_mapping(node, deep=True)
    return BinderParamater(n['name'], n['values'], n.get('vars', None),
                           n.get('cost', 1), n.get("transitions", None))


yaml.add_constructor(u'!binder', _binder_constructor)
yaml.add_constructor(u'!playbook', _binderplaybook_constructor)
yaml.add_constructor(u'!paramater', _binderparamater_constructor)
