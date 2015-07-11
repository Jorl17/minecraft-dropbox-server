import cgi
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import time
import json

HOST_NAME = "0.0.0.0"
HOST_PORT = 9000


class mc_dropbox_state_server(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.state = None
        super().__init__(request, client_address, server)

    def save_state(self):
        if self.state:
            with open('mc_dropbox_server_status_central.txt', 'w') as f:
                f.write(self.state)
        else:
            try:
                os.remove('mc_dropbox_server_status_central.txt')
            except:
                pass

    def get_state(self):
        if not self.state:
            try:
                with open('mc_dropbox_server_status_central.txt') as f:
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
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(self.state_to_json(), "utf-8"))

    def get_post_variables(self):
        ctype, pdict = cgi.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            return cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            return cgi.urllib.parse.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            return {}

    def do_POST(self):
        variables = self.get_post_variables()
        message = variables.get(b'message')[0].decode('utf-8')
        if not message or message not in ('stopped', 'started'):
            print(message)
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


def main():
    myServer = HTTPServer((HOST_NAME, HOST_PORT), mc_dropbox_state_server)
    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, HOST_PORT))
    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        pass

    myServer.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, HOST_PORT))

main()