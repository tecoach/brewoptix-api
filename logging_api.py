import os
from logging import Logger, getLevelName

import rollbar


class LoggerWithThirdParty(Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rollbar_secret = os.getenv("ROLLBAR_SECRET")
        environment = os.getenv("STAGE", "dev")

        if self.rollbar_secret:
            try:    # we dont want the api to go down if rollbar goes down
                rollbar.init(self.rollbar_secret, environment)
            except:
                print("Unable to initialize rollbar")
                pass

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        try:
            fn, lno, func, sinfo = self.findCaller(stack_info)
        except ValueError:  # pragma: no cover
            fn, lno, func, sinfo = "(unknown file)", 0, "(unknown function)", None

        extra_data = {
            'file': fn,
            'line': lno,
            'module': func,
            'sinfo': sinfo
        }
        super()._log(level, msg, args, exc_info, extra, stack_info)

        if self.rollbar_secret:
            try:
                if level >= 40:    # on error or critical
                    rollbar.report_message(msg, getLevelName(level).lower(), extra_data=extra_data)
            except:
                print("Unable to report message to rollbar")
                pass

    def log_uncaught_exception(self):
        if self.rollbar_secret:
            try:
                rollbar.report_exc_info()
                rollbar.wait()
            except:
                print("Unable to catch errors with rollbar")
                pass

        raise