'''
prensted by LiYongKang
The util includes several common class definitions and functions.
'''

class Message:
    '''
    Message class for inter-process communication.
    '''
    def __init__(self, type: str, object: str, id: int, floor: int, state  : int = 0, delay = False):
        self.type = type  # 'init', 'move', 'stop', 'call', 'arrive'
        self.object = object  # 'elevator' or 'passenger'
        self.id = id  # elevator id or passenger id
        self.floor = floor  # current floor
        self.state = state
        self.delay = delay
      

