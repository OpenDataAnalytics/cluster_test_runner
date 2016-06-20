from dauber import Playbook, Inventory
import yaml
import argparse
import logging
import time
import sys
import os
from tabulate import tabulate
from binder import Binder # noqa

DEBUG = False

logger = logging.getLogger('cluster_test_runner')


def excepthook(exctype, value, traceback):
    global DEBUG

    if DEBUG:
        sys.__excepthook__(exctype, value, traceback)
    else:
        logger.error("%s: %s" % (value.__class__.__name__, str(value)))

    sys.exit(1)

sys.excepthook = excepthook

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


def dry_run_playbook(binder_path, show_static=False, tabstyle='simple'):
    # get the binder object,  sort paramaters based on cost,
    # and get a list of names. We want to make sure the column order
    # will be playbook,  *paramaters,  *static_vars and that paramaters
    # will be sorted based on descending cost
    binder = get_binder(binder_path)
    column_order = binder.global_paramaters.keys()

    # get all playbooks/inventory/extra_vars as a list
    playbooks = list(binder())

    # Get a set of all of the variables (e.g. paramatesrs + static variables)
    # and subtract the paramater list,  then append it to the column order.
    # This makes sure the static variables are at the end of list of columns
    if show_static:
        column_order += list(set([k for p, i, e in playbooks
                                  for k in e.keys()]) - set(column_order))

    # Generate table rows. Cycle through column_order variable and get
    # extra_vars value for that key (or None). Keep in mind there may be
    # playbook specific variables so it is possible for some playbooks
    # that we will get None for the key.
    table = [[playbook] + [extra_vars.get(k, None) for k in column_order]
             for playbook, inventory, extra_vars in playbooks]

    # prepend the 'playbook' column
    column_order = ["playbook"] + column_order

    print tabulate(table, headers=column_order, tablefmt=tabstyle)


def run_playbooks(binder_path):
    binder_dir = os.path.dirname(os.path.realpath(binder_path))

    for playbook, inventory, extra_vars in parse_binder(binder_path):
        if inventory is None:
            inventory = Inventory(['localhost'])

        p = Playbook(inventory, extra_vars=extra_vars)

        if DEBUG:
            p.logger.setLevel(logging.DEBUG)

        logger.info("Running %s" % playbook); t0 = time.time()

        if not playbook.startswith("/"):
            playbook = os.path.join(binder_dir, playbook)

        ret = p.run(playbook)

        logger.info("Finished %s (%s)" % (playbook, time.time() - t0))

        if ret != 0:
            logger.error("Error running %s" % playbook)
            sys.exit(ret)

def main():
    global DEBUG

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
        DEBUG = True

    logger.setLevel(getattr(logging, args.loglevel))

    if args.dryrun:
        dry_run_playbook(args.input_binder,
                         show_static=args.showallvars,
                         tabstyle=args.tabstyle)
        sys.exit(0)

    run_playbooks(args.input_binder)

if __name__ == "__main__":
    main()
