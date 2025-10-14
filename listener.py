#!/usr/bin/env python3
from typing import List
import time
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent
from GUI import GUI
from utils import Message
from collections import Counter

class Listener(ElevatorController):
    def __init__(self, start_event, finish_event, message_queue) -> None: # 初始化函数，传入用于与GUI进程通信的同步变量和消息队列
        super().__init__("http://127.0.0.1:8000", True)

        #用于与GUI进程进行通信的同步变量和消息队列
        self.start_event = start_event
        self.finish_event = finish_event    
        self.message_queue = message_queue
        self.board = False


    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None: # 最开始给电梯下达第一条指令
        self.floors = floors


        print("---------------------------------Listener on_init---------------------------------")
        # 把楼层的数量传递给GUI
        if self.message_queue != None:
            new_message = Message(type = 'init', object= 'floor', id = -1, floor =20, state = None)
            self.message_queue.put(new_message)
            
            # 将电梯的初始化事件加入到 message queue 当中
            for e in elevators:
                new_message = Message(type = 'init', object= 'elevator', id = e.id, floor = e.current_floor, state = None)
                self.message_queue.put(new_message)


       

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        pass

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        pass

    def on_elevator_idle(self, elevator):
        pass

    def on_elevator_stopped(self, elevator, floor):
        pass

    def on_event_execute_start(self, tick, events, elevators, floors):
        pass

    def on_passenger_call(self, passenger, floor, direction):
        pass

    def on_event_execute_end( 
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        '''
        1. 再次打印这一 tick 已处理的事件类型与电梯状态；
        2. 遍历 events，把与乘客相关的消息按规则塞进 message_queue；
        3. 遍历 elevators，把电梯和电梯内乘客的“同步”消息塞进 message_queue；
        4. 用 start_event.set() 通知 GUI 可以消费消息；随后 finish_event.wait() 阻塞，等 GUI 处理完再 clear() 继续。
        '''
        print('***********************listerner on_event_execute_end******************************')
        print(f"Tick {tick}: 处理了 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(
                f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]"
                + "[Man]" * len(i.passengers),
                end="",
            )
            print(i.passengers)
        for e in events:
            print(e.type)
        print('***********************listerner on_event_execute_end******************************')

        # 在每一个tick处理完毕之后，我们需要通知GUI进程进行更新，然后等待GUI完成更新
        # Ops: Message 里面的 object 字段好像没用，但目前还是不删掉。
        
        # 处理 events
        if self.message_queue != None:
            self.board = False
            for e in events:
                # 乘客的初始化事件
                if e.type.value == 'down_button_pressed' or e.type.value == 'up_button_pressed':
                    new_message = Message(type = 'init', object= 'passenger', id = e.data['passenger'], floor = e.data['floor'], state = None, delay = False)
                    self.message_queue.put(new_message)
                # 乘客登上电梯事件
                elif e.type.value == 'passenger_board':
                    print('------passenger board----------:\n')
                    print(f"{e.data['passenger']} floor = {e.data['floor']}, state = {e.data['elevator']}")
                    new_message = Message(type = 'passenger', object= None, id = e.data['passenger'], floor = e.data['floor'], state = e.data['elevator'], delay = False)
                    self.message_queue.put(new_message)

                    # 新增：该乘客已上车，不再算“等待中”
                    self.waiting_passengers.pop(e.data['passenger'], None)

                    # 本 tick 有乘客上电梯 -> 后续电梯内乘客刷新消息用 delay
                    self.board = True
                # 乘客离开电梯事件，注意，由于模拟器把停靠和离开放在同一 tick 里，因此这里是 delay 事件
                elif e.type.value == 'passenger_alight':
                    # 乘客下电梯时不在电梯内了，检索不到，所以这里再塞入一个事件
                    new_message = Message(type = 'passenger', object= 'passenger', id = e.data['passenger'], floor = (e.data['floor']), state = -2, delay = False)
                    self.message_queue.put(new_message)
                    # 如果没有下面这句，GUI 里面，乘客会“漂浮在空中”
                    new_message2 = Message(type = 'passenger', object= 'passenger', id = e.data['passenger'], floor = e.data['floor'], state = -1, delay = True)
                    self.message_queue.put(new_message2)
            
            # 处理 elevators
            for e in elevators:
                # 如果有乘客上电梯，则 delay
                if self.board:
                    delay = True    
                else:
                    delay = False   
                new_message = Message(type = 'elevator', object= None, id = e.id, floor = e.current_floor_float, state = 0, delay= delay)
                self.message_queue.put(new_message)
                # 为电梯中的每个用户创建事件
                for p in e.passengers:
                    new_message = Message(type = 'passenger', object= None, id = p, floor = e.current_floor_float, state = -2,delay= delay)
                    self.message_queue.put(new_message)
            # 消息已经准备好了，通知 GUI 进程可以进行更新
            self.start_event.set()
            # 等待 GUI 进程完成更新，这里的 wait 必须后面跟着一个 clear，否则无法生效
            self.finish_event.wait()
            self.finish_event.clear()







def Start_Listener(start_event, finish_event, message_queue):
    algorithm = Listener(start_event, finish_event, None)
    algorithm.start()

# Start_Algorithm(None,None,None)