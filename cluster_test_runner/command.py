from dauber import Playbook, Inventory
from binder import Binder
import yaml
import argparse
import logging
import sys

DEBUG = False

logger = logging.getLogger("ctr")

def excepthook(exctype, value, traceback):
    global DEBUG

    if DEBUG:
        sys.__excepthook__(exctype, value, traceback)
    else:
        logger.error("%s: %s" % (value.__class__.__name__, str(value)))

    sys.exit(1)

sys.excepthook = excepthook

def init_logger(level):
    logger = logging.getLogger("ctr")
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    logger.addHandler(ch)



def run_playbook(args):
    p = Playbook(Inventory(['localhost']))
    p.logger.setLevel(getattr(logging, args.loglevel))

    status = p.run(args.path)
    if status != 0:
        p.logger.error("There was a problem with the playbook")


def parse_binder(input_binder_path):
    try:
        with open(input_binder_path, "rb") as fh:
            binder_list = yaml.load(fh.read())

        if len(binder_list) > 1:
            logger.warn("More than one binder detected. Dropping all but first binder.")

        return binder_list[0]

    except IOError as e:
        logger.error("Could not read %s" % input_binder_path)
        sys.exit(1)
    except yaml.scanner.ScannerError:
        logger.error("Could not parse %s" % input_binder_path)
        sys.exit(1)


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
        "input_binder", help="path to a playbook to run")

    args = parser.parse_args()

    if args.debug or args.loglevel == "DEBUG":
        DEBUG = True

    init_logger(getattr(logging, args.loglevel))

    binder = parse_binder(args.input_binder)


if __name__ == "__main__":
    main()
