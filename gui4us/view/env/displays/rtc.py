from aiohttp import web
import asyncio
import os
import json
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from gui4us.logging import get_logger
import queue


class VideoTrack(VideoStreamTrack):
    def __init__(self, input_queue):
        super().__init__()
        self.counter = 0
        self.input_queue = input_queue

    async def recv(self):
        """
        Time-critical part (consider moving to a separate process?)
        TODO consider sending non-rgb values
        """
        pts, time_base = await self.next_timestamp()
        img = self.input_queue.get()
        frame = VideoFrame.from_ndarray(img, format="bgr24")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class RTCServer:

    def __init__(self, host, port, input_queue):
        self.logger = get_logger(f"{type(self)}:{host}:{port}")
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.on_shutdown.append(self.on_shutdown)
        # self.app.router.add_get("/client.js", javascript)
        self.app.router.add_post("/offer", self.offer)
        # TODO SSL certificate
        self.pcs = set()
        self.input_queue = input_queue

    def start(self):
        web.run_app(self.app, host=self.host, port=self.port, ssl_context=None)

    def send(self, data):
        try:
            self.input_queue.put_nowait(data)
        except queue.Full:
            pass

    async def on_shutdown(self, app):
        # close peer connections
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()

    # async def javascript(self, request):
    #     content = open(os.path.join(ROOT, "client.js"), "r").read()
    #     return web.Response(content_type="application/javascript", text=content)

    async def offer(self, request):
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is %s" % pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        video_track = VideoTrack(self.input_queue)
        video_sender = pc.addTrack(video_track)
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": pc.localDescription.sdp,
                 "type": pc.localDescription.type}
            ),
        )











