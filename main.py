import asyncio
import json
import re
import struct
from datetime import datetime
from uuid import uuid4

import websockets

SUB_KEY = "<API KEY>"


def bytes_from_file(filename, chunksize=8192):
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                yield chunk
            else:
                break


def extract_json_body(response):
    pattern = "^\r\n"  # header separator is an empty line
    m = re.search(pattern, response, re.M)
    return json.loads(response[m.end():])  # assuming that content type is json


def build_message(req_id, payload):
    message = b""
    timestamp = datetime.utcnow().isoformat()
    header = f"X-RequestId: {req_id}\r\nX-Timestamp: {timestamp}Z\r\n" \
             f"Path: audio\r\nContent-Type: audio/x-wav\r\n\r\n"
    message += struct.pack(">H", len(header))
    message += header.encode()
    message += payload
    return message


async def send_file(websocket, filename):
    req_id = uuid4().hex
    for payload in bytes_from_file(filename):
        message = build_message(req_id, payload)
        await websocket.send(message)


async def handler(filename):
    conn_id = uuid4().hex
    url = f"wss://speech.platform.bing.com/speech/recognition/dictation/cognitiveservices/v1?" \
          f"language=nl-NL&Ocp-Apim-Subscription-Key={SUB_KEY}&X-ConnectionId={conn_id}&format=detailed"
    try:
        async with websockets.connect(url) as websocket:
            await send_file(websocket, filename)
            while True:
                response = await websocket.recv()
                content = extract_json_body(response)
                if "RecognitionStatus" in content and content["RecognitionStatus"] == "Success":
                    if("NBest" in content):
                        print("Text: ", content["NBest"][0]["Display"])
                        print("Confidence: ", content["NBest"][0]["Confidence"])
                        print("=====")
                if "RecognitionStatus" in content and content["RecognitionStatus"] == "EndOfDictation":
                    break
    except ConnectionResetError:
        pass


asyncio.get_event_loop().run_until_complete(handler("<Audio file>"))
