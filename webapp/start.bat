@echo off
echo [科研助手] 启动论文雷达...
cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [*] 首次运行，创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [*] 安装依赖...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo [*] 访问地址: http://localhost:5001
echo [*] 按 Ctrl+C 停止服务
python app.py
pause
