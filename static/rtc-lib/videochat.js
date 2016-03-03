
"use strict";

var myHostname = window.location.hostname;
var myPort = window.location.port
console.log("Hostname: " + myHostname);

//using websockets
var connection = null;

var mediaConstraints = {
  audio: true,            // We want an audio track
  video: true             // ...and we want a video track
};

var myUsername = null;
var targetUsername = null;      // To store username of other peer
var myPeerConnection = null;    // RTCPeerConnection
var clientID = 0;

var remoteVideo = null;
var localVideo = null;
var startTime = null;


var localStream;
var pc1;
var pc2;
var offerOptions = {
  offerToReceiveAudio: 1,
  offerToReceiveVideo: 1
};


var iceServers = [
  {
    urls: 'stun:stun.l.google.com:19302',
  },
  {
	urls:'stun:202.153.34.169:8002?transport=tcp'
  },
//  {
//	urls:'stun:global.stun.twilio.com:3478?transport=udp'
//  },
  {
    urls: 'turn:202.153.34.169:8002?transport=tcp',
    credential: 'dhanush123',
    username: 'dhanush'
  },
//  {
//    urls: 'turn:global.turn.twilio.com:3478?transport=udp',
//    credential: 'lN48+q3dzIvVFTIojLICy53W0lo9vujIoBcLExzS6pI=',
//    username: '70cfe39ec1b0922d41f49812f110383f31c7d0e861b27e40d58e5a1b453f4c01'
//  }
  ];

function getName(pc) {
  return (pc === myPeerConnection) ? myUsername : targetUsername;
}


function sendToServer(msg) {
  var msgJSON = JSON.stringify(msg);

  trace("Sending '" + msg.type + "' message: " + msgJSON);
  connection.send(msgJSON);
}

function broadcastNew(username, notify_peer) {
  if(notify_peer)
    sendToServer({
      name: myUsername,
      date: Date.now(),
      type: "username"
    });
}

function connect(path, username, peer_id, notify_peer) {
  myUsername = username;
  targetUsername = peer_id;
  clientID = myUsername;
  var scheme = "ws";

  // If this is an HTTPS connection, we have to use a secure WebSocket
  // connection too, so add another "s" to the scheme.

  if (document.location.protocol === "https:") {
      scheme += "s";
  }
  var serverUrl = scheme + "://" + myHostname + ':' + myPort + path;

  console.log('using server url: ' + serverUrl);

  connection = new WebSocket(serverUrl);

  connection.onopen = function(event) {
    broadcastNew(username, notify_peer);
    trace('connection opened.');
  };

  connection.onmessage = function(evt) {
    if (document.getElementById("send").disabled) {
      document.getElementById("text").disabled = false;
      document.getElementById("send").disabled = false;
    }
    var text = "";
    var msg = JSON.parse(evt.data);
    trace("Message received: ");
    console.dir(msg);
    var time = new Date(msg.date);
    var timeStr = time.toLocaleTimeString();

    switch(msg.type) {

      case "username":
        text = "<b>User <em>" + msg.name + "</em> signed in at " + timeStr + "</b><br>";
        document.getElementById("welcome").innerHTML = '';
        call(msg.name);
        break;

      case "message":
        text = '<span class="you-msg" style="color: #483D8B;">(' + timeStr + ") <b>" + msg.name + "</b>: " + msg.text + "<br></span>";
        break;

      case "rejectusername":
        myUsername = msg.name;
        text = "<b>Your username has been set to <em>" + myUsername +
          "</em> because the name you chose is in use.</b><br>";
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
        handleNewICECandidateMsg(msg);
        break;

      case "hang-up": // The other peer has hung up the call
        handleHangUpMsg(msg);
        break;

      // Unknown message; output to console for debugging.

      default:
        log_error("Unknown message received:");
        log_error(msg);
    }

    // If there's text to insert into the chat buffer, do so now, then
    // scroll the chat panel so that the new text is visible.

    if (text.length) {
      updateChat(text);
//      document.getElementById("chatbox").contentWindow.scrollByPages(1);
    }
  };

    remoteVideo = document.getElementById("received_video");
    localVideo = document.getElementById("local_video");
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
      // We'll use the first onsize callback as an indication that video has started
      // playing out.
      if (startTime) {
        var elapsedTime = window.performance.now() - startTime;
        trace('Setup time: ' + elapsedTime.toFixed(3) + 'ms');
        startTime = null;
      }
    };

}

function updateChat(text)
{
  var chatPane = document.getElementById("chatbox");
  chatPane.innerHTML = chatPane.innerHTML + '<p class="chat">' + text + '</p>';
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
  sendToServer(msg);
  document.getElementById("text").value = "";
  var time = new Date(msg.date);
  var timeStr = time.toLocaleTimeString();
  var text =  '<span class="me-msg" style="color: #4169E1;">(' + timeStr + ") <b>" + msg.name + "</b>: " + msg.text + "<br></span>";
  if (text.length) {
      updateChat(text);
  }
}

function gotStream(stream) {
  trace('Received local stream');
  localVideo.src = window.URL.createObjectURL(stream);
  localVideo.srcObject = stream;
  localStream = stream;
  trace('done settng stream');
}

function start() {
  trace('Requesting local stream');
  navigator.mediaDevices.getUserMedia(mediaConstraints)
  .then(function(stream) {
      gotStream(stream);
      myPeerConnection = new RTCPeerConnection({
      iceServers: iceServers
      });
      trace('Created local peer connection object myPeerConnection');
      myPeerConnection.onicecandidate = function(e) {
        onIceCandidate(myPeerConnection, e);
      };
      myPeerConnection.oniceconnectionstatechange = function(e) {
        onIceStateChange(myPeerConnection, e);
      };

      myPeerConnection.onaddstream = gotRemoteStream;
  })
  .catch(function(e) {
    alert('getUserMedia() error: ' + e.name);
  });
}

