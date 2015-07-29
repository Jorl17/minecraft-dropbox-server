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
import datetime
from optparse import OptionParser
import os
import subprocess
import urllib.request
import urllib.parse
import json
from os.path import isfile
import time
from threading import Thread

__author__ = 'jorl17'

CENTRAL_SERVER_ADDRESS='http://localhost:9000'
DEFAULT_JVM_OPTIONS='-Xmx3G -Xms2G'
DEFAULT_HEARTBEAT = 60
IP_REQUEST_TIMEOUT = 2

#------------------------------------------------------------------------------
# Threading stuff, to be able to run a thread which periodically updates the
# server status
#------------------------------------------------------------------------------
global_threads = []

def stop_hanging_threads():
    for thread in global_threads:
        thread.stop()

class PeriodicThread(Thread):
    def __init__(self, f, interval):
        self.stopped = False
        self.f = f
        self.interval = interval
        Thread.__init__(self)
    def run(self):
        global global_threads
        global_threads += [self]
        while not self.stopped:
            self.f()

            # Sleep in ticks of 1 so we can be aborted decently
            slept = 0
            while slept < self.interval:
                if self.stopped:
                    break
                remaining = self.interval - slept
                time_to_sleep = min(1, remaining)
                time.sleep(time_to_sleep)
                slept += time_to_sleep
        global_threads.remove(self)
    def stop(self):
        self.stopped = True


#------------------------------------------------------------------------------
# Dropbox folder auto-detection stuff.
# From http://stackoverflow.com/a/12118327
#------------------------------------------------------------------------------

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

#------------------------------------------------------------------------------
# Used later on to determine if a file should be considered outdated
#------------------------------------------------------------------------------
def get_seconds_since_last_file_change(file_path):
    file_change_time = os.path.getmtime(file_path)
    return (datetime.datetime.now() - datetime.datetime.fromtimestamp(file_change_time)).total_seconds()

#------------------------------------------------------------------------------
# To check that the server directory really exists
#------------------------------------------------------------------------------
def directory_exists(dir):
    return os.path.exists(dir) and os.path.isdir(dir)

#------------------------------------------------------------------------------
# To auto-determine the user's public IP. FIXME: We could add a time-out
#------------------------------------------------------------------------------
def get_public_ip():
    addresses = ['http://ipv4bot.whatismyipaddress.com', 'http://ipinfo.io/ip', 'http://www.trackip.net/ip']
    for address in addresses:
        try:
            f = urllib.request.urlopen(address, timeout=IP_REQUEST_TIMEOUT)
            return f.read().decode().strip()
        except:
            pass

    exit('Cannot reliably determine your IP. Please use the -i option.')

#------------------------------------------------------------------------------
# To automatically find the jar of the server
#------------------------------------------------------------------------------
def find_first_jar(full_path):
    all_jars = [f for f in os.listdir(full_path) if isfile(os.path.join(full_path, f)) and f.lower().endswith(".jar")]
    return all_jars[0] if all_jars else None

#------------------------------------------------------------------------------
# Ask the central server what's the current status of the Minecraft server.
# All we need to do is a GET, passing the key. The server can be HTTPS for more
# security.
#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
# Check Dropbox to see if the server is running. If there is no file, then
# the server is not running. If there is, we check if it is within the
# valid threshold (if it's older than that, we consider it to be outdated)
#
# Note that if valid_last_change_threshold aliases to False
# (e.g. 0, False, None), this check is not performed and files are considered
# regardless of their age.
#------------------------------------------------------------------------------
def check_dropbox_file(server_folder_path, valid_last_change_threshold):
    path = os.path.join(server_folder_path, 'mc_dropbox_server_status.txt')

    try:
        with open(path) as f:
            lines = f.readlines()
            if lines:
                ip = lines[0].strip()
                seconds_since_heartbeat = get_seconds_since_last_file_change(path)
                if not valid_last_change_threshold or seconds_since_heartbeat < valid_last_change_threshold:
                    return ip
                else:
                    print("Dropbox reported {} was running the server, but last heartbeat was {} seconds ago! Considering nobody is running server...".format(ip, seconds_since_heartbeat))
                    #update_dropbox_state(None, server_folder_path)
                    return False
            else:
                return False
    except:
        return False


#------------------------------------------------------------------------------
# Check if someone is running the server. In most cases, this acts as a direct
# wrapper to check_dropbox_file. However, if the central server is used, it
# checks both (currently we prefer Dropbox if there is a disagreement)
#------------------------------------------------------------------------------
def is_someone_running_server(central_server_address, server_folder_path, secret_key, time_threshold):
    status = check_central_server(secret_key, central_server_address)
    status_dropbox = check_dropbox_file(server_folder_path, time_threshold)
    if status != None:
        if status == status_dropbox:
            return status
        else:
            print('Dropbox and server disagree. Notifying server of status update (Dropbox is probably correct)')
            inform_central_server(status, secret_key, central_server_address)
    else:
        return status_dropbox

#------------------------------------------------------------------------------
# Inform the central server of a change in status. This equates to a POST
# on the address with a couple of pre-defined parameters (message and ip)
#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
# Update the status of the Dropbox file. We either log the IP or delete the
# file if the server is not running.
#------------------------------------------------------------------------------
def update_dropbox_state(ip, server_folder):
    path = os.path.join(server_folder, 'mc_dropbox_server_status.txt')

    if ip:
        with open(path, 'w') as f:
            f.write(ip + "\n")
            f.write(time.strftime('%Y/%m/%d %H:%M:%S'))
    else:
        try:
            os.remove(path)
        except:
            pass

