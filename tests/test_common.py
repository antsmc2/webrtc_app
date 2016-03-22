__author__ = 'anthony'

import websocket
import os, sys, time
from tornado import template
from tornado import testing, httpserver, gen, websocket, httpclient
import json

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.dirname(SCRIPT_DIR))
sys.path.append(SCRIPT_DIR)
sys.path.append(PROJECT_DIR)
import webrtc_server
from urllib import urlencode, quote
from collections import OrderedDict

MY_CALLER_ID = 'ME'
TEST_PEER_ID1 = 'PEER1'
TEST_PEER_ID2 = 'PEER2'
TEST_PEER_ID3 = 'PEER3'


class BasicTestCase(testing.AsyncHTTPTestCase, testing.LogTrapTestCase):

    def setUp(self):
        super(BasicTestCase, self).setUp()
        # for peer in webrtc_server.peers.values():
        #     peer.close()
        # for client in webrtc_server.clients.values():
        #     client.close()
        webrtc_server.peers = {}
        webrtc_server.clients = {}

    def make_url(self, path, protocol='ws', **kwargs):
        url = '%s://127.0.0.1:%s%s' % (protocol, self.get_http_port(), path)
        query_string =  urlencode(OrderedDict(kwargs))
        if kwargs:
            url = '%s?%s' % (url, query_string)
        return url

    def make_relative_url(self, path, **kwargs):
        query_string =  urlencode(OrderedDict(kwargs))
        return '%s?%s' % (path, query_string)

    def _mk_ws_connection(self, path, **kwargs):
        return websocket.websocket_connect(self.make_url(path, protocol='ws', **kwargs))

    def get_app(self):
        return webrtc_server.app


if __name__ == "__main__":
    testing.unittest.main(verbosity=1)