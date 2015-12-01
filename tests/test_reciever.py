__author__ = 'anthony'

from test_common import *


class TestRecieverApp(BasicTestCase):

    @testing.gen_test
    def test_recieve_page_uses_RecieveHandler_for_signaling(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'),
                                                id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        reciever_page_uri = self.make_url(webrtc_server.app.reverse_url('reciever_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        try:
            response = yield self.http_client.fetch(reciever_page_uri)
            reciever_ws_uri = self.make_url(webrtc_server.app.reverse_url('reciever_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
            self.assertIn(reciever_ws_uri, response.body)
            code = response.code
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_recieve_websocket_message_is_sent_to_the_correct_caller(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID2)
        caller_socket1 =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        caller_socket2 =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=TEST_PEER_ID3, peer_id=TEST_PEER_ID2) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        reciever_socket1 =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID2, peer_id=TEST_PEER_ID3) #pickup call
        test_msg1 = 'hey man1'
        test_msg2 = 'hey man2'
        reciever_socket.write_message(test_msg1)
        val1 = yield caller_socket1.read_message()
        self.assertEqual(val1, test_msg1)
        reciever_socket1.write_message(test_msg2)
        val2 = yield caller_socket2.read_message()
        self.assertEqual(val2, test_msg2)

    @testing.gen_test
    def test_get_or_post_to_recieve_page_url_gives_same_reciever_page(self):
        import urllib
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'),
                                                id=TEST_PEER_ID1)
        reciever_page_uri = self.make_url(webrtc_server.app.reverse_url('reciever_page'),
                                        protocol='http', id=TEST_PEER_ID1, peer_id=MY_CALLER_ID)
        reciever_page_uri_no_query_string = self.make_url(webrtc_server.app.reverse_url('reciever_page'),
                                        protocol='http')
        data = { 'id': TEST_PEER_ID1, 'peer_id': MY_CALLER_ID } #A dictionary of your post data
        request_body = urllib.urlencode(data)
        self.assertEqual(reciever_page_uri, '%s?%s'%(reciever_page_uri_no_query_string, request_body))
        try:
            response1 = yield self.http_client.fetch(reciever_page_uri, method='GET')
            response2 = yield self.http_client.fetch(reciever_page_uri_no_query_string,
                                                     method='POST', body=request_body)
            self.assertEqual(response1.body, response2.body)
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_recepient_removed_from_inmemory_when_peer_disconnects(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        yield client_socket.read_message() #call ini message
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        val = yield reciever_socket.read_message()
        caller_socket.close()
        val = yield client_socket.read_message()
        self.assertTrue(TEST_PEER_ID1 not in webrtc_server.peers.keys())

    @testing.gen_test
    def test_recepient_removed_from_inmemory_when_recepient_disconnects(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        yield client_socket.read_message() #call ini message
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        yield reciever_socket.read_message()
        reciever_socket.close()   #closing reciever should trigger close caller
        val = yield client_socket.read_message() #this leads to call dropped message
        self.assertTrue(TEST_PEER_ID1 not in webrtc_server.peers.keys())

    @testing.gen_test
    def test_recepient_disconnection_triggers_caller_disconnection(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        yield client_socket.read_message() #call ini message
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        caller_socket.write_message(test_msg)
        yield reciever_socket.read_message()
        reciever_socket.close()   #closing reciever should trigger close caller
        msg = yield client_socket.read_message() #this leads to call dropped message
        self.assertEqual(msg, webrtc_server.get_notice_msg(MY_CALLER_ID,
                                webrtc_server.CALL_TYPE, webrtc_server.CALL_DROPPED)) #assert call dropped

    @testing.gen_test
    def test_when_clients_comes_online_clientws_is_added_to_memory(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        self.assertTrue(TEST_PEER_ID1 in webrtc_server.clients.keys())

    @testing.gen_test
    def test_when_clients_goes_offline_clientws_is_removed_from_memory(self):
        client_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'), id=TEST_PEER_ID1)
        client_socket.read_message()
        client_socket.close()
        client_socket2 = yield self._mk_ws_connection(webrtc_server.app.reverse_url('login_ws'),
                                                     id=TEST_PEER_ID2)
        self.assertTrue(TEST_PEER_ID1 not in webrtc_server.clients.keys())
        self.assertTrue(TEST_PEER_ID2 in webrtc_server.clients.keys())

if __name__ == "__main__":
    testing.unittest.main(verbosity=1)