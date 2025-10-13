from algorithm import Start_Algorithm
from GUI import GUI
from multiprocessing import Process, Event, Queue

# Add: 确保标准输出和错误输出都使用 UTF-8 编码，以便终端输出内容保存到 result.txt 文件中进行后续分析
# import sys
# import io
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    #定义两个线程之间的同步变量
    start_event = Event()
    finish_event = Event()
    message_queue = Queue()

    algorithm = Process(target=Start_Algorithm, args=(start_event, finish_event, message_queue))
    gui = Process(target=GUI,args=(start_event, finish_event, message_queue))
    algorithm.start()
    gui.start() 

    algorithm.join()
    gui.terminate()
    gui.join()