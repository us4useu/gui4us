export default function connectToDisplay(container, displayCfg) {
    displayCfg = JSON.parse(displayCfg);
    var config = {
        sdpSemantics: "unified-plan"
    };
    var pc = new RTCPeerConnection(config);

    function negotiate() {
        pc.addTransceiver("video", {direction: "recvonly"});
        pc.createOffer().then((offer) => {
            return pc.setLocalDescription(offer);
        }).then(() => {
            // wait for ICE gathering to complete
            return new Promise((resolve) => {
                if (pc.iceGatheringState === "complete") {
                    resolve();
                } else {
                    const checkState = () => {
                        if (pc.iceGatheringState === "complete") {
                            pc.removeEventListener("icegatheringstatechange", checkState);
                            resolve();
                        }
                    };
                    pc.addEventListener("icegatheringstatechange", checkState);
                }
            });
        }).then(() => {
            var offer = pc.localDescription;
            return fetch(`${displayCfg.sessionURL}/offer`, {
                body: JSON.stringify({
                    sdp: offer.sdp,
                    type: offer.type,
                }),
                headers: {
                    "Content-Type": "application/json"
                },
                method: "POST"
            });
        }).then((response) => {
            return response.json();
        }).then((answer) => {
            return pc.setRemoteDescription(answer);
        }).catch((e) => {
            alert(e);
        });
    }

    pc.addEventListener("track", (evt) => {
        container.srcObject = evt.streams[0];
    });
    // negotiate communication
    negotiate();
}

