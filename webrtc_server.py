#!/usr/bin/env python
__author__ = 'anthony'
from tornado import websocket, web, ioloop
import os, sys
import json
import logging
from daemon import Daemon
from urllib import urlencode, quote
from collections import OrderedDict

APP_PORT = 8004
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, 'templates')
STATIC_DIR = os.path.join(SCRIPT_DIR, 'static')
LOG_FILE = os.path.join(SCRIPT_DIR, 'webrtc.log')
PID_FILE = os.path.join(SCRIPT_DIR, 'webrtc.pid')

CALL_INIT = 'INI'
CALL_ONGOING = 'IN_PROG'
CALL_DROPPED = 'DROPPED'
LOGIN_TYPE = 'LOGIN'
CALL_TYPE = 'CALL'
PEER_UNAVAILABLE = 'Peer Unavailable'
PEER_BUSY = 'Peer Busy'
PEER_NOT_FOUND = 'Recepient not found'

sys.path.append(SCRIPT_DIR)
handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger("WebRTCServer")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

#in the future these values would be put in cache maybe
peers = {}
clients = {}

def get_notice_msg(caller_id, msg_type, status):
    data = {
     'caller' : caller_id,
     'msg_type' : msg_type,
     'status': status
     }
    return json.dumps(data)

def make_url(host, path, protocol='ws', **kwargs):
    base_url = '%s://%s%s' % (protocol, host, path)
    query_string =  urlencode(OrderedDict(kwargs))
    return '%s?%s' % (base_url, query_string)

class CallTemplateHandler(web.RequestHandler):
    def get(self):
        peer_id = self.get_query_argument('peer_id', None)
        id = self.get_query_argument('id', None)
        if clients.has_key(peer_id) is False:
            logger.error('peer unavailable: %s' % peer_id)
            self.set_status(404, reason=PEER_UNAVAILABLE)
            return self.write(PEER_UNAVAILABLE)
        logger.debug('client call status %s: %s' % (peer_id, clients[peer_id].call_status))
        if clients[peer_id].call_status == LoginHandler.BUSY:
            self.set_status(423, reason=PEER_BUSY)
            return self.write(PEER_BUSY)
        caller_ws_uri = make_url(self.request.host, app.reverse_url('caller_ws'), id=id, peer_id=peer_id)
        self.render(os.path.join(TEMPLATE_DIR, "base.html"),
                    caller_ws_uri=caller_ws_uri, my_id=id, peer_id=peer_id, title='Caller')

class RecieveTemplateHandler(web.RequestHandler):
    def get(self):
        peer_id = self.get_query_argument('peer_id', None)
        id = self.get_query_argument('id', None)
        recieve_ws_uri = make_url(self.request.host, app.reverse_url('reciever_ws'), id=id, peer_id=peer_id)
        self.render(os.path.join(TEMPLATE_DIR, "base.html"), recieve_ws_uri=recieve_ws_uri,
                    my_id=id, peer_id=peer_id, title='Receiver')

class BaseHandler(websocket.WebSocketHandler):
    id = None
    closed = False
    def check_origin(self, origin):
        #to do, restrict cross domain login
        return True

    def on_connection_close(self):
        logger.info('lost remote "%s"' % self.id)
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
            if peers.has_key(self.id) is False:
                peers[self.id] = self
            else:
                self.close(code=423, reason=PEER_BUSY)
        else:
            self.close(code=404, reason=PEER_NOT_FOUND)
        logger.debug('peers: %s, closed: %s' % (len(peers), self.closed))
    
    def on_message(self, message):
        logger.debug('from: %s, to: %s, msg: %s' % (self.id, self.peer_id, message))
        if peers.has_key(self.peer_id):
            peers[self.peer_id].write_message(message)

    def clean(self):
        logger.debug('cleaning.. %s' % self.id)
        if peers.has_key(self.id):
            peers.pop(self.id)
        if peers.has_key(self.peer_id) and peers[self.peer_id].closed is False:
            peer = peers[self.peer_id]
            logger.info('closing peer %s' % self.peer_id)
            peer.clean()
            peer.close(code=404, reason=PEER_UNAVAILABLE)
        if clients.has_key(self.peer_id) and clients[self.peer_id].closed is False:
            clients[self.peer_id].write_message(get_notice_msg(self.id, CALL_TYPE, CALL_DROPPED))
        logger.debug('closed: %s. total peers: %s' % (self.id, len(peers)))

class CallHandler(WebRTCHandler):
    
    def open(self):
        super(CallHandler, self).open()
        if self.closed is False:
            if clients.has_key(self.peer_id) is False:
                return self.close(code=404, reason=PEER_UNAVAILABLE)
            clients[self.peer_id].write_message(get_notice_msg(self.id, CALL_TYPE, CALL_INIT))
            
class RecieveHandler(WebRTCHandler):
    pass

class LoginHandler(BaseHandler):
    BUSY = 0
    AVAILABLE = 1
    call_status = AVAILABLE

    def open(self):
        self.id = self.get_query_argument('id', None)
        logger.info('login request for: %s' % self.id)
        if self.id and clients.has_key(id) is False:
            clients[self.id] = self
            self.call_status = LoginHandler.AVAILABLE

    def write_message(self, message, binary=False):
        msg = json.loads(message)
        if msg.has_key('msg_type') and msg['msg_type'] == CALL_TYPE and msg['status'] == CALL_INIT:
            self.call_status = LoginHandler.BUSY
        if msg.has_key('msg_type') and msg['msg_type'] == CALL_TYPE and msg['status'] == CALL_DROPPED:
            self.call_status = LoginHandler.AVAILABLE
        return super(LoginHandler, self).write_message(message, binary)

    def on_close(self):
        if clients.has_key(self.id):
            clients.pop(self.id)
        logger.info('logout: %s' % self.id)

app = web.Application([
    web.URLSpec(r'/wscall', CallHandler, name='caller_ws'),
    web.URLSpec(r'/wsrecieve', RecieveHandler, name='reciever_ws'),
    web.URLSpec(r'/wslogin', LoginHandler, name='login_ws'),
    (r'/static/(.*)', web.StaticFileHandler, {'path': STATIC_DIR}),
    web.URLSpec(r'/call', CallTemplateHandler, name='caller_page'),
    web.URLSpec(r'/recieve', RecieveTemplateHandler, name='reciever_page'),
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