function call() {
//  hangupButton.disabled = false;
  trace('Starting call');
  startTime = window.performance.now();
  var videoTracks = localStream.getVideoTracks();
  var audioTracks = localStream.getAudioTracks();
  if (videoTracks.length > 0) {
    trace('Using video device: ' + videoTracks[0].label);
  }
  if (audioTracks.length > 0) {
    trace('Using audio device: ' + audioTracks[0].label);
  }
  trace('myPeerConnection createOffer start');
  myPeerConnection.createOffer(onCreateOfferSuccess, onCreateSessionDescriptionError,
      offerOptions);
  myPeerConnection.addStream(localStream);
  trace('Added local stream to myPeerConnection');
}

function onCreateSessionDescriptionError(error) {
  trace('Failed to create session description: ' + error.toString());
}


function onCreateOfferSuccess(desc) {
  trace('Offer from myPeerConnection\n' + desc.sdp);
  trace('pc1 setLocalDescription start');
  myPeerConnection.setLocalDescription(desc, function() {
    onSetLocalSuccess(myPeerConnection);
  }, onSetSessionDescriptionError);
  sendToServer({
        name: myUsername,
        target: targetUsername,
        type: "video-offer",
        sdp: desc
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
  trace('pc2 received remote stream');
}


function handleVideoOfferMsg(msg) {
  //hangupButton.disabled = false;
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
  myPeerConnection.setRemoteDescription(desc, function() {
    onSetRemoteSuccess(myPeerConnection);
    trace('myPeerConnection createAnswer start');
      // Since the 'remote' side has no media stream we need
      // to pass in the right constraints in order for it to
      // accept the incoming offer of audio and video.
    myPeerConnection.createAnswer(onCreateAnswerSuccess, onCreateSessionDescriptionError);
  }, onSetSessionDescriptionError);

}

function onCreateAnswerSuccess(desc) {
  trace('Answer from myPeerConnection:\n' + desc.sdp);
  trace('myPeerConnection setLocalDescription start');
  myPeerConnection.setLocalDescription(desc, function() {
    onSetLocalSuccess(myPeerConnection);
  }, onSetSessionDescriptionError);
  // We've configured our end of the call now. Time to send our
  // answer back to the caller so they know that we want to talk
  // and how to talk to us.
  trace("Sending answer packet back to other peer");
  sendToServer({
      name: myUsername,
      target: targetUsername,
      type: "video-answer",
      sdp: desc
    });
  myPeerConnection.addStream(localStream);
}

function handleVideoAnswerMsg(msg) {
  var desc = new RTCSessionDescription(msg.sdp);
  trace('myPeerConnection setRemoteDescription start');
  myPeerConnection.setRemoteDescription(desc, function() {
    onSetRemoteSuccess(myPeerConnection);
  }, onSetSessionDescriptionError);
}

function onIceCandidate(pc, event) {
  if (event.candidate) {
    sendToServer({
      type: "new-ice-candidate",
      target: targetUsername,
      candidate: event.candidate
    });
    trace(getName(pc) + ' ICE candidate: \n' + event.candidate.candidate);
  }
}

function onAddIceCandidateSuccess(pc, event) {
    trace("Outgoing ICE candidate: " + event.candidate);
    sendToServer({
      type: "new-ice-candidate",
      target: targetUsername,
      candidate: event.candidate
    });
  trace(getName(pc) + ' addIceCandidate success');
}

function onAddIceCandidateError(pc, error) {
  trace(getName(pc) + ' failed to add ICE Candidate: ' + error.toString());
}

function onIceStateChange(pc, event) {
  if (pc) {
    trace(getName(pc) + ' ICE state: ' + pc.iceConnectionState);
    console.log('ICE state change event: ', event);
  }
}

function handleHangUpMsg(msg) {
  trace("*** Received hang up notification from other peer");

  closeVideoCall();
}

// A new ICE candidate has been received from the other peer. Call
// RTCPeerConnection.addIceCandidate() to send it along to the
// local ICE framework.

function handleNewICECandidateMsg(msg) {
  var candidate = new RTCIceCandidate(msg.candidate);

  trace("Adding received ICE candidate: " + JSON.stringify(candidate));
  myPeerConnection.addIceCandidate(candidate)
    .catch(reportError);
}


function reportError(errMessage) {
  trace("Error " + errMessage.name + ": " + errMessage.message);
}

// Hang up the call by closing our end of the connection, then
// sending a "hang-up" message to the other peer (keep in mind that
// the signaling is done on a different connection). This notifies
// the other peer that the connection should be terminated and the UI
// returned to the "no call in progress" state.

function hangUpCall() {
  closeVideoCall();
  sendToServer({
    name: myUsername,
    target: targetUsername,
    type: "hang-up"
  });
}


function closeVideoCall() {

  trace("Closing the call");

  // Close the RTCPeerConnection

  if (myPeerConnection) {
    trace("--> Closing the peer connection");

    // Stop the videos

    if (remoteVideo.srcObject) {
      remoteVideo.srcObject.getTracks().forEach(track => track.stop());
    }

    if (localVideo.srcObject) {
      localVideo.srcObject.getTracks().forEach(track => track.stop());
    }

    remoteVideo.src = null;
    localVideo.src = null;

    // Close the peer connection

    myPeerConnection.close();
    myPeerConnection = null;
  }

  // Disable the hangup button

  document.getElementById("hangup-button").disabled = true;

  targetUsername = null;
}