"""Pick up newly installed Windows runtimes without replacing caller overrides."""
import ntpath
import os
import re

def _registered_environment():
    import winreg
    result = []
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
                       (winreg.HKEY_CURRENT_USER, 'Environment')):
        values = {}
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                for name in ('Path', 'JAVA_HOME', 'PAFTA_JAVA'):
                    try:
                        value, kind = winreg.QueryValueEx(key, name)
                        if kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and isinstance(value, str):
                            values[name] = value
                    except OSError:
                        pass
        except OSError:
            pass
        result.append(values)
    return result

def refresh_windows_runtime_env(environ=None, *, platform=None, read_registry=None):
    """Append registered paths; preserve explicit process PATH/Java precedence.

    This changes only this process, never the registry or persistent settings.
    The return value contains changed variable names, never their private values.
    """
    if (os.name if platform is None else platform) != 'nt':
        return []
    env = os.environ if environ is None else environ
    try:
        registered = (read_registry or _registered_environment)()
    except OSError:
        return []
    def key(name):
        return next((k for k in env if k.casefold() == name.casefold()), name)
    def expand(value):
        for _ in range(4):
            new = re.sub(r'%([^%]+)%', lambda m: env.get(key(m[1]), m[0]), value)
            if new == value:
                break
            value = new
        return value
    changed = []
    for name in ('JAVA_HOME', 'PAFTA_JAVA'):
        target = key(name)
        if not env.get(target):
            value = next((layer[name] for layer in reversed(registered) if layer.get(name)), '')
            if value:
                env[target] = expand(value)
                changed.append(name)
    target = key('PATH')
    original = env.get(target, '')
    normalize = lambda path: ntpath.normcase(ntpath.normpath(path.strip('"')))
    seen = {normalize(p) for p in original.split(';') if p}
    added = []
    for layer in registered:
        for path in expand(layer.get('Path', '')).split(';'):
            if path and normalize(path) not in seen:
                seen.add(normalize(path))
                added.append(path)
    if added:
        env[target] = original + (';' if original and not original.endswith(';') else '') + ';'.join(added)
        changed.append('PATH')
    return changed
