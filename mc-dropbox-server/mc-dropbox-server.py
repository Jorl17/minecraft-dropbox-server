#!/usr/bin/env python3
##
## Copyright (C) 2015 João Ricardo Lourenço <jorl17.8@gmail.com>
##
## Github: https://github.com/Jorl17
##
## Project main repository: https://github.com/Jorl17/minecraft-dropbox-server
##
## This file is part of minecraft-dropbox-server.
##
## minecraft-dropbox-server is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 2 of the License, or
## (at your option) any later version.
##
## minecraft-dropbox-server is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with minecraft-dropbox-server.  If not, see <http://www.gnu.org/licenses/>.
##
from optparse import OptionParser
import os
import subprocess
import urllib.request
import urllib.parse
import json
from os.path import isfile

__author__ = 'jorl17'

CENTRAL_SERVER_ADDRESS='http://localhost:9000'
DEFAULT_JVM_OPTIONS='-Xmx3G -Xms2G -jar'

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
def autodetect_dropbox_home():
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
        raise RuntimeError("Config path={} doesn't exist".format(host_db_path))
    with open(host_db_path, 'r') as f:
        data = f.read().split()

    return base64.b64decode(data[1]).decode('utf-8')

def check_central_server(secret_key, server = CENTRAL_SERVER_ADDRESS):
    if not server:
        return None
    try:
        req = urllib.request.Request(server + '?key=' + secret_key + '')
        f = urllib.request.urlopen(req)
        response = f.read().decode('utf-8')
        d = json.loads(response)
        if d['online']:
            return d['ip']
        else:
            return False
    except Exception as e:
        print('Could not access central server: ' + str(e))
        return None


def check_dropbox_file(server_folder_path):
    path = os.path.join(server_folder_path, 'mc_dropbox_server_status.txt')

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


def is_someone_running_server(central_server_address, server_folder_path, secret_key):
    status = check_central_server(secret_key, central_server_address)
    status_dropbox = check_dropbox_file(server_folder_path)
    if status != None:
        if status == status_dropbox:
            return status
        else:
            print('Dropbox and server disagree. Notifying server of status update (Dropbox is probably correct)')
            inform_central_server(status, secret_key, central_server_address)
    else:
        return status_dropbox

def inform_central_server(ip, secret_key, central_server_address=CENTRAL_SERVER_ADDRESS):
    if not central_server_address:
        return
    try:
        if ip:
            data = urllib.parse.urlencode({'key': secret_key, 'message': 'started', 'ip': ip}).encode()
        else:
            data = urllib.parse.urlencode({'key': secret_key, 'message': 'stopped'}).encode()
        header = {"Content-Type": "application/x-www-form-urlencoded"}
        req = urllib.request.Request(central_server_address, data, header)
        f = urllib.request.urlopen(req)
    except Exception as e:
        print('Could not inform central server: ' + str(e))
        return None


def get_public_ip():
    f = urllib.request.urlopen('http://ipv4bot.whatismyipaddress.com')
    return f.read().decode()


def update_dropbox_state(ip, server_folder):
    path = os.path.join(server_folder, 'mc_dropbox_server_status.txt')

    if ip:
        with open(path, 'w') as f:
            f.write(ip)
    else:
        try:
            os.remove(path)
        except:
            pass

def mark_server_as_running(ip, central_server, server_folder, secret_key):
    inform_central_server(ip, secret_key, central_server)
    update_dropbox_state(ip, server_folder)

def mark_server_as_stopped(central_server, server_folder, secret_key):
    inform_central_server(None, secret_key, central_server)
    update_dropbox_state(None, server_folder)

def start_local_server(server_folder, jvm_flags=DEFAULT_JVM_OPTIONS, server_jar='minecraft_server.1.8.3.jar'):
    os.chdir(server_folder)
    command = 'java {:s} -jar {:s} '.format(jvm_flags, server_jar)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()


