
"use strict";

var myHostname = window.location.hostname;
var myPort = window.location.port;
console.log("Hostname: " + myHostname);

//using websockets
var connection = null;

var mediaConstraints = {
  audio: true,            // We want an audio track
  video: { frameRate: { min: 10, ideal: 15, max: 30 }, width: {exact: 160}, height: {exact: 120} }             // ...and we want a video track
};

var NOT_STARTED = 1;
var CALL_IN_PROGRESS = 2;
var RESTARTING = 3;
var CLOSING = 4;
var peerConnected = false;
var callStatus = NOT_STARTED;
var myUsername = null;
var targetUsername = null;      // To store username of other peer
var meColor = '#DEDEDD';
var youColor = '#26AE90';
var systemMessageColor = '#F8CD71';
var myPeerConnection = null;    // RTCPeerConnection
var dataChannel = null;
var dataChannelID = null;
var clientID = 0;
var serverUrl = null;

var remoteVideo = null;
var localVideo = null;
var hangupButton = null;
var startTime = null;
var muteButton = null;
var unMuteButton = null;

var localStream;
var localDesc = null;
var remoteDesc = null;
var pc1;
var pc2;
var offerOptions = {
  offerToReceiveAudio: 1,
  offerToReceiveVideo: 1
};

//var dataChannelOptions = {
//  ordered: false, // don not guarantee order
//  maxRetransmitTime: 2000, // in milliseconds
//};

var dataChannelOptions = null; //use browser defaults

var iceServers = null;

function getName(pc) {
  return (pc === myPeerConnection) ? myUsername : targetUsername;
}

var bandwidthSelector = null;
var videoResolutionSelector = null;


function findLine(sdpLines, prefix, substr) {
  return findLineInRange(sdpLines, 0, -1, prefix, substr);
}
function findLineInRange(sdpLines, startLine, endLine, prefix, substr) {
  var realEndLine = endLine !== -1 ? endLine : sdpLines.length;
  for (var i = startLine;i < realEndLine;++i) {
    if (sdpLines[i].indexOf(prefix) === 0) {
      if (!substr || sdpLines[i].toLowerCase().indexOf(substr.toLowerCase()) !== -1) {
        return i;
      }
    }
  }
  return null;
}

function setPreferredCodec(sdp, type, dir, codec) {
  var str = type + " " + dir + " codec";
  if (!codec) {
    trace("No preference on " + str + ".");
    return sdp;
  }
  trace("Prefer " + str + ": " + codec);
  var sdpLines = sdp.split("\r\n");
  var mLineIndex = findLine(sdpLines, "m=", type);
  if (mLineIndex === null) {
    return sdp;
  }
  var payload = getCodecPayloadType(sdpLines, codec);
  trace('found codec payload: ' + payload);
  trace('codec order: '+ sdpLines[mLineIndex]);
  if (payload) {
    sdpLines[mLineIndex] = setDefaultCodec(sdpLines[mLineIndex], payload);
  }
  trace('updated codec order: '+ sdpLines[mLineIndex]);
  sdp = sdpLines.join("\r\n");
  return sdp;
}

function setPreferredVideoSendCodec(sdp) {
  var codecSelector = document.querySelector('select#codec');
  return setPreferredCodec(sdp, "video", "send", codecSelector.options[codecSelector.selectedIndex].value);
}

function getCodecPayloadType(sdpLines, codec) {
  var index = findLine(sdpLines, "a=rtpmap", codec);
  return index ? getCodecPayloadTypeFromLine(sdpLines[index]) : null;
}

function getCodecPayloadTypeFromLine(sdpLine) {
  var pattern = new RegExp("a=rtpmap:(\\d+) [a-zA-Z0-9-]+\\/\\d+");
  var result = sdpLine.match(pattern);
  return result && result.length === 2 ? result[1] : null;
}

function setDefaultCodec(mLine, payload) {
  var elements = mLine.split(" ");
  var newLine = elements.slice(0, 3);
  newLine.push(payload);
  for (var i = 3;i < elements.length;i++) {
    if (elements[i] !== payload) {
      newLine.push(elements[i]);
    }
  }
  return newLine.join(" ");
}


