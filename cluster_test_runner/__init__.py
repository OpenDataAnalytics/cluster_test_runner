import logging
from utils import get_click_handler


logger = logging.getLogger('TestRunner')
if not len(logger.handlers):
    logger.addHandler(get_click_handler())
