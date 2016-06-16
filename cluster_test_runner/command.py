from dauber import Playbook, Inventory
import pkg_resources as pr
import argparse
import logging

PACKAGE_NAME = "cluster_test_runner"

def run_playbook(args):
    p = Playbook(args.path, Inventory(['localhost']))
    p.add_extra_vars({'ansible_python_interpreter': 'python2'})
    p.logger.setLevel(getattr(logging, args.loglevel))
    p.logger.info(p.cmd)

    status = p.run()
    if status != 0:
        p.logger.error("There was a problem with the playbook")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--log-level',
        help="Print lots of debugging statements",
        action="store", dest="loglevel", default="INFO",
        choices=["INFO", "WARN", "ERROR", "DEBUG"]

    )
    parser.add_argument(
        "path", help="path to a playbook to run")

    args = parser.parse_args()

    run_playbook(args)

if __name__ == "__main__":
    main()
