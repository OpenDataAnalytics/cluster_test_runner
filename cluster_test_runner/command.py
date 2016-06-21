from dauber import Playbook, Inventory
import argparse
import logging
import time
import sys
import os
from tabulate import tabulate
from binder import get_binder, parse_binder  # noqa
from binder import BinderPlaybook
from utils import recursive_hash
import hashlib
import click
import shutil

logger = logging.getLogger('cluster_test_runner')

# Controls whether we show raw python exceptions
DEBUG = False

def _excepthook(exctype, value, traceback):
    if DEBUG:
        sys.__excepthook__(exctype, value, traceback)
    else:
        logger.error("%s: %s" % (value.__class__.__name__, str(value)))

    sys.exit(1)

sys.excepthook = _excepthook


def _playbook_root_callback(ctx, param, value):
    if value is not None:
        BinderPlaybook.root_playbook_dir = value
    if 'binder_path' in ctx.params:
        BinderPlaybook.root_playbook_dir = os.path.dirname(os.path.realpath(ctx.params['binder_path']))



@click.group()
@click.option("--debug", "-d", is_flag=True, default=False,
              help="Print logs of debugging statements")

@click.option("--loglevel", "-l", default="INFO",
              type=click.Choice(["INFO", "WARN", "ERROR", "DEBUG"]),
              help="Set the log level")
@click.option("--cachedir", "-c", default=".test_cache",
              help="")
def main(debug, loglevel, cachedir):
    global DEBUG
    logger.setLevel(getattr(logging, loglevel))

    if debug or loglevel == "DEBUG":
        DEBUG = True
        logger.setLevel(logging.DEBUG)

    BinderPlaybook.root_cache_dir = cachedir



@main.command()
@click.option("--showallvars", "-s", is_flag=True, default=False,
              help="Also print static variables that will be set on run")
@click.option("--tabstyle", "-t", default="simple",
              type=click.Choice(["plain", "simple", "grid", "fancy_grid",
                                 "pip", "orgtbl", "rst", "mediawiki",
                                 "html", "latex", "latex_booktabs"]),
              help="Style to print table. See:https://pypi.python.org/pypi/tabulate")
@click.option("--playbook-root", "-p",
              callback=_playbook_root_callback, expose_value=False,
              help="Root directory for playbooks with relative paths, "
              "defaults to location of input_binder")
@click.argument('binder_path', type=click.Path(exists=True))
def status(showallvars, tabstyle, binder_path):
    binder = get_binder(binder_path)
    # get the binder object,  sort paramaters based on cost,
    # and get a list of names. We want to make sure the column order
    # will be playbook,  *paramaters,  *static_vars and that paramaters
    # will be sorted based on descending cost
    column_order = binder.global_paramaters.keys()

    # get all playbooks/inventory/extra_vars as a list
    playbooks = list(binder())

    # Get a set of all of the variables (e.g. paramatesrs + static variables)
    # and subtract the paramater list,  then append it to the column order.
    # This makes sure the static variables are at the end of list of columns
    if showallvars:

        column_order += list(set([k for p in playbooks
                                  for k in p.extra_vars.keys()]) -
                             set(column_order))

    # Generate table rows. Cycle through column_order variable and get
    # extra_vars value for that key (or None). Keep in mind there may be
    # playbook specific variables so it is possible for some playbooks
    # that we will get None for the key.
    table = []
    for playbook in playbooks:

        table.append([os.path.basename(playbook.playbook),
                      playbook.cache_dir(),
                      playbook.get_status()] +
                     [playbook.extra_vars.get(k, None) for k in column_order])

    # prepend the 'playbook' column
    column_order = ["playbook", "cache_dir", "status"] + column_order

    print tabulate(table, headers=column_order, tablefmt=tabstyle)



@main.command()
@click.option("--playbook-root", "-p",
              callback=_playbook_root_callback, expose_value=False,
              help="Root directory for playbooks with relative paths, "
              "defaults to location of input_binder")
@click.argument('binder_path', type=click.Path(exists=True))
def run(binder_path):
    binder = get_binder(binder_path)

    for playbook in binder():
        if DEBUG:
            playbook.logger.setLevel(logging.DEBUG)

        logger.info("Running %s" % playbook.playbook); t0 = time.time()

        ret = playbook.run()

        logger.info("Finished %s (%s)" % (playbook.playbook, time.time() - t0))

        if ret != 0:
            logger.error("Error running %s" % playbook.playbook)
            sys.exit(ret)


@main.command()
def clean():
    try:
        shutil.rmtree(BinderPlaybook.root_cache_dir + "/")
    except OSError as e:
        logger.debug(str(e))



if __name__ == "__main__":
    main()
