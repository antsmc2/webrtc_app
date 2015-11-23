# webrtc_app
Basic Web RTC app using Python-Tornado websockets for signaling.
The app also provides pages for caller and receiver

##Installation
>git clone https://github.com/antsmc2/webrtc_app.git

>cd webrtc_app

>pip install -r pip-requirements.txt

##Documentation
This Webrtc server has been tested on python2.7, tornado 4.3

To start the webrtc server, run the following command:

>python webrtc_server.py start {port_number}

The webrtc_server runs in background.

To make WEBRTC call from caller_id to receiver_id, receiver must first login to server using websocket endpoint on:

>ws://127.0.0.1:PORT/wslogin?id={receiver_id}

This websocket login can happen from any client app. Eg web browser or custom application supporting websockets

Caller page is accessed on the link:

 >http://127.0.0.1:PORT/call?id={caller_id}&peer_id={receiver_id}

Receiver page is accessed on the link:

 http://127.0.0.1:PORT/call?id={caller_id}&peer_id={reciever_id}


##Testing
Unit tests are all in tests folder

To run unit tests using below commands:

>python -m tornado.testing discover tests/


