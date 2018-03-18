from tasksync.config import executions
from tasksync.sync import sync_all

import argparse
import logging
import oauth2client.tools

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser('tasksync', parents=[oauth2client.tools.argparser])
    parser.add_argument('--debug', action='store_true', default=False, help='Enable debugging.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        httplib2.debuglevel=4


    runbook = executions(args)
    for p in runbook:
        logger.info("Running - %s.", p)
        sync_all(runbook[p])

if __name__ == "__main__":
    main()
