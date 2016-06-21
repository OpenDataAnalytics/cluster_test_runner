import copy
import logging
import click

# http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
def recursive_hash(o):
  """
  Makes a hash from a dictionary, list, tuple or set to any level, that contains
  only other hashable types (including any lists, tuples, sets, and
  dictionaries).
  """

  if isinstance(o, (set, tuple, list)):

    return tuple([recursive_hash(e) for e in o])

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = recursive_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))




class ColorFormatter(logging.Formatter):
    _colors = {
        'ERROR': dict(fg='red', bold=True),
        'EXCEPTION': dict(fg='red', bold=True),
        'CRITICAL': dict(fg='red', bold=True),
        'DEBUG': dict(fg='blue', bold=True),
        'WARNING': dict(fg='yellow', bold=True),
        'INFO': dict(fg='green', bold=True)
    }
    def __init__(self, *args, **kwargs):
        self.colors = ColorFormatter._colors.copy()
        self.colors.update(kwargs.get("colors", {}))
        try:
            del kwargs['colors']
        except KeyError:
            pass

        super(ColorFormatter, self).__init__(*args, **kwargs)


    def format(self, record):
        if not record.exc_info:
            record.levelname = click.style(record.levelname, **self.colors[record.levelname])
        return logging.Formatter.format(self, record)


class ClickHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            err = record.levelname in ('warning', 'error', 'exception', 'critical')
            click.echo(msg, err=err)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


def get_click_handler(fmt='%(asctime)s - %(name)-15s - %(levelname)s - %(message)s',
                      **colors):
    formatter = ColorFormatter(fmt, colors=colors)
    ch = ClickHandler()
    ch.setFormatter(formatter)
    return ch