#------------------------------------------------------------------------------
# Mark the server as running. This usually just results in updating the
# Dropbox state. However, if the central server is used, it is also notified.
#------------------------------------------------------------------------------
def mark_server_as_running(ip, central_server, server_folder, secret_key):
    inform_central_server(ip, secret_key, central_server)
    update_dropbox_state(ip, server_folder)

#------------------------------------------------------------------------------
# Mark the server as stopped. This usually just results in updating the
# Dropbox state. However, if the central server is used, it is also notified.
# It is equivalent to
# mark_server_as_running(None, central_server, server_folder, secret_key)
#------------------------------------------------------------------------------
def mark_server_as_stopped(central_server, server_folder, secret_key):
    mark_server_as_running(None, central_server, server_folder, secret_key)

#------------------------------------------------------------------------------
# Start the local server with the givem JVM arguments. Once it is started,
# keep updating the state of the Dropbox file (if a heartbeat time is given).
# If no heartbeat time is given, update it only when starting and when
# quitting.
#------------------------------------------------------------------------------
def start_local_server(server_folder, jvm_flags, server_jar, ip, remote_server_address, full_path_to_server, secret_key, heartbeat_time):
    os.chdir(server_folder)
    command = 'java {:s} -jar {:s} '.format(jvm_flags, server_jar)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    print('Server process started. Waiting for it to finish...')
    if heartbeat_time:
        updaterThread = PeriodicThread(lambda: mark_server_as_running(ip, remote_server_address, full_path_to_server, secret_key), heartbeat_time)
        updaterThread.start()
        process.wait()
        updaterThread.stop()
    else:
        mark_server_as_running(ip, remote_server_address, full_path_to_server, secret_key)
        process.wait()


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
    parser.add_option('-b', '--heartbeat',help="Set the heartbeat time (interval, in seconds, between successive updates of server status to Dropbox). If the Dropbox status hasn't been updated in 2*[heartbeat time], the server is considered to be stopped. Set to 0 if you want to disable heartbeats. By disabling them, the server status is updated only once and the modification time is ignored when querying for time. (Default: {})".format(DEFAULT_HEARTBEAT), dest='heartbeat_time', type='int', default=2*DEFAULT_HEARTBEAT)
    parser.add_option('-q', '--query-status',help='Just query the status of the server (is it running, and who is running it?)',dest='query_status', action='store_true', default=False)
    parser.add_option('-c', '--clear',help='DEPRECATED: Should not be needed if appropriate heartbeat values are chosen. Clear the saved state of the current server session. USE WITH CARE. This notifies everyone that the server isn\'t actually running. If it _is_ running, it is a very bad idea to do this. Use only after a system crash or similar accident.',dest='clear', action='store_true', default=False)

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

    if options.clear and options.query_status:
        parser.error("Can't use both the -c and -q options. Choose one of them!")

    if not directory_exists(full_path):
        parser.error("Directory {} does not exist.".format(full_path))


    if options.heartbeat_time < 0:
        parser.error('Invalid heartbeat time ({}). Please supply a positive integer!'.format(options.heartbeat_time))
    elif options.heartbeat_time == 0:
        print('Disabling heartbeat...')

    if options.clear:
        print('ARE YOU SURE THAT THE SERVER REALLY IS STOPPED? (y/n) ')
        choice = input().lower()
        if choice in ['y', 'yes', 'ye', 's']:
            mark_server_as_stopped(options.server_address, full_path, options.secret_key, 2*options.heartbeat_time)
            exit("Done. All status cleared. Don't come complaining if you mess up someone's game!")
        else:
            exit('Status clear aborted.')
    elif options.query_status:
        status = is_someone_running_server(options.server_address, full_path, options.secret_key, 2*options.heartbeat_time)
        if status:
            exit('Server is running at {:s}'.format(status))
        else:
            exit('Server is not running.')

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


    return options.server_address, options.secret_key, full_path, jar_name, options.jvm_options, ip, options.heartbeat_time

def go():
        remote_server_address, secret_key, full_path_to_server, jar_name, jvm_options, ip, heartbeat_time = parse_input()
        status = is_someone_running_server(remote_server_address, full_path_to_server, secret_key, 2*heartbeat_time)
        if status:
            print('Server is running at {:s}'.format(status))
        else:
            try:
                print('Server is not running. Starting...')
                start_local_server(full_path_to_server, jvm_options, jar_name, ip, remote_server_address, full_path_to_server, secret_key, heartbeat_time)
                print('Server stopped. Updating server and Dropbox...')
                mark_server_as_stopped(remote_server_address, full_path_to_server, secret_key)
                print('Done!')
            except KeyboardInterrupt:
                print('Caught interrupt. Terminating and marking as stopped if we were the server.')
                # Pass no heartbeat time because we don't care about that now! We just want to clear the state if we
                # were the last ones reported to be hosting the server
                status = is_someone_running_server(remote_server_address, full_path_to_server, secret_key, None)
                if status and status == ip:
                    print('We were the server! Marking as stopped')
                    mark_server_as_stopped(remote_server_address, full_path_to_server, secret_key)

def main():
    orig_dir = os.getcwd()
    go()
    os.chdir(orig_dir)

main()
stop_hanging_threads()