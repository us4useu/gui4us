import vtkWSLinkClient from '@kitware/vtk.js/IO/Core/WSLinkClient';
import SmartConnect from 'wslink/src/SmartConnect';
import vtkRemoteView from '@kitware/vtk.js/Rendering/Misc/RemoteView';

function connectToDisplay(container, config) {
    // TODO is the below necessary?
    vtkWSLinkClient.setSmartConnectClass(SmartConnect);
    const client = vtkWSLinkClient.newInstance();

    // Error
    client.onConnectionError((httpReq) => {
        const message =
            (httpReq && httpReq.response && httpReq.response.error) ||
            "Connection error";
        console.error(message);
        console.log(httpReq);
    });

    // Close
    client.onConnectionClose((httpReq) => {
        const message =
            (httpReq && httpReq.response && httpReq.response.error) ||
            "Connection close";
        console.error(message);
        console.log(httpReq);
    });


    // Connect
    client
        .connect(config)
        .then((validClient) => {
            const viewStream = client.getImageStream().createViewStream('-1');

            const view = vtkRemoteView.newInstance({
                viewStream,
            });
            const session = validClient.getConnection().getSession();
            view.setSession(session);
            view.setContainer(container);
            // the scaled image compared to the clients view resolution
            view.setInteractiveRatio(0.2);
            // jpeg quality
            view.setInteractiveQuality(10);
            // TODO event listener on container resize?
            window.addEventListener('resize', view.resize);
        })
        .catch((error) => {
            console.error(error);
        });

}