function updateBandwidthRestriction(sdp, bandwidth) {
  if (sdp.indexOf('b=AS:') === -1) {
    // insert b=AS after c= line.
    sdp = sdp.replace(/c=IN IP4 (.*)\r\n/,
                      'c=IN IP4 $1\r\nb=AS:' + bandwidth + '\r\n');
  } else {
    sdp = sdp.replace(/b=AS:(.*)\r\n/, 'b=AS:' + bandwidth + '\r\n');
  }
  return sdp;
}

function setVideoConstraints() {
    videoResolutionSelector = document.querySelector('select#vidResolution');
    var resolution = videoResolutionSelector.options[videoResolutionSelector.selectedIndex].value;
    if(resolution === 'v-high') {
        mediaConstraints.video = { facingMode: "user", frameRate: { min: 25, ideal: 30, max: 30 }, width: {exact: 1920},
                                    height: {exact: 1080}};
    }
    if(resolution === 'high') {
        mediaConstraints.video = { facingMode: "user", frameRate: { min: 20, ideal: 30, max: 30 }, width: {exact: 1280},
                                        height: {exact: 720} };
    }
    if(resolution === 'medium') {
        mediaConstraints.video = { facingMode: "user", frameRate: { min: 20, ideal: 25, max: 30 }, width: {exact: 640},
                                        height: {exact: 480} };
    }
    if(resolution === 'low') {
        mediaConstraints.video = { facingMode: "user", frameRate: { min: 10, ideal: 15, max: 30 }, width: {exact: 320},
                                        height: {exact: 240} };
    }
    if(resolution === 'v-low') {
        mediaConstraints.video = { facingMode: "user", frameRate: { min: 10, ideal: 15, max: 30 }, width: {exact: 160},
                                    height: {exact: 120} };
    }
    trace('using media constraints: ');
    console.dir(mediaConstraints);
}

function removeBandwidthRestriction(sdp) {
  return sdp.replace(/b=AS:(.*)\r\n/, '');
}

function sendToServer(msg) {

  if(peerConnected == false) {
      switch (connection.readyState) {
          case WebSocket.CLOSING:
          case WebSocket.CLOSED:
            alert('Looks like you got offline. Pls Check your network and restart the call');
            return;
        }
   }

  if(!msg.target)
    msg.target = targetUsername;
  var msgJSON = JSON.stringify(msg);

  trace("Sending '" + msg.type + "' message: " + msgJSON);
  connection.send(msgJSON);
}

function broadcastPresence(username) {

    sendToServer({
      name: myUsername,
      date: Date.now(),
      type: "username",
      target: targetUsername
    });
}

function resetCallControls() {
    bandwidthSelector = document.querySelector('select#bandwidth');

    bandwidthSelector.onchange = function() {
      if(myPeerConnection == null)
        return;
      bandwidthSelector.disabled = true;
      var bandwidth = bandwidthSelector.options[bandwidthSelector.selectedIndex]
          .value;
      myPeerConnection.setLocalDescription(myPeerConnection.localDescription)
      .then(function() {
        var desc = myPeerConnection.remoteDescription;
        trace('Applying bandwidth restriction: ' + bandwidth);
        if (bandwidth === 'unlimited') {
          desc.sdp = removeBandwidthRestriction(desc.sdp);
        } else {
          desc.sdp = updateBandwidthRestriction(desc.sdp, bandwidth);
        }
        trace('Applying bandwidth restriction to setRemoteDescription:\n' +
            desc.sdp);
        return myPeerConnection.setRemoteDescription(desc);
      })
      .then(function() {
        bandwidthSelector.disabled = false;
      })
      .catch(onSetSessionDescriptionError);
    };
}

