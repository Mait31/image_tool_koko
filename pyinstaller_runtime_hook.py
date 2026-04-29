from pathlib import Path
import os
import sys


base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
tcl_library = base / "_tcl_data"
tk_library = base / "_tk_data"

if tcl_library.exists():
    os.environ["TCL_LIBRARY"] = str(tcl_library)

if tk_library.exists():
    os.environ["TK_LIBRARY"] = str(tk_library)
