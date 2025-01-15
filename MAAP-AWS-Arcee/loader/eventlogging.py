import logging
import logging.handlers
class EventLogger:
    def get_logger():
        log_file_name = './applogs/MAAP.log'
        name="werkzeug"
        logging_level = logging.DEBUG
        # set TimedRotatingFileHandler for root
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        # use very short interval for this example, typical 'when' would be 'midnight' and no explicit interval
        handler = logging.handlers.TimedRotatingFileHandler(log_file_name, when="midnight", backupCount=10)
        handler.suffix= "%Y-%m-%d.log"

        handler.setFormatter(formatter)
        logger = logging.getLogger(name) # or pass string to give it a name
        logger.addHandler(handler)
        logger.setLevel(logging_level)
        return logger