function connect(path, username, peer_id, ice_url, ice_pass) {
  myUsername = username;
  targetUsername = peer_id;
  clientID = myUsername;
  var scheme = "ws";

  // If this is an HTTPS connection, we have to use a secure WebSocket
  // connection too, so add another "s" to the scheme.
  var req_protocol = document.location.protocol;
  if (req_protocol === "https:") {
      scheme += "s";
  }
  serverUrl = scheme + "://" + myHostname + ':' + myPort + path;

  console.log('using server url: ' + serverUrl);
  resetCallControls();
  var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
       if (xhttp.readyState == 4 && xhttp.status == 200) {
          iceServers = JSON.parse(xhttp.responseText);
          initialize(serverUrl);
       }
    }
    xhttp.open("POST", ice_url);
    xhttp.send(ice_pass);

    hangupButton = document.getElementById("hangup-button");
    remoteVideo = document.getElementById("received_video");
    localVideo = document.getElementById("local_video");
unMuteButton = document.getElementById("unMuteAudio");
unMuteButton.style.display = "none";
    localVideo.addEventListener('loadedmetadata', function() {
      trace('Local video videoWidth: ' + this.videoWidth +
        'px,  videoHeight: ' + this.videoHeight + 'px');
    });

    remoteVideo.addEventListener('loadedmetadata', function() {
      trace('Remote video videoWidth: ' + this.videoWidth +
        'px,  videoHeight: ' + this.videoHeight + 'px');
    });

    remoteVideo.onresize = function() {
      trace('Remote video size changed to ' +
        remoteVideo.videoWidth + 'x' + remoteVideo.videoHeight);
      //****To do******
      // We'll use the first onsize callback as an indication that video has started
      // playing out.
      if (startTime) {
        var elapsedTime = window.performance.now() - startTime;
        trace('Setup time: ' + elapsedTime.toFixed(3) + 'ms');
        startTime = null;
      }
    };

}

function initialize(serverUrl, callbacks) {
  if(callbacks === undefined)
    callbacks = {};
  connection = new WebSocket(serverUrl);
  connection.onopen = function(event) {
    trace('connection opened.');
    //get ice servers
    if(callbacks.onSignalingOpen)
        callbacks.onSignalingOpen();
    else
        start();
    if(callbacks.onFinishRTCInit)
        callbacks.onFinishRTCInit();
    trace('on signal open sequence complete.');
  };

  connection.onclose = function() {
    trace('signal server link closed');
    if(peerConnected === true || callStatus === NOT_STARTED) {
        trace('Seems server ran away while still in contact with Peer.');
        return setTimeout(function(){ initialize(serverUrl,
                                    {
                                        'onSignalingOpen': function(){}
                                    }); }, 3000);
    }
    if(callStatus !== RESTARTING)
        updateChat({text: 'Please check your network connection'});
  }

  connection.onmessage = function(evt) {
//    if (document.getElementById("send").disabled) {
//      document.getElementById("text").disabled = false;
//      document.getElementById("send").disabled = false;
//    }
    var text = "";
    var msg = JSON.parse(evt.data);
    trace("Message received: ");
    console.dir(msg);
    if(msg.msg_type == 'SERVER_NOTICE' && msg.message == 'PEER-UNAVAILABLE') {
        return updateChat({text: targetUsername + ' not online'});
    }
    if(msg.target != myUsername) //you can only call if its your conversation
        return;
    var time = new Date(msg.date);
    var timeStr = time.toLocaleTimeString();

    switch(msg.type) {

      case "username":
        if(callStatus !== CALL_IN_PROGRESS)
            call(msg.name);
        break;

      case "message":
        updateChat(msg);
        break;

      case "add-stream":  //invitation to add stream
        handleAddStreamMsg(msg);
        break;

      // Signaling messages: these messages are used to trade WebRTC
      // signaling information during negotiations leading up to a video
      // call.

      case "video-offer":  // Invitation and offer to chat
        handleVideoOfferMsg(msg);
        break;

      case "video-answer":  // Callee has answered our offer
        handleVideoAnswerMsg(msg);
        break;

      case "new-ice-candidate": // A new ICE candidate has been received
        if(peerConnected == false)
            handleNewICECandidateMsg(msg);
        break;

      case "hang-up": // The other peer has hung up the call
        handleHangUpMsg(msg);
        break;

       case "start-call":
          updateChat({text: 'restart call from ' + targetUsername});
          if(callStatus !== CALL_IN_PROGRESS)
              start(function(){
                            broadcastPresence(myUsername);
                        });
          break;

      // Unknown message; output to console for debugging.

      default:
        trace("Error: Unknown message received: " + msg);
    }

  };


}

