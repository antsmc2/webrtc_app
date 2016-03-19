#!/usr/bin/env python
__author__ = 'anthony'
from tornado import websocket, web, ioloop
import os, sys
import json
import logging
from daemon import Daemon
from urllib import urlencode, quote
from collections import OrderedDict, defaultdict
import threading


APP_PORT = 8004
WS_PROTOCOL = 'wss'
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, 'templates')
STATIC_DIR = os.path.join(SCRIPT_DIR, 'static')
LOG_FILE = os.path.join(SCRIPT_DIR, 'webrtc.log')
PID_FILE = os.path.join(SCRIPT_DIR, 'webrtc.pid')


SERVER_NOTICE_TYPE = 'SERVER_NOTICE'
PEER_UNAVAILABLE = 'PEER-UNAVAILABLE'
PEER_BUSY = 'PEER-BUSY'
PEER_NOT_FOUND = 'PEER-NOT-FOUND'
BAD_REQUEST = 'BAD-REQUEST'
BAD_REQUEST_STATUS = 400

sys.path.append(SCRIPT_DIR)
handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger("tornado.application")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

#ice servers
iceServers = [
  {
    'urls': 'stun:stun.l.google.com:19302',
  },
  {
	'urls':'stun:202.153.34.169:8002?transport=tcp'
  },
  {
	'urls':'stun:global.stun.twilio.com:3478?transport=udp'
  },
  {
    'urls' : 'turn:202.153.34.169:8002?transport=tcp',
    'credential': 'dhanush123',
    'username': 'dhanush'
  },
  {
    'urls': 'turn:global.turn.twilio.com:3478?transport=udp',
    'credential': 'lN48+q3dzIvVFTIojLICy53W0lo9vujIoBcLExzS6pI=',
    'username': '70cfe39ec1b0922d41f49812f110383f31c7d0e861b27e40d58e5a1b453f4c01'
  }
  ];

#in the future these values would be put in cache maybe
clients = defaultdict(set)

def get_notice_msg(msg, msg_type=SERVER_NOTICE_TYPE):
    data = {
     'msg_type' : msg_type,
     'message': msg
     }
    return json.dumps(data)

def make_url(host, path, protocol=WS_PROTOCOL, **kwargs):
    base_url = '%s://%s%s' % (protocol, host, path)
    query_string =  urlencode(OrderedDict(kwargs))
    return '%s?%s' % (base_url, query_string)

def make_relative_url(path, **kwargs):
    query_string =  urlencode(OrderedDict(kwargs))
    return '%s?%s' % (path, query_string)

class ICEServerHandler(web.RequestHandler):

    def post(self, *args, **kwargs):
        self.add_header('Content-Type', 'application/json')
        self.write(json.dumps(iceServers))


class BaseTemplateHandler(web.RequestHandler):
    ws_url_name = None
    title = None

    def process_request(self, *args, **kwargs):
        peer_id = self.get_query_argument('peer_id', None) or self.get_argument('peer_id', None)
        id = self.get_query_argument('id', None) or self.get_argument('id', None)
        ws_uri = make_relative_url(app.reverse_url(self.ws_url_name), id=id, peer_id=peer_id)
        ice_url = make_relative_url(app.reverse_url('ice_url'))
        logger.debug('using ice servers: %s' % ice_url)
        self.render(os.path.join(TEMPLATE_DIR, "base.html"),
                    ws_uri=ws_uri, my_id=id, peer_id=peer_id, title=self.title, ice_url=ice_url)

    def get(self, *args, **kwargs):
        self.process_request(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.process_request(*args, **kwargs)


class CallTemplateHandler(BaseTemplateHandler):
    ws_url_name = 'caller_ws'
    title = 'Caller'

class RecieveTemplateHandler(BaseTemplateHandler):
    ws_url_name = 'reciever_ws'
    title = 'Receiver'

class BaseHandler(websocket.WebSocketHandler):
    id = None
    closed = False
    def check_origin(self, origin):
        #to do, restrict cross domain login
        return True

    def on_connection_close(self):
        logger.info('lost connection "%s"' % self.id)
        self.closed = True
        self.clean()
        super(BaseHandler, self).on_connection_close()

    def clean(self):
        pass

class WebRTCHandler(BaseHandler):
    peer_id = None
    
    def check_origin(self, origin):
        return True

    def open(self):
        logger.debug('new connection ')
        self.id = self.get_query_argument('id', None)
        self.peer_id = self.get_query_argument('peer_id', None)
        logger.info('new id: %s, peer: %s' % (self.id, self.peer_id))
        if self.id and self.id is not self.peer_id:
            lock = threading.Lock()
            with lock:
                clients[self.id].add(self)
        else:
            self.close(BAD_REQUEST_STATUS, BAD_REQUEST)
        logger.debug('clients: %s, closed: %s' % (len(clients), self.closed))
    
    def on_message(self, message):
        logger.debug('from: %s, to: %s, msg: %s' % (self.id, self.peer_id, message))
        sent = False
        if clients.has_key(self.peer_id):
            peer_clients = clients[self.peer_id]
            for client in peer_clients:
                if client.peer_id == self.id:   ###send message only to relevant peer
                    try:
                        client.write_message(message)
                        sent = True
                    except Exception, ex:
                        logger.error('error sending from: %s, To: %s' % (self.id, self.peer_id))
        if not sent:
            my_clients = clients[self.id]
            message = get_notice_msg(PEER_UNAVAILABLE)
            for client in my_clients:
                if client.id == self.peer_id:       ##only notify on relevant conversation
                    try:
                        client.write_message(message) #just try to notify if you can
                    except:
                        pass

    def clean(self):
        logger.debug('cleaning.. %s' % self.id)
        lock = threading.Lock()
        with lock:
            clients[self.id].remove(self)
            if not clients[self.id]:
                clients.pop(self.id)
        logger.debug('closed: %s. total clients: %s' % (self.id, len(clients)))

class CallHandler(WebRTCHandler):
    pass
            
class RecieveHandler(WebRTCHandler):
    pass

app = web.Application([
    web.URLSpec(r'/wscall', CallHandler, name='caller_ws'),
    web.URLSpec(r'/wsrecieve', RecieveHandler, name='reciever_ws'),
    (r'/static/(.*)', web.StaticFileHandler, {'path': STATIC_DIR}),
    web.URLSpec(r'/call', CallTemplateHandler, name='caller_page'),
    web.URLSpec(r'/recieve', RecieveTemplateHandler, name='reciever_page'),
    web.URLSpec(r'/ice_servers', ICEServerHandler, name='ice_url'),
])


class MyDaemon(Daemon):
    def run(self):
        app.listen(APP_PORT)
        ioloop.IOLoop.instance().start()

def get_daemon():
    return MyDaemon(PID_FILE, stdout=LOG_FILE, stderr=LOG_FILE)

if __name__ == '__main__':
    daemon = get_daemon()
    if len(sys.argv) >= 2:
        if len(sys.argv) == 3 and sys.argv[2].isdigit():
            APP_PORT = int(sys.argv[2])
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print 'unknown command'
            sys.exit(2)
        sys.exit(0)
    else:
        print 'usage: %s start|stop|restart port' % sys.argv[0]
        sys.exit(2)

