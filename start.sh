#!/bin/bash

# 安装pygame
pip install pygame

# 检查pip install是否成功
if [ $? -eq 0 ]; then
    echo "pygame安装成功"
    # 运行main.py
    python main.py
else
    echo "pygame安装失败，请检查网络或Python环境"
fi