function enableChat() {
    document.getElementById("text").disabled = false;
    document.getElementById("send").disabled = false;
}

function disableChat() {
    document.getElementById("text").disabled = true;
    document.getElementById("send").disabled = true;
}

function updateChat(msg)
{
  if(!(msg.text && msg.text.trim()))
    return;
  var date = Date.now();
  if(msg.date)
    date = msg.date;
  var time = new Date(date);
  var timeStr = time.toLocaleTimeString();
  var color = systemMessageColor;
  var name = msg.name ? msg.name : '';
  switch(msg.name){
    case myUsername:
      color = meColor;
      break;
    case targetUsername:
      color = youColor;
      break;
  }
  var text = '<span class="you-msg" style="color: ' + color + ';">(' + timeStr + ") <b>" + name + "</b>: " + msg.text + "<br></span>";
  var chatPane = document.getElementById("chatbox");
  chatPane.innerHTML = chatPane.innerHTML + '<p class="chat">' + text + '</p>';
  document.querySelector('#chatbox .chat:last-of-type').scrollIntoView();
}

function resetChat() {
  var chatPane = document.getElementById("chatbox");
  chatPane.innerHTML = '';
}

// Handler for keyboard events. This is used to intercept the return and
// enter keys so that we can call send() to transmit the entered text
// to the server.
function handleKey(evt) {
  if (evt.keyCode === 13 || evt.keyCode === 14) {
    if (!document.getElementById("send").disabled) {
      handleSendButton();
    }
  }
}

// Handles a click on the Send button (or pressing return/enter) by
// building a "message" object and sending it to the server.
function handleSendButton() {
  var msg = {
    text: document.getElementById("text").value,
    type: "message",
    id: clientID,
    name: myUsername,
    date: Date.now()
  };
  document.getElementById("text").value = "";
  var time = new Date(msg.date);
  var timeStr = time.toLocaleTimeString();
  if (msg.text.length) {
      try {
        dataChannel.send(JSON.stringify(msg));
      }catch(e) {
          trace('Error sending msg: ' + e);
          sendToServer(msg);
      }
      updateChat(msg);
  }
}

function gotStream(stream) {
  trace('Received local stream');
  localVideo.src = window.URL.createObjectURL(stream);
  localVideo.srcObject = stream;
  localStream = stream;
  document.querySelector('select#codec').disabled = true;
  videoResolutionSelector.disabled = true;
  trace('done setting stream');
}

function setUpDataChannel() {
  trace('setting up data channel');

  dataChannelID = dataChannel.id;

  dataChannel.onerror = function (error) {
    trace("Data Channel Error:" + error);
  };

  dataChannel.onmessage = onReceiveDataChannelMessage;

  dataChannel.onopen = function () {
    trace('Send channel state is: ' + dataChannel.readyState);
    resetChat();
    updateChat({text: 'Connected to ' + targetUsername});
    enableChat();
  };

  dataChannel.onclose = function () {
    trace("The Data Channel is Closed");
    disableChat();
  };
  trace('done setting up channel');
}

function onReceiveDataChannelMessage (event) {
    trace("Got Data Channel Message:" + event.data);
    var msg = JSON.parse(event.data);
    switch(msg.type) {
        case "message":
            updateChat(msg);
            break;
        case "hang-up":
            handleHangUpMsg(msg);
            break;
    };
  };

function receiveDataChannel(event) {
        trace('recieved data channel');
        dataChannel = event.channel;
        setUpDataChannel();
}


