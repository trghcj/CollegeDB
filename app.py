import os
import shutil
import zipfile
import asyncio
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Make sure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables for state
is_running = False
log_queue = asyncio.Queue()

async def run_scraper():
    global is_running
    is_running = True
    # Clear old files
    for f in ['engineering_colleges.csv', 'failed.csv', 'logs/scraper.log']:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
    if os.path.exists('logos'):
        try: shutil.rmtree('logos')
        except: pass
    
    await log_queue.put("Starting scraper pipeline...")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = await asyncio.create_subprocess_exec(
        "python", "build_dataset.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env
    )

    buffer = bytearray()
    while True:
        char = await process.stdout.read(1)
        if not char:
            if buffer:
                text = buffer.decode('utf-8', errors='replace').strip()
                if text:
                    await log_queue.put(text)
            break
            
        buffer.extend(char)
        if char == b'\n' or char == b'\r':
            text = buffer.decode('utf-8', errors='replace').strip()
            buffer.clear()
            if text:
                if char == b'\r':
                    text = '\r' + text
                await log_queue.put(text)
            
    await process.wait()
    await log_queue.put(f"Process exited with code {process.returncode}")
    await log_queue.put("DONE")
    is_running = False

@app.get("/")
async def get_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    global is_running
    if is_running:
        return {"error": "A job is already running"}
    
    # Save uploaded file as colleges.csv
    with open("colleges.csv", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Drain the log queue
    while not log_queue.empty():
        try: log_queue.get_nowait()
        except: pass
        
    background_tasks.add_task(run_scraper)
    return {"status": "started"}

async def log_generator():
    while True:
        msg = await log_queue.get()
        yield f"data: {msg}\n\n"
        if msg == "DONE":
            break

@app.get("/stream")
async def stream_logs():
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/download")
async def download_results():
    zip_filename = "Dataset_Results.zip"
    
    # Zip up the results
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists('engineering_colleges.csv'):
            zipf.write('engineering_colleges.csv')
        if os.path.exists('failed.csv'):
            zipf.write('failed.csv')
        if os.path.exists('logos'):
            for root, dirs, files in os.walk('logos'):
                for file in files:
                    zipf.write(os.path.join(root, file))
                    
    return FileResponse(zip_filename, media_type='application/zip', filename=zip_filename)
