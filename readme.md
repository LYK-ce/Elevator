This is a homework for Software Engineering

The GUI part is presented by LiYongKang
GUI is built with pygame

Update Log:
10.7 version 0.92
现在GUI已经基本没有问题了，可以正确的显示每一个事件。唯一的问题是模拟器的反馈结果并不一致。
主要是在停靠，上电梯，下电梯这几件事上。停靠和上电梯不在同一个tick上，这意味着上电梯时，电梯已经不在那一层了，因此动画上会脱节。
而下电梯和停靠在同一个tick上，这点倒反而好处理。
如果能把上电梯和停靠放在同一个tick就好了，我需要再去确认下能否改成这样。否则我就必须实现很复杂的特殊情况处理。我真是艹了。