function start(onMediaInit) {
  trace('Requesting local stream');
  trace('using media callback ' + onMediaInit);
  setVideoConstraints();
  navigator.mediaDevices.getUserMedia(mediaConstraints)
  .then(function(stream) {
      gotStream(stream);
      resetPeer();
      if(onMediaInit) {
        onMediaInit();
      }
      else {
        broadcastPresence(myUsername);
      }

  })
  .catch(function(e) {
    alert('getUserMedia() error: ' + e.name);
  });
}

function resetPeer() {
       myPeerConnection = new RTCPeerConnection({
      iceServers: iceServers
      });
      trace('Created local peer connection object myPeerConnection');
      myPeerConnection.onicecandidate = function(e) {
        onIceCandidate(myPeerConnection, e);
      };
      myPeerConnection.oniceconnectionstatechange = handleICEConnectionStateChangeEvent;
      myPeerConnection.onaddstream = gotRemoteStream;
}

function call() {
//  hangupButton.disabled = false;
  trace('Starting call');
  trace('creating data channel');
  dataChannel = myPeerConnection.createDataChannel("chat", dataChannelOptions);
  setUpDataChannel();
  startTime = window.performance.now();
  var videoTracks = localStream.getVideoTracks();
  var audioTracks = localStream.getAudioTracks();
  if (videoTracks.length > 0) {
    trace('Using video device: ' + videoTracks[0].label);
  }
  if (audioTracks.length > 0) {
    trace('Using audio device: ' + audioTracks[0].label);
  }
  trace('Adding remote stream to myPeerConnection');
  myPeerConnection.addStream(localStream);
  trace('myPeerConnection createOffer start');
  myPeerConnection.createOffer(offerOptions)
    .then(function(desc){
        onCreateOfferSuccess(desc);
    })
    .catch(function(error) {
        onCreateSessionDescriptionError(error);
    });
}

function onCreateSessionDescriptionError(error) {
  trace('Failed to create session description: ' + error.toString());
}


function onCreateOfferSuccess(desc) {
  desc.sdp = setPreferredVideoSendCodec(desc.sdp);
  localDesc = desc;
  trace('Offer from myPeerConnection\n' + desc.sdp);
  trace('pc1 setLocalDescription start');
  myPeerConnection.setLocalDescription(desc)
  .then(function() {
    onSetLocalSuccess(myPeerConnection);
    trace("Sending offer packet back to other peer");
    sendToServer({
        name: myUsername,
        target: targetUsername,
        type: "video-offer",
        sdp: desc
      });
  })
  .catch(function(error) {
    onSetSessionDescriptionError(error);
    });
}

function onSetLocalSuccess(pc) {
  trace(getName(pc) + ' setLocalDescription complete');
}

function onSetRemoteSuccess(pc) {
  trace(getName(pc) + ' setRemoteDescription complete');
}

function onSetSessionDescriptionError(error) {
  trace('Failed to set session description: ' + error.toString());
}

function gotRemoteStream(e) {
  remoteVideo.srcObject = e.stream;
  remoteVideo.src = window.URL.createObjectURL(e.stream);
  bandwidthSelector.disabled = false;
  trace('pc2 received remote stream');
}


function handleVideoOfferMsg(msg) {
  hangupButton.disabled = false;
  callStatus = CALL_IN_PROGRESS;
  myPeerConnection.ondatachannel = receiveDataChannel; //register to use callers datachannel
  var desc = new RTCSessionDescription(msg.sdp);
  trace('Accepting call');
  startTime = window.performance.now();
  var videoTracks = localStream.getVideoTracks();
  var audioTracks = localStream.getAudioTracks();
  if (videoTracks.length > 0) {
    trace('Using video device: ' + videoTracks[0].label);
  }
  if (audioTracks.length > 0) {
    trace('Using audio device: ' + audioTracks[0].label);
  }
  trace('recieved offer is ' + desc);
  desc = getAdjustedBandwidth(desc);
  myPeerConnection.setRemoteDescription(desc)
    .then(function() {
    onSetRemoteSuccess(myPeerConnection);
    remoteDesc = desc;
    trace('Adding remote stream to myPeerConnection');
    myPeerConnection.addStream(localStream);
    trace('myPeerConnection createAnswer start');
      // Since the 'remote' side has no media stream we need
      // to pass in the right constraints in order for it to
      // accept the incoming offer of audio and video.
    myPeerConnection.createAnswer(onCreateAnswerSuccess, onCreateSessionDescriptionError);
  })
  .catch(function(error) {
    onSetSessionDescriptionError(error);
  });

}

