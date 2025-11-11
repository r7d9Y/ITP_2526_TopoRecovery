import parser
import logging

logger = logging.getLogger(__name__)

FORMAT = '_%(ip)-15s:%(port)s--%(message)s'
DATE_TIME_FORMAT = '%Y:%m:%d_%H:%M:%S'


def main():
    logging.basicConfig(filename='log.txt',
                        datefmt=DATE_TIME_FORMAT,
                        format=FORMAT
                        )
    logger.info('Started')
    parser.parse("output.txt", "1.2.3.4", 80)
    logger.info('Finished')


if __name__ == '__main__':
    main()
