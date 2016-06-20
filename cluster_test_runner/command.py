from dauber import Playbook, Inventory
import argparse
import logging
import time
import sys
import os
from tabulate import tabulate
from binder import get_binder, parse_binder  # noqa
from utils import recursive_hash
import hashlib


logger = logging.getLogger('cluster_test_runner')


def excepthook(exctype, value, traceback):
    if TestRunner.DEBUG:
        sys.__excepthook__(exctype, value, traceback)
    else:
        logger.error("%s: %s" % (value.__class__.__name__, str(value)))

    sys.exit(1)

sys.excepthook = excepthook


class TestRunner(object):
    DEBUG = False

    def __init__(self, args):
        self.binder_path = args.input_binder
        self.binder_dir = os.path.dirname(os.path.realpath(self.binder_path))
        self.binder = get_binder(self.binder_path)

        self.cachedir = args.cachedir

    def dry_run_playbook(self, show_static=False, tabstyle='simple'):
        # get the binder object,  sort paramaters based on cost,
        # and get a list of names. We want to make sure the column order
        # will be playbook,  *paramaters,  *static_vars and that paramaters
        # will be sorted based on descending cost
        column_order = self.binder.global_paramaters.keys()

        # get all playbooks/inventory/extra_vars as a list
        playbooks = list(self.binder())

        # Get a set of all of the variables (e.g. paramatesrs + static variables)
        # and subtract the paramater list,  then append it to the column order.
        # This makes sure the static variables are at the end of list of columns
        if show_static:

            column_order += list(set([k for p in playbooks
                                      for k in p.extra_vars.keys()]) -
                                 set(column_order))

        # Generate table rows. Cycle through column_order variable and get
        # extra_vars value for that key (or None). Keep in mind there may be
        # playbook specific variables so it is possible for some playbooks
        # that we will get None for the key.
        table = []
        for playbook in playbooks:
            table.append([playbook.playbook, playbook.cache_dir(self.cachedir)] +
                         [playbook.extra_vars.get(k, None) for k in column_order])

        # prepend the 'playbook' column
        column_order = ["playbook", "cache_dir"] + column_order

        print tabulate(table, headers=column_order, tablefmt=tabstyle)


    def run_playbooks(self):
        for playbook in self.binder():
            if self.DEBUG:
                playbook.logger.setLevel(logging.DEBUG)

            logger.info("Running %s" % playbook); t0 = time.time()

            # handle relative directories in binders
            if not playbook.playbook.startswith("/"):
                playbook.playbook = os.path.join(self.binder_dir, playbook.playbook)

            ret = playbook.run()

            logger.info("Finished %s (%s)" % (playbook.playbook, time.time() - t0))

            if ret != 0:
                logger.error("Error running %s" % playbook.playbook)
                sys.exit(ret)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--log-level',
        help="Print lots of debugging statements (implies -d)",
        action="store", dest="loglevel", default="INFO",
        choices=["INFO", "WARN", "ERROR", "DEBUG"]

    )
    parser.add_argument(
        '-d', '--debug',
        help="Print lots of debugging statements",
        action='store_true')

    parser.add_argument(
        '-c', '--cache-dir',
        help="Directory to cache playbook output, status, etc",
        action='store', default='.test_cache', dest="cachedir")

    parser.add_argument(
        '--dry-run', dest="dryrun",
        help="Display what would be run, including paramaters",
        action='store_true')

    parser.add_argument(
        '--show-all-vars', dest="showallvars",
        help="Also print static variables that will be set on"
        " playbook run when --dry-run is used",
        action='store_true')

    parser.add_argument(
        '--tabstyle', dest="tabstyle", action="store", default="simple",
        help="Style to print the table in, see: https://pypi.python.org/pypi/tabulate",
        choices=["plain", "simple", "grid", "fancy_grid", "pip", "orgtbl", "rst", "mediawiki",
                 "html", "latex", "latex_booktabs"])

    parser.add_argument(
        "input_binder", help="path to a playbook to run")

    args = parser.parse_args()

    if args.debug or args.loglevel == "DEBUG":
        TestRunner.DEBUG = True

    logger.setLevel(getattr(logging, args.loglevel))

    tr = TestRunner(args)
    if args.dryrun:
        tr.dry_run_playbook(show_static=args.showallvars,
                            tabstyle=args.tabstyle)
        sys.exit(0)

    tr.run_playbooks()

if __name__ == "__main__":
    main()