function onCreateAnswerSuccess(desc) {
  desc.sdp = setPreferredVideoSendCodec(desc.sdp);
  localDesc = desc;
  trace('Answer from myPeerConnection:\n' + desc.sdp);
  trace('myPeerConnection setLocalDescription start');
  myPeerConnection.setLocalDescription(desc)
    .then( function() {
      onSetLocalSuccess(myPeerConnection);
      trace("Sending answer packet back to other peer");
      sendToServer({
          name: myUsername,
          target: targetUsername,
          type: "video-answer",
          sdp: desc
        });
  })
   .catch(
   function(error) {
        onSetSessionDescriptionError(error);
   });
  // We've configured our end of the call now. Time to send our
  // answer back to the caller so they know that we want to talk
  // and how to talk to us.

}

function getAdjustedBandwidth(desc){
  var bandwidth = bandwidthSelector.options[bandwidthSelector.selectedIndex]
          .value;
  if (bandwidth !== 'unlimited') {
    trace('SC. Applying bandwidth restriction: ' + bandwidth);
    desc.sdp = updateBandwidthRestriction(desc.sdp, bandwidth);
  }
  return desc;
}

function handleVideoAnswerMsg(msg) {
  callStatus = CALL_IN_PROGRESS;
  hangupButton.disabled = false;
  var desc = new RTCSessionDescription(msg.sdp);
  trace('myPeerConnection setRemoteDescription start');
  desc = getAdjustedBandwidth(desc);
  myPeerConnection.setRemoteDescription(desc)
   .then(function() {
    remoteDesc = desc;
    onSetRemoteSuccess(myPeerConnection);
  })
  .catch(function(error) {
    onSetSessionDescriptionError(error);
  });
}

function handleAddStreamMsg(msg) {
  trace('got request to add share stream with remote');
  trace('Adding remote stream to myPeerConnection');
  myPeerConnection.addStream(localStream);
}

function onIceCandidate(pc, event) {
  if (event.candidate) {
//    myPeerConnection.onicecandidate = function(){};
    trace('sending ice candidate: ' + event.candidate);
    sendToServer({
      type: "new-ice-candidate",
      target: targetUsername,
      candidate: event.candidate
    });
    trace(getName(pc) + ' ICE candidate: \n' + event.candidate);
  }
}

function onAddIceCandidateSuccess(pc) {
  trace(getName(pc) + ' addIceCandidate success');
}

function onAddIceCandidateError(pc, error) {
  trace(getName(pc) + ' failed to add ICE Candidate: ' + error.toString());
}

function handleHangUpMsg(msg) {
  trace("*** Received hang up notification from other peer");
  updateChat({text: targetUsername + ' ended call.'});
  closeVideoCall();
}

// A new ICE candidate has been received from the other peer. Call
// RTCPeerConnection.addIceCandidate() to send it along to the
// local ICE framework.

function handleNewICECandidateMsg(msg) {
  var candidate = new RTCIceCandidate(msg.candidate);
  trace("Adding received ICE candidate: " + JSON.stringify(candidate));
  myPeerConnection.addIceCandidate(candidate)
    .then(
        function() {
          onAddIceCandidateSuccess(myPeerConnection);
        })
    .catch(
        function(err) {
          onAddIceCandidateError(myPeerConnection, err);
        });

}

// Handle |iceconnectionstatechange| events. This will detect
// when the ICE connection is closed, failed, or disconnected.
//
// Note that currently, the spec is hazy on exactly when this and other
// "connection failure" scenarios should occur, so sometimes they simply
// don't happen.

