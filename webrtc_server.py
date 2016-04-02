#!/usr/bin/env python
__author__ = 'anthony'
from tornado import websocket, web, ioloop
import os, sys
import json
import logging
from urllib import urlencode, quote
from collections import OrderedDict, defaultdict
import uuid
import threading


APP_PORT = 8004
WS_PROTOCOL = 'ws'
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

ICE_URL = r'/ice_servers'
ICE_ACCESS_TOKEN = '7af52166dadf6e1e3d46100fe272f85e'
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


def has_ice_pass(request_handler):
    access_token = request_handler.request.body
    logger.debug('got token %s' % access_token)
    return access_token == ICE_ACCESS_TOKEN

def get_ice_pass():
    return ICE_ACCESS_TOKEN

#in the future these values would be put in cache maybe
clients = {}

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
        if has_ice_pass(self):
            self.add_header('Content-Type', 'application/json')
            self.write(json.dumps(iceServers))

class ClientConnectionsHandler(web.RequestHandler):

    def get(self, *args, **kwargs):
        id = self.get_query_argument('id', None)
        my_clients = clients.get(id, [])
        self.add_header('Content-Type', 'application/json')
        self.write(json.dumps([{'peer': client.peer_id, 'session': str(client.session_id)} for client in  my_clients]))


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
                    ws_uri=ws_uri, my_id=id, peer_id=peer_id, title=self.title,
                    ice_url=ice_url, ice_pass=get_ice_pass())

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

    def on_close(self):
        logger.info('lost connection "%s"' % self.id)
        self.closed = True
        self.clean()
        super(BaseHandler, self).on_connection_close()

    # def on_close(self):

    def clean(self):
        pass

class WebRTCHandler(BaseHandler):
    session_id = None
    peer_id = None
    
    def check_origin(self, origin):
        return True

    def open(self):
        self.session_id = uuid.uuid4()
        logger.debug('new connection %s' % self.session_id)
        self.id = self.get_query_argument('id', None)
        self.peer_id = self.get_query_argument('peer_id', None)
        logger.info('new id: %s, peer: %s, session_id: %s' % (self.id, self.peer_id, self.session_id))
        if self.id and self.id is not self.peer_id:
            if clients.has_key(self.id) is False:
                clients[self.id] = set()  #removing thread lock since impact is only with present peer
                # lock = threading.Lock()
                # with lock:
                #     clients[self.id] = set()
            clients[self.id].add(self)
        else:
            self.close(BAD_REQUEST_STATUS, BAD_REQUEST)
        logger.debug('clients: %s, closed: %s' % (len(clients), self.closed))
    
    def on_message(self, message):
        logger.debug('from: %s<%s>, to: %s, msg: %s' % (self.id, self.session_id, self.peer_id, message))
        sent = False
        my_clients = clients[self.id]
        if clients.has_key(self.peer_id):
            peer_clients = clients[self.peer_id]
            logger.debug('sending to %s clients' % len(peer_clients))
            for client in peer_clients:
                logger.debug('attempting send to: %s, client peer is: %s' % (client.id, client.peer_id))
                ## message only relevant peer or peer client with not having any conversation
                if (client.peer_id == self.id) or (client.peer_id is None):
                    try:
                        client.write_message(message)
                        logger.debug('sent to %s<%s>' % (client.id, client.session_id))
                        sent = True
                    except Exception, ex:
                        logger.error('error sending from: %s, To: %s' % (self.id, self.peer_id))
        for client in my_clients:
            if (client is not self) and (client.peer_id == self.peer_id):  ##notify your other clients of your msg
                try:
                    client.write_message(message)
                    logger.debug('sent to other device %s. session_id: %s' % (client.id, client.session_id))
                except Exception, ex:
                    logger.error('error sending to other device: %s, To: %s' % (self.id, self.peer_id))
        if not sent:
            logger.debug('message to: %s not sent' % self.peer_id)
            message = get_notice_msg(PEER_UNAVAILABLE)
            logger.debug('sending to: %s msg: %s' % (self.id, message))
            for client in my_clients:
                if client.peer_id == self.peer_id:       ##only notify on relevant conversation
                    try:
                        client.write_message(message) #just try to notify if you can
                        logger.debug('sent to %s<%s>' % (client.id, client.session_id))
                    except:
                        pass
        else:
            logger.debug('message sent to: %s' % self.peer_id)

    def clean(self):
        logger.debug('cleaning.. %s' % self.id)
        clients[self.id].remove(self)
        if not clients[self.id]:
            clients.pop(self.id)   #removing the thread lock, since impact is only with present user
            # lock = threading.Lock()
            # with lock:
            #     clients.pop(self.id)
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
    web.URLSpec(ICE_URL, ICEServerHandler, name='ice_url'),
    web.URLSpec(r'/connections', ClientConnectionsHandler, name='clients_url'),
])

if __name__ == '__main__':
    app.listen(APP_PORT)
    ioloop.IOLoop.instance().start()
