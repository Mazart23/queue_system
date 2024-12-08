from . import System


class IS_segmented(System):
    def __init__(self):
        super().__init__()
        self.segment_watchtime = self.config['segment_watchtime']
        self.earlier_download = self.config['earlier_download']
