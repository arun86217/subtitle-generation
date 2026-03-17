@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

echo ============================================================
echo SYSTEM CHECK - VIDEO TRANSCRIPTION SETUP
echo ============================================================

echo.
echo [1] Checking Python...

where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    where python3 >nul 2>nul
    IF %ERRORLEVEL% NEQ 0 (
        echo FAIL: Python not found
        echo.
        echo Install Python:
        echo https://www.python.org/downloads/windows/
        echo IMPORTANT: Enable "Add Python to PATH"
        goto :end
    ) ELSE (
        set PYTHON=python3
    )
) ELSE (
    set PYTHON=python
)

echo OK: Python found
%PYTHON% --version

echo.
echo [2] Creating virtual environment...

IF NOT EXIST venv (
    %PYTHON% -m venv venv
    echo venv created
) ELSE (
    echo venv already exists
)

echo.
echo [3] Activating virtual environment...
call venv\Scripts\activate

echo.
echo [4] Installing requirements...

IF EXIST requirements.txt (
    pip install --upgrade pip
    pip install -r requirements.txt
) ELSE (
    echo WARNING: requirements.txt not found
)

echo.
echo [5] Checking FFmpeg...

where ffmpeg >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo FAIL: ffmpeg not found
    echo.
    echo Install:
    echo 1. Download: https://www.gyan.dev/ffmpeg/builds/
    echo 2. Extract to C:\ffmpeg
    echo 3. Add C:\ffmpeg\bin to PATH
) ELSE (
    echo OK: ffmpeg found
)

echo.
echo [6] Checking ENV variables...

IF "%WORKING_DIR%"=="" (
    echo FAIL: WORKING_DIR not set
    echo Example:
    echo set WORKING_DIR=D:\temp
) ELSE (
    echo WORKING_DIR=%WORKING_DIR%
)

IF "%WHISPER_MODEL_PATH%"=="" (
    echo FAIL: WHISPER_MODEL_PATH not set
    echo Example:
    echo set WHISPER_MODEL_PATH=D:\models\faster-whisper-base
) ELSE (
    echo WHISPER_MODEL_PATH=%WHISPER_MODEL_PATH%
)

echo.
echo [7] Model check...

IF "%WHISPER_MODEL_PATH%"=="" (
    echo Skipped (env not set)
) ELSE (
    IF EXIST "%WHISPER_MODEL_PATH%\model.bin" (
        echo OK: model found
    ) ELSE (
        echo FAIL: model not found
        echo.
        echo Download manually:
        echo git lfs install
        echo git clone https://huggingface.co/Systran/faster-whisper-base
    )
)

echo.
echo ============================================================
echo SETUP COMPLETE (verify failures above if any)
echo ============================================================

:end
pause