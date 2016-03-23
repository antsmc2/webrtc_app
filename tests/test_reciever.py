__author__ = 'anthony'

from test_common import *


class TestRecieverApp(BasicTestCase):

    @testing.gen_test
    def test_recieve_page_uses_RecieveHandler_for_signaling(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        reciever_page_uri = self.make_url(webrtc_server.app.reverse_url('reciever_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        try:
            response = yield self.http_client.fetch(reciever_page_uri)
            reciever_ws_uri = self.make_relative_url(webrtc_server.app.reverse_url('reciever_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
            self.assertIn(reciever_ws_uri, response.body)
            code = response.code
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_recieve_websocket_message_is_sent_to_the_correct_caller(self):
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
    def test_caller_page_is_rendered_correctly(self):
        reciever_page_uri = self.make_url(webrtc_server.app.reverse_url('reciever_page'),
                                        protocol='http', id=TEST_PEER_ID1, peer_id=MY_CALLER_ID)
        response = yield self.http_client.fetch(reciever_page_uri)
        recieve_ws_uri = self.make_relative_url(webrtc_server.app.reverse_url('reciever_ws'),
                                        id=TEST_PEER_ID1, peer_id=MY_CALLER_ID)
        loader = template.Loader(webrtc_server.TEMPLATE_DIR)
        ice_url = self.make_relative_url(webrtc_server.app.reverse_url('ice_url'))
        self.assertEqual(response.body, loader.load('base.html').generate(ws_uri=recieve_ws_uri,
                    my_id=TEST_PEER_ID1, peer_id=MY_CALLER_ID, title='Receiver',
                                                                          ice_url=ice_url,
                                                                          ice_pass=webrtc_server.get_ice_pass()))

    @testing.gen_test
    def test_get_or_post_to_recieve_page_url_gives_same_reciever_page(self):
        import urllib
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
    def test_ice_server_is_retreived_with_correct_token(self):
        ice_uri_no_query_string = self.make_url(webrtc_server.app.reverse_url('ice_url'),
                                        protocol='http')
        response = yield self.http_client.fetch(ice_uri_no_query_string,
                                                     method='POST', body=webrtc_server.ICE_ACCESS_TOKEN)
        self.assertEqual(json.loads(response.body), webrtc_server.iceServers)

    @testing.gen_test
    def test_reciever_ws_gets_peer_unavailable_msg_when_peer_gets_disconnected(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        test_msg1 = 'hey man2'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        caller_socket.close()
        reciever_socket.write_message(test_msg1)
        reciever_socket.write_message(test_msg1)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(webrtc_server.get_notice_msg(webrtc_server.PEER_UNAVAILABLE), rcved_msg)

    @testing.gen_test
    def test_after_reciever_getting_peer_unavailable_and_peer_is_back_online_msg_is_delivered_to_peer(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        test_msg1 = 'hey man2'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        caller_socket.close()
        reciever_socket.write_message(test_msg1)
        reciever_socket.write_message(test_msg1)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(webrtc_server.get_notice_msg(webrtc_server.PEER_UNAVAILABLE), rcved_msg)
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket.write_message(test_msg)
        rcved_msg = yield caller_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)

    @testing.gen_test
    def test_reciever_with_no_peer_id_gets_message_from_caller_with_reciever_as_peer_id(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1) #pickup call
        test_msg = 'hey man'
        test_msg2 = 'hey boy'
        caller_socket.write_message(test_msg)
        caller_socket.write_message(test_msg2)
        rcved_msg = yield reciever_socket.read_message()
        rcved_msg2 = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        self.assertEqual(test_msg2, rcved_msg2)

if __name__ == "__main__":
    testing.unittest.main(verbosity=1)