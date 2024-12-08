from . import System
from ..users import User


class FIFO(System):
    def __init__(self):
        super().__init__()
    
    def process(self, user: User):
        pass