function handleICEConnectionStateChangeEvent(event) {
  trace("*** ICE connection state changed to " + myPeerConnection.iceConnectionState);

  switch(myPeerConnection.iceConnectionState) {
    case "closed":
    case "failed":
    //case "disconnected": removing this becos some networks might still recover
      updateChat({text: targetUsername + ' disconnected.'});
      closeVideoCall();
      break;
    case "completed":
    //case "connected":    //stated might be connected but might still get better connection. Thos is allow new ice
      peerConnected = true;
      trace('Peer has been connection completed');
    //  myPeerConnection.oniceconnectionstatechange = null; //stop exchanging ice if it is completed.
      break;
  }
}


// Hang up the call by closing our end of the connection, then
// sending a "hang-up" message to the other peer (keep in mind that
// the signaling is done on a different connection). This notifies
// the other peer that the connection should be terminated and the UI
// returned to the "no call in progress" state.

function hangUpCall(event) {
  var msg = {
    name: myUsername,
    target: targetUsername,
    type: "hang-up"
  };
  var callWasInProgress = (callStatus === CALL_IN_PROGRESS);
  callStatus = CLOSING;
  try {
        dataChannel.send(JSON.stringify(msg));
      }catch(e) {
          trace('Error sending msg: ' + e);
          sendToServer(msg);
  };
  closeVideoCall();
  if(callWasInProgress)
    updateChat({text: 'Call ended.'});
  return false;
}

//restart the call
function restartCall(event) {
  try {
      callStatus = RESTARTING;
      connection.close();  //close since this is being reinitialized
  }catch(e){};
  initialize(serverUrl,
                    {
                    'onSignalingOpen' : function() {
                                              hangUpCall();
                                              start(function(){
                                              sendToServer({
                                                name: myUsername,
                                                target: targetUsername,
                                                type: "start-call"
                                              });
                                            });
                                            }
                    }
             );
  updateChat({text: 'Connecting...'});
    return false;
}



function muteOrunmute() {
muteButton = document.getElementById("hangup-button2");
unMuteButton = document.getElementById("unMuteAudio");
    if (localStream.getAudioTracks()[0].enabled == true) {
        console.log("mute")
	localStream.getAudioTracks()[0].enabled = false;
muteButton.style.display = "none";
unMuteButton.style.display = "inline-block";
    }
    else {
	localStream.getAudioTracks()[0].enabled = true;


    }

}
function unMuteAudio(){
unMuteButton = document.getElementById("unMuteAudio");
localStream.getAudioTracks()[0].enabled = true;
unMuteButton.style.display = "none";
muteButton.style.display = "inline-block";

}
function closeVideoCall() {

  trace("Closing the call");

   if(dataChannel) {
        //if(dataChannelID == dataChannel.id)
        dataChannel.close();
        dataChannel = null;
        dataChannelID = null;
   }

  // Close the RTCPeerConnection

  if (myPeerConnection) {
    trace("--> Closing the peer connection");

    // Stop the videos

    if (remoteVideo.srcObject) {
      remoteVideo.srcObject.getTracks().forEach(track => track.stop());
    }

    if (localVideo.srcObject) {
      localVideo.srcObject.getTracks().forEach(track => track.stop());
      videoResolutionSelector.disabled = false;
      document.querySelector('select#codec').disabled = false;
    }

    remoteVideo.src = null;
    localVideo.src = null;

    trace("--> disabling rtc listeners...");

    //disable listeners
    myPeerConnection.onicecandidate = null;
    myPeerConnection.oniceconnectionstatechange = null;
    myPeerConnection.ondatachannel = null;
    myPeerConnection.onaddstream = null;
    // Close the peer connection
    myPeerConnection.close();
    myPeerConnection = null;
    trace('done reseting all');
  }

  peerConnected = false;
  callStatus = NOT_STARTED;
  // Disable the hangup button
  document.getElementById("restart-call-button").disabled = false;
  document.getElementById("hangup-button").disabled = true;
  disableChat();
}