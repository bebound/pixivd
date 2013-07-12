import sys

from cx_Freeze import setup, Executable

includes = ["atexit","re"]
includefiles = []

if sys.platform == "win32":
    exe = Executable(
	script = "main.py",
	#base = "Win32GUI"
	)

setup(
        name = "Pixiv Downloader",
        version = "0.9",
        options = {"build_exe" : {"includes" : includes , 'include_files' : includefiles}},
        executables = [exe]
     )

