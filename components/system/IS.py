from . import System


class IS(System):
    def __init__(self):
        super().__init__()
        self.time = self.config['time']
    