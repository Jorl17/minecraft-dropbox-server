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
import cgi
from optparse import OptionParser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import time
import json

HOST_NAME = "0.0.0.0"
HOST_PORT = 9000
DEFAULT_FILE_NAME = 'mc_dropbox_server_status_central.txt'

# This is fugly
global_key = None
global_filepath = None
def get_key():
    return global_key

def get_filepath():
    return global_filepath

class mc_dropbox_state_server(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.state = None
        super().__init__(request, client_address, server)
        key = get_key()

    def save_state(self):
        if self.state:
            with open(get_filepath(), 'w') as f:
                f.write(self.state)
        else:
            try:
                os.remove(get_filepath())
            except:
                pass

    def get_state(self):
        if not self.state:
            try:
                with open(get_filepath()) as f:
                    lines = f.readlines()
                    if lines:
                        ip = lines[0].strip()
                        self.state = ip
                    else:
                        self.state = False
            except:
                self.state = False
        return self.state

    def state_to_json(self):
        state = self.get_state()
        if not state:
            d =  {'online': False}
        else:
            d = {'online': True, 'ip': state }

        return json.dumps(d)


    def do_GET(self):
        variables = self.get_passed_variables()
        key = variables.get(b'key')[0].decode('utf-8')
        if not key or key != get_key():
            self.send_response(503)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes('Invalid key.', "utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(self.state_to_json(), "utf-8"))

    # This is soooo ugly.
    def get_passed_variables(self):
        try:
            ctype, pdict = cgi.parse_header(self.headers['content-type'])
        except:
            try:
                d = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                d_out = {}
                for key,val in d.items():
                    d_out[key.encode('utf-8')] = [i.encode('utf-8') for i in val]
                return d_out
            except:
                return {}
        if ctype == 'multipart/form-data':
            return cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            return cgi.urllib.parse.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            return {}

    def do_POST(self):
        variables = self.get_passed_variables()
        message = variables.get(b'message')[0].decode('utf-8')
        key = variables.get(b'key')[0].decode('utf-8')
        if not key or key != get_key():
            self.send_response(503)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes('Invalid key.', "utf-8"))
        elif not message or message not in ('stopped', 'started'):
            self.send_response(503)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes('No message supplied.', "utf-8"))
        else:
            if message == 'stopped':
                self.state = None
                self.save_state()
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
            else:
                state = variables.get(b'ip')[0].decode('utf-8')
                if not state:
                    self.send_response(503)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(bytes('No IP supplied!', "utf-8"))
                else:
                    if self.state:
                        self.send_response(503)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()
                        self.wfile.write(bytes('Server already running at ' + self.state + '!', "utf-8"))
                    else:
                        self.state = state
                        self.save_state()
                        self.send_response(200)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()


def parse_input():
    parser = OptionParser()
    parser.add_option('-p', '--port', help='Set the listening port (default: 9000)', dest='port', type='int', default=9000)
    parser.add_option('-f', '--server-file', help='Set the path (including name) to the status server file (default: {})'.format(DEFAULT_FILE_NAME), dest='server_file', type='string', default=DEFAULT_FILE_NAME)
    parser.add_option('-k', '--secret-key', help='Set the secret key.', dest='secret_key', type='string')
    (options, args) = parser.parse_args()

    if not options.secret_key:
        parser.error('A secret key is required! Use -k')

    return options.port, options.server_file, options.secret_key

def main():
    global global_key, global_filepath
    port, global_filepath, global_key = parse_input()

    myServer = HTTPServer((HOST_NAME, port), mc_dropbox_state_server)

    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, HOST_PORT))
    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        pass

    myServer.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, HOST_PORT))

main()