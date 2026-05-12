@echo off
setlocal EnableDelayedExpansion

title Offline Subtitle Generator Installer

echo ======================================
echo OFFLINE SUBTITLE GENERATOR INSTALLER
echo ======================================
echo.

REM ======================================
REM PYTHON INSTALL
REM ======================================

where python >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo Python not found.
    echo Downloading Python...

    powershell -Command ^
    "Invoke-WebRequest https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -OutFile python_installer.exe"

    echo Installing Python silently...

    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    del python_installer.exe
)

echo.
python --version

REM ======================================
REM FFMPEG INSTALL
REM ======================================

echo.
echo Installing FFmpeg...

if exist ffmpeg_temp rmdir /s /q ffmpeg_temp
mkdir ffmpeg_temp

powershell -Command ^
"Invoke-WebRequest https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip"

powershell -Command ^
"Expand-Archive ffmpeg.zip -DestinationPath ffmpeg_temp"

if exist ffmpeg rmdir /s /q ffmpeg
mkdir ffmpeg

for /d %%i in (ffmpeg_temp\ffmpeg-*) do (
    xcopy /E /I /Y "%%i\bin" "ffmpeg\bin"
)

del ffmpeg.zip
rmdir /s /q ffmpeg_temp

echo.
echo Verifying FFmpeg...

if not exist ffmpeg\bin\ffmpeg.exe (
    echo ERROR: ffmpeg.exe missing
    pause
    exit /b 1
)

if not exist ffmpeg\bin\ffprobe.exe (
    echo ERROR: ffprobe.exe missing
    pause
    exit /b 1
)

echo FFmpeg installed successfully.
echo.

REM ======================================
REM VENV
REM ======================================

echo Creating virtual environment...

python -m venv venv

call venv\Scripts\activate

echo.
echo Updating pip...

python -m pip install --upgrade pip

echo.
echo Installing dependencies...

pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

REM ======================================
REM WHISPER MODEL
REM ======================================

echo.
echo Downloading Whisper model...

if not exist models mkdir models

where git >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git is not installed.
    echo Install Git:
    echo https://git-scm.com/download/win
    pause
    exit /b 1
)

git lfs install

if not exist models\faster-whisper-base (
    git clone https://huggingface.co/Systran/faster-whisper-base models\faster-whisper-base
)

REM ======================================
REM WORKDIR
REM ======================================

echo.
echo Creating work directory...

if not exist workdir mkdir workdir

REM ======================================
REM VALIDATION
REM ======================================

echo.
echo Running validation...

ffmpeg\bin\ffmpeg.exe -version >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo FFmpeg validation failed
    pause
    exit /b 1
)

ffmpeg\bin\ffprobe.exe -version >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo FFprobe validation failed
    pause
    exit /b 1
)

python -c "import faster_whisper" >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo faster-whisper validation failed
    pause
    exit /b 1
)

echo.
echo ======================================
echo INSTALL COMPLETE
echo ======================================
echo.
echo Launch using:
echo run_gui.bat
echo.

pause