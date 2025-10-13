This is a homework for Software Engineering

The GUI part is presented by LiYongKang

GUI is built with pygame

Update Log:

10.7 version 0.92
现在GUI已经基本没有问题了，可以正确的显示每一个事件。唯一的问题是模拟器的反馈结果并不一致。
主要是在停靠，上电梯，下电梯这几件事上。停靠和上电梯不在同一个tick上，这意味着上电梯时，电梯已经不在那一层了，因此动画上会脱节。
而下电梯和停靠在同一个tick上，这点倒反而好处理。
如果能把上电梯和停靠放在同一个tick就好了，我需要再去确认下能否改成这样。否则我就必须实现很复杂的特殊情况处理。我真是艹了。

10.9 version 0.93
修复了每一帧渲染完后卡顿的bug，主要是电梯和乘客的更新逻辑写的有问题。更新完后就解决了。
现在就等模拟器更新，添加一个电梯动的事件即可。然后再更新一下素材就可以了。

10.9 version 0.94
解决了一个小bug，之前忘了把up button pressed事件添加进去导致上楼的乘客不能正确生成

10.9 version 0.95
解决了动画脱节的问题。接下来把sprite内容完善一下即可。

10.10 version 1.0
修复了windows和linux系统下路径名不同的问题。更新了sprite素材，现在增加了环境sprite，人物sprite。到这里GUI的初始版本就算是完成了。

10.13 version 1.0
更新了课程要求的运行脚本


10.12 version 1.5
更新了电梯调度算法。