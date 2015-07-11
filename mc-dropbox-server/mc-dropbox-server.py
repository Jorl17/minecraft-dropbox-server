import os
import urllib.request
import urllib.parse
import json

__author__ = 'jorl17'

CENTRAL_SERVER_ADDRESS='http://localhost:9000'

#From http://stackoverflow.com/a/12118327
def _get_appdata_path():
    import ctypes
    from ctypes import wintypes, windll
    CSIDL_APPDATA = 26
    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                 ctypes.c_int,
                                 wintypes.HANDLE,
                                 wintypes.DWORD,
                                 wintypes.LPCWSTR]
    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    result = _SHGetFolderPath(0, CSIDL_APPDATA, 0, 0, path_buf)
    return path_buf.value

#From http://stackoverflow.com/a/12118327
def dropbox_home():
    from platform import system
    import base64
    import os.path
    _system = system()
    if _system in ('Windows', 'cli'):
        host_db_path = os.path.join(_get_appdata_path(),
                                    'Dropbox',
                                    'host.db')
    elif _system in ('Linux', 'Darwin'):
        host_db_path = os.path.expanduser('~'
                                          '/.dropbox'
                                          '/host.db')
    else:
        raise RuntimeError('Unknown system={}'.format(_system))
    if not os.path.exists(host_db_path):
        raise RuntimeError("Config path={} doesn't exists".format(host_db_path))
    with open(host_db_path, 'r') as f:
        data = f.read().split()

    return base64.b64decode(data[1]).decode('utf-8')

def check_central_server(server = CENTRAL_SERVER_ADDRESS):
    try:
        f = urllib.request.urlopen(server)
        response = f.read().decode('utf-8')
        d = json.loads(response)
        if d['online']:
            return d['ip']
        else:
            return False
    except Exception as e:
        print('Could not access central server: ' + str(e))
        return None


def check_dropbox_file(server_folder='minecraft-server', dropbox_home_path=dropbox_home()):
    path = os.path.join(dropbox_home_path, server_folder, 'mc_dropbox_server_status.txt')

    try:
        with open(path) as f:
            lines = f.readlines()
            if lines:
                ip = lines[0].strip()
                return ip
            else:
                return False
    except:
        return False


def is_someone_running_server():
    status = check_central_server()
    if status == None:
        return check_dropbox_file()
    else:
        return status


def inform_central_server(ip, central_server_address=CENTRAL_SERVER_ADDRESS):
    data = urllib.parse.urlencode({'ip': ip}).encode()
    header = {"Content-Type": "application/x-www-form-urlencoded"}
    req = urllib.request.Request(central_server_address, data, header)
    f = urllib.request.urlopen(req)


def get_public_ip():
    f = urllib.request.urlopen('http://ipv4bot.whatismyipaddress.com')
    return f.read().decode()


def update_dropbox_state(ip, server_folder='minecraft-server', dropbox_home_path=dropbox_home()):
    path = os.path.join(dropbox_home_path, server_folder, 'mc_dropbox_server_status.txt')

    with open(path, 'w') as f:
        f.write(ip)

def mark_server_as_running():
    our_ip = get_public_ip()
    inform_central_server(our_ip)
    update_dropbox_state(our_ip)

mark_server_as_running()