@echo off
rem Bam dup file nay de mo Bang dieu khien Anna.
setlocal
cd /d "%~dp0"

rem 1) May co Python (cai tu python.org) thi dung pythonw de khong hien cua so den
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%~dp0anna_launcher.py"
  exit /b 0
)

rem 2) Khong co thi nho uv (da cai cung Open-LLM-VTuber) lay Python ve
set "UV=uv"
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
set "PY="
for /f "usebackq delims=" %%P in (`"%UV%" python find 3.12 2^>nul`) do set "PY=%%P"
if not defined PY (
  echo Dang tai Python lan dau, doi mot chut...
  "%UV%" python install 3.12
  for /f "usebackq delims=" %%P in (`"%UV%" python find 3.12 2^>nul`) do set "PY=%%P"
)
if not defined PY (
  echo.
  echo Khong tim thay Python va uv.
  echo Cai Python bang lenh:  winget install Python.Python.3.12
  echo Roi bam dup lai file nay.
  pause
  exit /b 1
)

set "PYW=%PY:python.exe=pythonw.exe%"
if not exist "%PYW%" set "PYW=%PY%"
start "" "%PYW%" "%~dp0anna_launcher.py"
exit /b 0