def find_first_jar(full_path):
    all_jars = [f for f in os.listdir(full_path) if isfile(os.path.join(full_path, f)) and f.lower().endswith(".jar")]
    return all_jars[0] if all_jars else None


def parse_input():
    parser = OptionParser()
    parser.add_option('-s', '--server', help='Set the remote/central server address (default: http://a.server.com:9000; default: None). If no remote server is supplied, only Dropbox backend will be used.', dest='server_address', type='string', default=None)
    parser.add_option('-k', '--secret-key', help='Set the secret key.', dest='secret_key', type='string')
    parser.add_option('-d', '--dropbox-path', help='Manually set the path to the Dropbox base folder (by default, it will be auto-detected)', dest='dropbox_path', type='string', default=None)
    parser.add_option('-n', '--name',help='Set the server name. This should match the shared folder in Dropbox. E.g., if server is named DEI, then a folder with that name (and with the jar in it) should be at the root of your Dropbox folder.',dest='server_name', type='string', default=None)
    parser.add_option('-p', '--path',help='Manually supply the full path to the server, bypassing dropbox altogether. Cannot use -p with -d and -n.',dest='server_path', type='string', default=None)
    parser.add_option('-j', '--jar',help='Server jar name. By default, the first jar found in the server folder will be used.',dest='jar_name', type='string', default=None)
    parser.add_option('-o', '--jvm-options',help='JVM options to use when starting the server (Default: "{}")'.format(DEFAULT_JVM_OPTIONS),dest='jvm_options', type='string', default=DEFAULT_JVM_OPTIONS)
    parser.add_option('-i', '--ip',help='Set the IP to report in case a server is started. By default, the public facing IP is auto-detected.',dest='ip', type='string', default=None)

    (options, args) = parser.parse_args()

    if options.server_address and not options.secret_key:
        parser.error('A secret key is required when using a central server! Use -k')
    if (options.dropbox_path or options.server_name) and options.server_path:
        parser.error('Cannot use -p with -d/-n.')
    if not options.server_name and not options.server_path:
        parser.error('A server folder must be somehow determined. Give the server name (same as in your Dropbox folder) with -n or explicitly set the folder path with -p.')

    if options.server_path:
        full_path = options.server_path
    else:
        if options.dropbox_path:
            dropbox_path = options.dropbox_path
        else:
            dropbox_path = autodetect_dropbox_home()
        full_path = os.path.join(dropbox_path, options.server_name)


    if options.jar_name:
        jar_name = options.jar_name
    else:
        jar_name = find_first_jar(full_path)
        if not jar_name:
            parser.error('No jar files were found in server folder ({}) and no jar name supplied!'.format(full_path))

    if options.ip:
        ip = options.ip
    else:
        ip = get_public_ip()


    return options.server_address, options.secret_key, full_path, jar_name, options.jvm_options, ip

def go():

        remote_server_address, secret_key, full_path_to_server, jar_name, jvm_options, ip = parse_input()
        status = is_someone_running_server(remote_server_address, full_path_to_server, secret_key)
        if status:
            print('Server is running at {:s}'.format(status))
        else:
            try:
                print('Server is not running. Starting...')
                mark_server_as_running(ip, remote_server_address, full_path_to_server, secret_key)
                start_local_server(full_path_to_server, jvm_options, jar_name)
                print('Server stopped. Updating server and Dropbox...')
                mark_server_as_stopped(remote_server_address, full_path_to_server, secret_key)
                print('Done!')
            except KeyboardInterrupt:
                print('Caught interrupt. Terminating and marking as stopped if we were the server.')
                status = is_someone_running_server(remote_server_address, full_path_to_server, secret_key)
                if status and status == ip:
                    print('We were the server! Marking as stopped')
                    mark_server_as_stopped(remote_server_address, full_path_to_server, secret_key)

def main():
    orig_dir = os.getcwd()
    go()
    os.chdir(orig_dir)

main()