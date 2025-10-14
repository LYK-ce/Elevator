#!/usr/bin/env python3
from typing import List
import time
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent
from GUI import GUI
from utils import Message
from collections import Counter

class ElevatorBusExampleController(ElevatorController):
    def __init__(self, start_event, finish_event, message_queue) -> None: # 初始化函数，传入用于与GUI进程通信的同步变量和消息队列
        super().__init__("http://127.0.0.1:8000", True)
        self.all_passengers: List[ProxyPassenger] = []
        self.max_floor = 0

        #用于与GUI进程进行通信的同步变量和消息队列
        self.start_event = start_event
        self.finish_event = finish_event    
        self.message_queue = message_queue
        self.board = False

        # 新增：记录还在等待的乘客 -> {passenger_id: (origin_floor:int, dir:str 'up'|'down')}
        self.waiting_passengers = {}

        # NEW: 每台电梯的“车内目的层计数”
        self.in_car_targets = {}   # {elevator_id: Counter({floor: count})}

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None: # 最开始给电梯下达第一条指令
        self.max_floor = floors[-1].floor
        self.floors = floors

        # NEW: 为每台电梯建一个 Counter
        self.in_car_targets = {e.id: Counter() for e in elevators}

        for i, elevator in enumerate(elevators):
            # 计算目标楼层 - 均匀分布在不同楼层
            target_floor = (i * (len(floors) - 1)) // len(elevators)
            # 立刻移动到目标位置并开始循环
            elevator.go_to_floor(target_floor, immediate=True)
        # 初始化阶段，打印电梯的初始位置
        print("-----------------------------------")
        print('begin initialization')
        for e in elevators:
            print(f'{e.id} floor:{e.current_floor_float}')
        print("---------------------------------")
        # 把楼层的数量传递给GUI
        new_message = Message(type = 'init', object= 'floor', id = -1, floor =20, state = None)
        self.message_queue.put(new_message)
        
        # 将电梯的初始化事件加入到 message queue 当中
        for e in elevators:
            new_message = Message(type = 'init', object= 'elevator', id = e.id, floor = e.current_floor, state = None)
            self.message_queue.put(new_message)
        pass

    def on_event_execute_start( # 打印即将处理的事件数量及每个事件的类型
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(
                f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]"
                + "[Man]" * len(i.passengers),
                end="",
            )
        print()

    def on_event_execute_end( 
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        '''
        1. 再次打印这一 tick 已处理的事件类型与电梯状态；
        2. 遍历 events，把与乘客相关的消息按规则塞进 message_queue；
        3. 遍历 elevators，把电梯和电梯内乘客的“同步”消息塞进 message_queue；
        4. 用 start_event.set() 通知 GUI 可以消费消息；随后 finish_event.wait() 阻塞，等 GUI 处理完再 clear() 继续。
        '''
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
        print()

        # 在每一个tick处理完毕之后，我们需要通知GUI进程进行更新，然后等待GUI完成更新
        # Ops: Message 里面的 object 字段好像没用，但目前还是不删掉。
        
        # 处理 events
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

    # 以下均为细粒度事件回调（在仿真内核处理 events 时，按需触发）
    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        '''
        把乘客记入 self.all_passengers，打印
        '''
        print(f"[Call] 乘客 P{passenger.id} 在 F{floor.floor} 呼叫电梯 {direction}")
        self.all_passengers.append(passenger)

        # 新增：登记该乘客为“等待中”
        # direction 由仿真回调给出，通常为 'up' 或 'down'
        self.waiting_passengers[passenger.id] = (floor.floor, direction)

        pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        '''
        电梯空闲时发一条“去 1 层”的指令
        '''
        elevator.go_to_floor(2)

    # 新增工具函数：判断“当前方向上是否还有人在等”
    def _has_waiting_ahead(self, current_floor: int, direction: Direction) -> bool:
        """
        是否存在位于当前层“前方”的等待呼叫（不区分 up/down，只要有人就算“有需求”）
        """
        if direction == Direction.UP:
            return any(origin > current_floor for origin, _ in self.waiting_passengers.values())
        elif direction == Direction.DOWN:
            return any(origin < current_floor for origin, _ in self.waiting_passengers.values())
        return False
    
    def _has_waiting_here(self, current_floor: int, direction: Direction) -> bool:
        """
        是否存在位于当前层、且期望与电梯同向的等待呼叫
        """
        if direction not in (Direction.UP, Direction.DOWN):
            return False
        want = 'up' if direction == Direction.UP else 'down'
        return any(origin == current_floor and dir_str == want
                for origin, dir_str in self.waiting_passengers.values())

    def _get_passenger_dest(self, passenger: ProxyPassenger):
        '''获取乘客的目的层'''
        try:
            return int(passenger.destination)   # 直接用 SDK 提供的属性
        except Exception:
            return None

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        '''
        实现调度策略：(最开始是 BUS 调度算法)
        '''
        print(f"[Alert] 电梯 E{elevator.id} 停靠在 F{floor.floor}")
        # 先拿到上一 tick 的运动方向
        dir_last = elevator.last_tick_direction
        curr = elevator.current_floor
        targets = self.in_car_targets.get(elevator.id, Counter())

        if targets:  # 车内优先
            above = [f for f,c in targets.items() if c>0 and f>curr]
            below = [f for f,c in targets.items() if c>0 and f<curr]
            if dir_last == Direction.UP and above:
                next_dir = Direction.UP
            elif dir_last == Direction.DOWN and below:
                next_dir = Direction.DOWN
            else:
                # 向最近的目的层走
                next_dir = Direction.UP if (above and (not below or min(above)-curr <= curr-min(below))) else Direction.DOWN
            dir_last = next_dir
        else:
            # 维持你现在的“本层同向/前方任意方向→保持；否则反转”的逻辑
            has_here  = self._has_waiting_here(curr, dir_last)
            has_ahead = self._has_waiting_ahead(curr, dir_last)
            if not (has_here or has_ahead):
                dir_last = Direction.DOWN if dir_last == Direction.UP else Direction.UP

        # 保持“每次移动一层”的原有风格 + 边界处理
        if dir_last == Direction.UP:
            if curr == self.max_floor:
                # 到顶则掉头向下
                elevator.go_to_floor(curr - 1)
            else:
                elevator.go_to_floor(curr + 1)
        elif dir_last == Direction.DOWN:
            if curr == 0:
                # 到底则掉头向上
                elevator.go_to_floor(curr + 1)
            else:
                elevator.go_to_floor(curr - 1)
        
        '''
        if elevator.last_tick_direction == Direction.UP and elevator.current_floor == self.max_floor:
            elevator.go_to_floor(elevator.current_floor -1)
        # 电梯到达底层后，立即上升一层
        elif elevator.last_tick_direction == Direction.DOWN and elevator.current_floor == 0:
            elevator.go_to_floor(elevator.current_floor + 1)
        elif elevator.last_tick_direction == Direction.UP:
            elevator.go_to_floor(elevator.current_floor + 1)
        elif elevator.last_tick_direction == Direction.DOWN:
            elevator.go_to_floor(elevator.current_floor - 1)
        '''

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        '''
        1. 仅打印乘客上电梯的信息;
        2. 真正把乘客上电梯的信息发给 GUI 的动作是在 on_event_execute_end 里统一完成
        '''
        print(f"[Man] 乘客 P{passenger.id} 进入电梯 E{elevator.id}")
        dest = getattr(passenger, "destination", None)
        if dest is not None and dest != elevator.current_floor:
            self.in_car_targets.setdefault(elevator.id, Counter())[int(dest)] += 1

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        '''
        1. 仅打印乘客下电梯的信息;
        2. 真正把乘客下电梯的信息发给 GUI 的动作是在 on_event_execute_end 里统一完成
        '''
        print(f"[Man] 乘客 P{passenger.id} 离开电梯 E{elevator.id} 在 F{floor.floor}")
        ctr = self.in_car_targets.get(elevator.id)
        if ctr:
            f = floor.floor
            if ctr.get(f, 0) > 0:
                ctr[f] -= 1
                if ctr[f] == 0:
                    del ctr[f]

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        '''
        目前是空实现
        '''
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        '''
        目前是空实现
        '''
        pass


def Start_Algorithm(start_event, finish_event, message_queue):
    algorithm = ElevatorBusExampleController(start_event, finish_event, message_queue)
    algorithm.start()

# Start_Algorithm(None,None,None)