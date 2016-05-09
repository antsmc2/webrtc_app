# webrtc_app
Basic Web RTC app using Python-Tornado websockets for signaling.
The app also provides pages for caller and receiver

##Installation
>git clone https://github.com/antsmc2/webrtc_app.git

>cd webrtc_app

>pip install -r pip-requirements.txt

##Documentation
This Webrtc server has been tested on python2.7, tornado 4.3

To start the webrtc server in background with supervisor, run the following command in the project directory:

>supervisord

To start the webrtc server in foreground, run the following command:

>python webrtc_server.py start {port_number}


Once the signal server is up and running, calling can start.

To make WEBRTC call from caller_id to receiver_id, simply enter the following URLs on the browser:

Caller page is accessed on the link:

 >http://HOST:PORT/call?id={caller_id}&peer_id={receiver_id}

Receiver page is accessed on the link:

 >http://HOST:PORT/recieve?id={reciever_id}&peer_id={caller_id}


The caller_id and reciever_id can be arbitrary values. The only requirement is that they are matching on both sides.

###Server settings

####ICE_URL
This is the relative URL path which shall be used to retrieve the ice settings from the webrtc clients. Default value is **r'/ice_servers'**

####ICE_ACCESS_TOKEN
This is the token which must be offered from webrtc client before ice settings can be retrieved. To access ice settings, webrtc client must perform post to ICE_URL. Post body must be autorized ICE_ACCESS_TOKEN. 

####iceServers
This is list of all ice servers to be used on webrtc client PeerConnection (STUN and TURN). It must contain list of dictionaries containing ice server credentials. If you plan use the webrtc across NATs, it is recommended to include at least one functioning TURN server in the ice server settings.

###Customizing Ice retrieval
Default behavior when browser requests a page is for the ICE_ACCESS_TOKEN to be supplied to the page for later authentication when retrieving ice server details via POST to ICE_URL.

To enable more dynamic allocation of ICE_ACCESS_TOKEN, **has_ice_pass** and **get_ice_pass** can be overridden as per needed policy requirement. e.g. change ACCESS_TOKEN periodically, to communicate with other backend systems like database, redis etc. 

**get_ice_pass** function is used to retrieve the ICE_ACCESS_TOKEN to be supplied to webrtc client.

**has_ice_pass** function is used to authenticate the ICE_ACCESS_TOKEN when webrtc client is requesting for ice settings via ICE_URL.

Implementation for bothe can be customized as per specific requirement.

###Signaling via websocket
The webrtc_server has a websocket server which can be used for signaling via websocket client. This can be useful in scenarios when both parties want to perform some communication via websocket before actually launching the browsers for webrtc call.

####Communicating via websocket client
To communicate via websocket between caller_id and reciever_id, the caller/initiator websocket client must connect with:

>ws.connect('ws://HOST:PORT/wscall?id={caller_id}&peer_id={receiver_id}')

In this case, for the reciever to get the caller messages, reciever websocket client should stay online with:

>ws.connect('ws://HOST:PORT/wscall?id={reciever_id}&peer_id={caller_id}')

ws and wss schemes are both supported.  

Provided bothe parties are online, message is delivered.

Messages would be delievered to both parties regardless of scheme provided id pairs are matching.

In the event one party tries to send messages to the other party who has gotten disconnected, that party gets below msg: 
```
    {
     'msg_type' : 'SERVER_NOTICE',
     'message': 'PEER-UNAVAILABLE'
     }
```


##Testing
Unit tests are all in tests folder

Run the unittest from project folder using below commands:

>python -m tornado.testing discover tests/


