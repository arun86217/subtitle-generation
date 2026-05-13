```bat
@echo off
setlocal EnableDelayedExpansion

title Offline Subtitle Generator Installer

color 0A

echo ==========================================
echo OFFLINE SUBTITLE GENERATOR INSTALLER
echo ==========================================
echo.

REM =========================================================
REM CHECK INTERNET
REM =========================================================

echo Checking internet connection...

ping google.com -n 1 >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No internet connection detected.
    pause
    exit /b 1
)

echo Internet OK.
echo.

REM =========================================================
REM PYTHON INSTALL
REM =========================================================

echo Checking Python...

where python >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (

    echo Python not found.
    echo Downloading Python 3.11.9...

    powershell -Command ^
    "Invoke-WebRequest https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -OutFile python_installer.exe"

    IF NOT EXIST python_installer.exe (
        echo ERROR: Failed downloading Python installer.
        pause
        exit /b 1
    )

    echo Installing Python silently...
    
    start /wait python_installer.exe ^
    /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    del python_installer.exe

    echo Refreshing PATH...

    set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts"

)

echo.
python --version

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python installation failed.
    pause
    exit /b 1
)

echo Python OK.
echo.

REM =========================================================
REM FFMPEG INSTALL
REM =========================================================

echo ==========================================
echo INSTALLING FFMPEG
echo ==========================================
echo.

if exist ffmpeg_temp rmdir /s /q ffmpeg_temp
if exist ffmpeg.zip del /f /q ffmpeg.zip

mkdir ffmpeg_temp

echo Downloading FFmpeg...

powershell -Command ^
"Invoke-WebRequest https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip"

IF NOT EXIST ffmpeg.zip (
    echo ERROR: Failed downloading FFmpeg.
    pause
    exit /b 1
)

echo Extracting FFmpeg...

powershell -Command ^
"Expand-Archive ffmpeg.zip -DestinationPath ffmpeg_temp"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed extracting FFmpeg.
    pause
    exit /b 1
)

if exist ffmpeg rmdir /s /q ffmpeg
mkdir ffmpeg
mkdir ffmpeg\bin

set FOUND_FFMPEG=0

for /d %%i in (ffmpeg_temp\ffmpeg-*) do (
    xcopy /E /I /Y "%%i\bin" "ffmpeg\bin" >nul
    set FOUND_FFMPEG=1
)

if "!FOUND_FFMPEG!"=="0" (
    echo ERROR: FFmpeg extraction failed.
    pause
    exit /b 1
)

del ffmpeg.zip
rmdir /s /q ffmpeg_temp

echo.
echo Validating FFmpeg...

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

ffmpeg\bin\ffmpeg.exe -version >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: FFmpeg validation failed.
    pause
    exit /b 1
)

echo FFmpeg installed successfully.
echo.

REM =========================================================
REM CREATE VENV
REM =========================================================

echo ==========================================
echo CREATING VIRTUAL ENVIRONMENT
echo ==========================================
echo.

if exist venv (
    echo Existing venv found.
) else (
    python -m venv venv
)

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed creating virtual environment.
    pause
    exit /b 1
)

echo Virtual environment OK.
echo.

REM =========================================================
REM UPDATE PIP
REM =========================================================

echo Updating pip...

venv\Scripts\python.exe -m pip install --upgrade pip

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed updating pip.
    pause
    exit /b 1
)

echo Pip updated.
echo.

REM =========================================================
REM INSTALL REQUIREMENTS
REM =========================================================

echo ==========================================
echo INSTALLING DEPENDENCIES
echo ==========================================
echo.

IF NOT EXIST requirements.txt (
    echo ERROR: requirements.txt not found.
    pause
    exit /b 1
)

venv\Scripts\pip.exe install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo Dependencies installed successfully.
echo.

REM =========================================================
REM DOWNLOAD WHISPER MODEL
REM =========================================================

echo ==========================================
echo DOWNLOADING WHISPER MODEL
echo ==========================================
echo.

if not exist models mkdir models
if not exist models\faster-whisper-base mkdir models\faster-whisper-base

if exist models\faster-whisper-base\model.bin (
    echo Whisper model already exists.
    goto :MODEL_DONE
)

echo Downloading config.json...

powershell -Command ^
"Invoke-WebRequest https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json -OutFile models\faster-whisper-base\config.json"

echo Downloading tokenizer.json...

powershell -Command ^
"Invoke-WebRequest https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json -OutFile models\faster-whisper-base\tokenizer.json"

echo Downloading vocabulary.txt...

powershell -Command ^
"Invoke-WebRequest https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.txt -OutFile models\faster-whisper-base\vocabulary.txt"

echo Downloading preprocessor_config.json...

powershell -Command ^
"Invoke-WebRequest https://huggingface.co/Systran/faster-whisper-base/resolve/main/preprocessor_config.json -OutFile models\faster-whisper-base\preprocessor_config.json"

echo Downloading model.bin...
echo This may take several minutes...

powershell -Command ^
"Invoke-WebRequest https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin -OutFile models\faster-whisper-base\model.bin"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed downloading Whisper model.
    pause
    exit /b 1
)

if not exist models\faster-whisper-base\model.bin (
    echo ERROR: model.bin missing
    pause
    exit /b 1
)

echo Whisper model downloaded successfully.
echo.

:MODEL_DONE

REM =========================================================
REM WORKDIR
REM =========================================================

echo Creating work directory...

if not exist workdir mkdir workdir

echo Work directory OK.
echo.

REM =========================================================
REM VALIDATION
REM =========================================================

echo ==========================================
echo RUNNING FINAL VALIDATION
echo ==========================================
echo.

venv\Scripts\python.exe -c "import faster_whisper"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: faster-whisper validation failed.
    pause
    exit /b 1
)

echo Python package validation OK.
echo.

echo Testing FFmpeg...

ffmpeg\bin\ffmpeg.exe -version >nul 2>nul

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: FFmpeg failed.
    pause
    exit /b 1
)

echo FFmpeg validation OK.
echo.

echo ==========================================
echo INSTALL COMPLETE
echo ==========================================
echo.
echo Launch application using:
echo.
echo run_gui.bat
echo.
echo Everything installed successfully.
echo.

pause
```
