def pre_find_module_path(hook_api):
    # Override PyInstaller's default tkinter pre-hook. This environment can
    # import tkinter successfully, but the default isolated probe marks it as
    # broken and excludes it from the build.
    return
