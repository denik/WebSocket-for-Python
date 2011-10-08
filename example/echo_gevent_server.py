# -*- coding: utf-8 -*-
from ws4py.server.geventserver import WebSocketServer
from gevent import spawn
from socket import error
from collections import deque


HTML = """<html>
    <head>
      <script type='application/javascript' src='https://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js'> </script>
      <script type='application/javascript'>

        try { WebSocket } catch(err) { WebSocket = MozWebSocket; }

        $(document).ready(function() {
          var ws = new WebSocket('ws://localhost:9000/ws');
          $(window).unload(function() {
             ws.close();
          });
          ws.onmessage = function (evt) {
             $('#chat').val($('#chat').val() + evt.data + '\\n');
          };
          ws.onopen = function() {
             ws.send("%(username)s entered the room");
          };
          $('#chatform').submit(function() {
             ws.send('%(username)s: ' + $('#message').val());
             $('#message').val("");
             return false;
          });
        });
      </script>
    </head>
    <body>
    <form action='/echo' id='chatform' method='get'>
      <textarea id='chat' cols='35' rows='10'></textarea>
      <br />
      <label for='message'>%(username)s: </label><input type='text' id='message' />
      <input type='submit' value='Send' />
      </form>
    </body>
    </html>
    """


sockets = set()
messagelog = deque(maxlen=20)


def _send(socket, message):
    try:
        socket.send(message)
    except error:
        pass


def broadcast(message):
    messagelog.append(message)
    for socket in sockets:
        spawn(_send, socket, message)


def application(environ, start_response):
    websocket = environ.get('wsgi.websocket')
    if websocket is None:
        start_response('200 OK', [])
        return [HTML % {'username': environ['REMOTE_ADDR']}]
    else:
        for msg in messagelog:
            websocket.send(msg)
        sockets.add(websocket)
        try:
            while True:
                message = websocket.receive()
                if not message:
                    broadcast('%s left the room' % environ['REMOTE_ADDR'])
                    break
                broadcast(message)
        finally:
            sockets.discard(websocket)


if __name__ == '__main__':
    WebSocketServer(('0.0.0.0', 9000), application).serve_forever()
