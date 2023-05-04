from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gpt import process_pdf

app = FastAPI()
# CORSを回避するための設定(ホストが違ってもアクセスを許可する)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestData(BaseModel):
    chattext: str

@app.post("/api/users")
async def create_user(requestdata: RequestData):
    return {"chattext": requestdata.chattext}

# ファイルをアップロードするAPI
@app.post("/files/")
async def create_file(file: UploadFile = File(...)):
    file_data = await file.read()
    # file_dataには、アップロードされたPDFファイルのバイナリデータが含まれます
    file_path = f"upload/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file_data)
    output_file = process_pdf(file_path)
    # return {"filename": file.filename}
    return FileResponse(output_file)