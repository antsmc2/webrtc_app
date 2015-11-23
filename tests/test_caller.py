__author__ = 'anthony'
from test_common import *

class TestCallerApp(BasicTestCase):

    def test_caller_gets_http_404_when_client_websocket_is_offline(self):
        response = self.fetch(webrtc_server.app.reverse_url('caller_page'))
        self.assertEqual(response.code, 404)

    def test_caller_gets_peer_unavailabe_message_when_client_websocket_is_offline(self):
        response = self.fetch(webrtc_server.app.reverse_url('caller_page'))
        self.assertEqual(response.body, webrtc_server.PEER_UNAVAILABLE)

    @testing.gen_test
    def test_caller_is_accessible_when_client_websocket_is_online(self):
        code = -1
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'),
                                                id=TEST_PEER_ID1)
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        try:
            response = yield self.http_client.fetch(caller_page_uri)
            code = response.code
        except httpclient.HTTPError, ex:
            code = ex.code
        self.assertEqual(code, 200)


    @testing.gen_test
    def test_caller_page_uses_CallHandler_for_signaling(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'),
                                                id=TEST_PEER_ID1)
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        try:
            response = yield self.http_client.fetch(caller_page_uri)
            caller_ws_uri = self.make_url(webrtc_server.app.reverse_url('caller_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
            self.assertIn(caller_ws_uri, response.body)
            code = response.code
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_caller_gets_peer_busy_page_when_recepient_peer_is_busy_with_a_caller(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket = self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket = self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),#call same peer again
                                        protocol='http', id=TEST_PEER_ID2, peer_id=TEST_PEER_ID1)
        with self.assertRaises(httpclient.HTTPError) as context:
            yield self.http_client.fetch(caller_page_uri)
        self.assertTrue(context.exception.message.endswith(webrtc_server.PEER_BUSY))

    @testing.gen_test
    def test_caller_websocket_triggers_correct_client_websocket_with_reciepient_peer_details(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket = self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        msg = yield client_socket.read_message()
        self.assertEqual(msg, webrtc_server.get_notice_msg(MY_CALLER_ID,
                                                webrtc_server.CALL_TYPE, webrtc_server.CALL_INIT))

    @testing.gen_test
    def test_subsequent_messages_from_caller_websocket_goes_to_reciepient_peer_websocket(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)

    @testing.gen_test
    def test_caller_info_is_removed_from_inmemory_when_caller_websocket_disconnects(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        yield client_socket.read_message() #call ini message
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        caller_socket.close()
        yield reciever_socket.read_message()
        yield client_socket.read_message() #call dropped msg
        self.assertTrue(MY_CALLER_ID not in webrtc_server.peers.keys())

    @testing.gen_test
    def test_reciepient_websocket_is_closed_when_caller_websocket_disconnects(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        yield client_socket.read_message() #call init
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        val = yield reciever_socket.read_message()
        caller_socket.close()
        yield client_socket.read_message() #call dropped msg
        self.assertTrue(TEST_PEER_ID1 not in webrtc_server.peers.keys())

    @testing.gen_test
    def test_recipent_peer_client_websocket_gets_call_dropped_msg_when_caller_websocket_disconnects(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        val = yield client_socket.read_message() #login message
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        val = yield reciever_socket.read_message()
        caller_socket.close()
        msg = yield client_socket.read_message()
        self.assertEqual(msg, webrtc_server.get_notice_msg(MY_CALLER_ID,
                                                webrtc_server.CALL_TYPE, webrtc_server.CALL_DROPPED))