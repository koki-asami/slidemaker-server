from typing import List
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gpt import process_pdf
import json
import os
import re
import openai
import asyncio

os.environ["OPENAI_API_KEY"]=""
openai.api_key = ""

app = FastAPI()
# CORSを回避するための設定(ホストが違ってもアクセスを許可する)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

class RequestData(BaseModel):
    chattext: str

@app.post("/api/users")
async def create_user(requestdata: RequestData):
    return {"chattext": requestdata.chattext}

@app.get("/files/")
async def get_file(file_path:str):
    output_file = process_pdf(file_path)
    # return {"filename": file.filename}
    return FileResponse(output_file)

# # ファイルをアップロードするAPI
# @app.post("/files/")
# async def create_file(file: UploadFile = File(...)):
#     file_data = await file.read()
#     # file_dataには、アップロードされたPDFファイルのバイナリデータが含まれます
#     file_path = f"upload/{file.filename}"
#     with open(file_path, "wb") as f:
#         f.write(file_data)
#     output_file = process_pdf(file_path)
#     # return {"filename": file.filename}
#     return FileResponse(output_file)


@app.websocket("/ws/chattext/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.websocket("/ws/chat/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    system_prompt = '''
    あなたは熟練のコンサルタントです。あなたが出力したスライドに応じて、ユーザが修正の要望を出すので、要望に合ったMarpで使えるMarkdown形式で修正した結果のみを出力してください。
    Maprのフォーマットは以下の通りです。
    """

    ---
    <!-- スライド n -->
    # { タイトル }

    - { 本文 }
    - { 本文 }
    - { 本文 } 

    """
    
    スライドの修正が完了したら変更分や追加分だけでなく変更を行なっていない部分についても合わせて完全な形式で出力してください。
    '''
    messages = [{"role": "system", "content": system_prompt}]
    while True:
        json_string = await websocket.receive_text()
        data = json.loads(json_string)

        filename = data['filename']
        message = data['message']
        print(message)
        if filename != "":
            file = await websocket.receive_bytes() 
            file_path = f"upload/{filename}"

            with open(file_path, "wb") as f:
                f.write(file)

            output_file, output_message = process_pdf(file_path)
            messages.append({"role": "assistant", "content": output_message})
            with open(output_file, mode="rb") as file:
            # WebSocketを使用してファイルのバイナリデータをストリーミング
                while True:
                    data = file.read(1024)
                    if not data:
                        break
                    await websocket.send_bytes(data)
            await websocket.send_text("file_receive_success")
            await websocket.send_text(json.dumps({"state":"completed", "message":"How do you like it? If you need to modify slide including design, type here:"}))
        
        else:
            # chatgptで手直し            
            messages.append({"role": "user", "content": message})
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                stream=True,
                messages=messages
            )
            answer = []
            for event in response:
                event_text = event['choices'][0]['delta']
                answer.append(event_text.get('content', ''))
                if answer:
                    print("".join(answer))
                    await websocket.send_text(json.dumps({"state":"processing", "message":"".join(answer)}))
                    await asyncio.sleep(0.01)
            await websocket.send_text(json.dumps({"state":"completed", "message":"".join(answer)}))
            messages.append({"role": "assistant", "content": "".join(answer)})

            # output_slide_index = "".join(answer).find("---")
            # output_slide = "".join(answer)[output_slide_index:]
            pattern = r"```(.*?)```"
            output_slide = re.findall(pattern, "".join(answer))
            if len(output_slide):
                output_slide = output_slide[0]
            else:
                output_slide = "".join(answer)
            
            output_slide_index = output_slide.find("---")
            output_slide = output_slide[output_slide_index:]
            output_path = f'download/{(file_path.split("/")[-1]).split("/")[0]}_slide.md'
           
            print(output_path)
            with open(output_path, "w") as file:
                file.write(output_slide)
            
            os.system(f"npx @marp-team/marp-cli@latest {output_path} --pdf -y")
            
            with open(output_file, mode="rb") as file:
            # WebSocketを使用してファイルのバイナリデータをストリーミング
                while True:
                    data = file.read(1024)
                    if not data:
                        break
                    await websocket.send_bytes(data)
            await websocket.send_text("file_receive_success")
