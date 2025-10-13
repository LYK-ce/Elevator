@echo off

:: 安装pygame
pip install pygame
if %ERRORLEVEL% == 0 (
    echo pygame安装成功
    :: 运行main.py
    python main.py
) else (
    echo pygame安装失败，请检查网络或Python环境
)

pause