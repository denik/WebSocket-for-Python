import gevent.pywsgi

from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware


# This should probably be built-in in gevent:
# environ['wsgi.socket'] is the connection that server puts here for applications like WebSocket
# environ['wsgi.socket.detach'] is a flag that application can set if it wants to use socket separately
# if it's True gevent server won't do anything about the connection anymore


class UpgradableWSGIHandler(gevent.pywsgi.WSGIHandler):

    def start_response_for_upgrade(self, status, headers, exc_info=None):
        write = self.start_response(status, headers, exc_info)
        if self.code == 101:
            # flushes headers now
            towrite = ['%s %s\r\n' % (self.request_version, self.status)]
            for header in headers:
                towrite.append('%s: %s\r\n' % header)
            towrite.append('\r\n')
            self.wfile.writelines(towrite)
            self.response_length += sum(len(x) for x in towrite)
        return write

    def run_application(self):
        self.environ['wsgi.socket'] = self.socket
        try:
            self.result = self.application(self.environ, self.start_response_for_upgrade)
            if not self.environ.get('wsgi.socket.detach'):
                self.process_result()
        finally:
            if self.environ.get('wsgi.socket.detach'):
                self.rfile.close() # makes sure we stop processing requests
                self.socket = None  # otherwise gevent server would close the connection


class WebSocketServer(gevent.pywsgi.WSGIServer):
    handler_class = UpgradableWSGIHandler

    def __init__(self, *args, **kwargs):
        gevent.pywsgi.WSGIServer.__init__(self, *args, **kwargs)
        protocols = kwargs.pop('websocket_protocols', [])
        extensions = kwargs.pop('websocket_extensions', [])
        self.application = WebSocketUpgradeMiddleware(self.application,
                            protocols=protocols,
                            extensions=extensions)

if __name__ == '__main__':
    def echo_handler(environ, websocket):
        try:
            while True:
                msg = websocket.receive(msg_obj=True)
                if msg is not None:
                    websocket.send(msg.data, msg.is_binary)
                else:
                    break
        finally:
            websocket.close()

    server = WebSocketServer(('127.0.0.1', 9000), echo_handler)
    server.serve_forever()
