@echo off
REM 三思GDB巡检平台 — Windows 安装脚本
REM 支持 Python 3.10+
REM 用法：双击运行或在项目根目录执行 scripts\install.bat

setlocal EnableDelayedExpansion

set PYTHON=

REM 尝试 py launcher（Windows 官方安装器附带）
py -3 --version >nul 2>&1
if %errorlevel% == 0 (
  for /f "tokens=*" %%i in ('py -3 -c "import sys; print(sys.version_info >= (3,10))"') do set PYCHECK=%%i
  if "!PYCHECK!" == "True" (
    set PYTHON=py -3
    goto found_python
  )
)

REM 尝试 python3
python3 --version >nul 2>&1
if %errorlevel% == 0 (
  for /f "tokens=*" %%i in ('python3 -c "import sys; print(sys.version_info >= (3,10))"') do set PYCHECK=%%i
  if "!PYCHECK!" == "True" (
    set PYTHON=python3
    goto found_python
  )
)

REM 尝试 python
python --version >nul 2>&1
if %errorlevel% == 0 (
  for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version_info >= (3,10))"') do set PYCHECK=%%i
  if "!PYCHECK!" == "True" (
    set PYTHON=python
    goto found_python
  )
)

echo [ERROR] 未找到 Python 3.10+，请先安装 Python 3.10 或更高版本。
echo         下载：https://www.python.org/downloads/
pause
exit /b 1

:found_python
for /f "tokens=*" %%v in ('%PYTHON% --version') do echo [OK] 使用 Python：%%v

REM 切换到项目根目录
pushd "%~dp0.."

if not exist "requirements.txt" (
  echo [ERROR] 未找到 requirements.txt
  pause
  exit /b 1
)

echo [1/3] 创建虚拟环境...
if not exist "venv" (
  %PYTHON% -m venv venv
  echo       已创建 venv\
) else (
  echo       venv\ 已存在，跳过创建
)

call venv\Scripts\activate.bat

echo [2/3] 安装依赖（在线）...
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo       依赖安装完成

echo [3/3] 初始化配置...
if not exist "config.yaml" (
  if exist "config.example.yaml" (
    copy config.example.yaml config.yaml >nul
    echo       已生成 config.yaml（请按需修改）
  )
) else (
  echo       config.yaml 已存在，跳过
)

echo.
echo ==============================
echo  安装完成！
echo ==============================
echo.
echo  启动 Web 界面：
echo    venv\Scripts\activate.bat
echo    python -m src.main web
echo.
popd
pause
