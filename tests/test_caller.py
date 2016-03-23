__author__ = 'anthony'
from test_common import *

class TestCallerApp(BasicTestCase):

    @testing.gen_test
    def test_caller_page_is_rendered_correctly(self):
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        response = yield self.http_client.fetch(caller_page_uri)
        caller_ws_uri = self.make_relative_url(webrtc_server.app.reverse_url('caller_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        loader = template.Loader(webrtc_server.TEMPLATE_DIR)
        ice_url = self.make_relative_url(webrtc_server.app.reverse_url('ice_url'))
        self.assertEqual(response.body, loader.load('base.html').generate(ws_uri=caller_ws_uri,
                                                                          my_id=MY_CALLER_ID,
                                                                          peer_id=TEST_PEER_ID1,
                                                                          title='Caller',
                                                                          ice_url=ice_url,
                                                                          ice_pass=webrtc_server.get_ice_pass()))

    @testing.gen_test
    def test_client_count_increases_everytime_ws_logs_in(self):
        caller_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        self.assertEqual(len(webrtc_server.clients), 1)
        reciever_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        self.assertEqual(len(webrtc_server.clients), 2)

    @testing.gen_test
    def test_caller_page_contain_ice_credentials_with_incorrect_ice_token(self):
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        ice_token = webrtc_server.ICE_ACCESS_TOKEN
        webrtc_server.ICE_ACCESS_TOKEN = ''
        response = yield self.http_client.fetch(caller_page_uri)
        webrtc_server.ICE_ACCESS_TOKEN = ice_token
        caller_ws_uri = self.make_relative_url(webrtc_server.app.reverse_url('caller_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        loader = template.Loader(webrtc_server.TEMPLATE_DIR)
        ice_url = self.make_relative_url(webrtc_server.app.reverse_url('ice_url'))
        self.assertNotEquals(response.body, loader.load('base.html').generate(ws_uri=caller_ws_uri,
                                                                          my_id=MY_CALLER_ID,
                                                                          peer_id=TEST_PEER_ID1,
                                                                          title='Caller',
                                                                          ice_url=ice_url,
                                                                          ice_pass=webrtc_server.get_ice_pass()))

    @testing.gen_test
    def test_caller_page_uses_CallHandler_for_signaling(self):
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        try:
            response = yield self.http_client.fetch(caller_page_uri)
            caller_ws_uri = self.make_relative_url(webrtc_server.app.reverse_url('caller_ws'),
                                        id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
            self.assertIn(caller_ws_uri, response.body)
            code = response.code
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_get_or_post_to_call_page_url_gives_same_caller_page(self):
        import urllib
        caller_page_uri = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http', id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        caller_page_uri_no_query_string = self.make_url(webrtc_server.app.reverse_url('caller_page'),
                                        protocol='http')
        data = { 'id': MY_CALLER_ID, 'peer_id': TEST_PEER_ID1 } #A dictionary of your post data
        request_body = urllib.urlencode(data)
        self.assertEqual(caller_page_uri, '%s?%s'%(caller_page_uri_no_query_string, request_body))
        try:
            response1 = yield self.http_client.fetch(caller_page_uri, method='GET')
            response2 = yield self.http_client.fetch(caller_page_uri_no_query_string,
                                                     method='POST', body=request_body)
            self.assertEqual(response1.body, response2.body)
        except httpclient.HTTPError, ex:
            self.assertTrue(False)

    @testing.gen_test
    def test_caller1_connects_to_peer2_then_again_caller1_connects_to_peer2_using_separate_client_passes(self):
        caller_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        caller_socket2 = yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_message = 'hey man'
        test_message2 = 'hey boy'
        caller_socket.write_message(test_message)
        caller_socket2.write_message(test_message2)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_message, rcved_msg)
        rcved_msg2 =  yield reciever_socket.read_message()
        self.assertEqual(test_message2, rcved_msg2)


    @testing.gen_test
    def test_caller1_connects_from_2_clients_msg_to_peer_2_from_either_client_is_seen_in_sibling_client(self):
        caller_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        caller_socket2 = yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket = yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        reciever_socket2 = yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        self.assertEqual(len(webrtc_server.clients[MY_CALLER_ID]), 2)
        test_message = 'hey man'
        test_message2 = 'hey boy'
        caller_socket.write_message(test_message)
        caller_socket2.write_message(test_message2)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_message, rcved_msg)
        rcved_msg2 =  yield reciever_socket.read_message()
        self.assertEqual(test_message2, rcved_msg2)
        rcved_msg = yield reciever_socket2.read_message()
        self.assertEqual(test_message, rcved_msg)
        rcved_msg2 =  yield reciever_socket2.read_message()
        self.assertEqual(test_message2, rcved_msg2)
        cl1_recv_msg = yield caller_socket.read_message()
        self.assertEqual(cl1_recv_msg, test_message2)
        cl2_recv_msg = yield caller_socket2.read_message()
        self.assertEqual(cl2_recv_msg, test_message)

    @testing.gen_test
    def test_two_callers_can_converse_with_same_reciepent_provided_its_separate_conversation(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1)
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_message = 'hey boy'
        caller_socket.write_message(test_message)
        rcv_msg = yield reciever_socket.read_message()
        self.assertEqual(test_message, rcv_msg)
        caller_socket2 =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=TEST_PEER_ID2, peer_id=TEST_PEER_ID1)
        test_message2 = 'hello man'
        caller_socket2.write_message(test_message2)
        # try:
        #     yield reciever_socket.read_message()
        #     self.fail('expected timeout did not happen')
        # except Exception:
        #     pass
        ##login to same conversation
        reciever_socket2 = yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=TEST_PEER_ID2)
        caller_socket2.write_message(test_message2)
        rcv_msg = yield reciever_socket2.read_message()
        self.assertEqual(test_message2, rcv_msg)

    @testing.gen_test
    def test_subsequent_messages_from_caller_websocket_goes_to_reciepient_peer_websocket(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        test_msg1 = 'hey man2'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        caller_socket.write_message(test_msg1)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg1, rcved_msg)

    @testing.gen_test
    def test_caller_ws_gets_peer_unavailable_msg_when_peer_gets_disconnected(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        test_msg1 = 'hey man2'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        reciever_socket.close()
        caller_socket.write_message(test_msg1)
        rcved_msg = yield caller_socket.read_message()
        self.assertEqual(webrtc_server.get_notice_msg(webrtc_server.PEER_UNAVAILABLE), rcved_msg)

    @testing.gen_test
    def test_after_caller_getting_peer_unavailable_and_peer_is_back_online_msg_is_delivered_to_peer(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'hey man'
        test_msg1 = 'hey man2'
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        reciever_socket.close()
        caller_socket.write_message(test_msg1)
        rcved_msg = yield caller_socket.read_message()
        self.assertEqual(webrtc_server.get_notice_msg(webrtc_server.PEER_UNAVAILABLE), rcved_msg)
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        caller_socket.write_message(test_msg)
        rcved_msg = yield reciever_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)

    @testing.gen_test
    def test_caller_with_no_peer_id_gets_message_from_reciever_with_caller_as_peer_id(self):
        caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
                                                         id=MY_CALLER_ID) #make call
        reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
                                                         id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
        test_msg = 'HEY MAN'
        test_msg2 = 'HEY MAN AGAIN'
        reciever_socket.write_message(test_msg)
        reciever_socket.write_message(test_msg2)
        rcved_msg = yield caller_socket.read_message()
        rcved_msg2 = yield caller_socket.read_message()
        self.assertEqual(test_msg, rcved_msg)
        self.assertEqual(test_msg2, rcved_msg2)

    # @testing.gen_test
    # def test_caller_info_is_removed_from_inmemory_when_caller_websocket_disconnects(self):
    #     caller_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('caller_ws'),
    #                                                      id=MY_CALLER_ID, peer_id=TEST_PEER_ID1) #make call
    #     reciever_socket =  yield self._mk_ws_connection(webrtc_server.app.reverse_url('reciever_ws'),
    #                                                      id=TEST_PEER_ID1, peer_id=MY_CALLER_ID) #pickup call
    #     test_msg = 'yep yep'
    #     caller_socket.write_message(test_msg)
    #     val = yield reciever_socket.read_message()
    #     caller_socket.close()
    #     caller_socket = None
    #     reciever_socket.write_message(test_msg)
    #     self.assertTrue(MY_CALLER_ID not in webrtc_server.clients.keys())

if __name__ == "__main__":
    testing.unittest.main(verbosity=1)
