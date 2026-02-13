import os
import subprocess
import tempfile


class AbstractPagerProvider(object):
    def __call__(self, message: str):
        raise NotImplementedError()


class LessPagerProvider(AbstractPagerProvider):
    def __call__(self, message):
        fd, temp_file = tempfile.mkstemp(text=True)
        try:
            os.write(fd, message.encode())
            os.close(fd)
            subprocess.call(["less", temp_file])
        finally:
            os.unlink(temp_file)