"""
Thonburian TTS - FastAPI REST API
ให้บริการ Thai Text-to-Speech ผ่าน REST API สำหรับใช้กับ n8n
"""

import os
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ============================
# Directories
# ============================
OUTPUT_DIR = Path("/app/outputs")
REF_DIR = Path("/app/ref_samples")
TEMP_DIR = Path("/app/temp")
MODEL_CACHE = Path("/app/models_cache")

for d in [OUTPUT_DIR, REF_DIR, TEMP_DIR, MODEL_CACHE]:
    d.mkdir(parents=True, exist_ok=True)

# ============================
# Global pipeline (โหลดครั้งเดียว)
# ============================
tts_pipeline = None
DEFAULT_REF_VOICE = None
DEFAULT_REF_TEXT = None

def load_pipeline():
    """โหลด TTS Pipeline ตอน startup"""
    global tts_pipeline, DEFAULT_REF_VOICE, DEFAULT_REF_TEXT
    try:
        from flowtts.inference import FlowTTSPipeline, ModelConfig, AudioConfig
        from cached_path import cached_path

        logger.info("🔄 กำลังโหลด Thonburian TTS model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"📱 ใช้ Device: {device}")

        model_config = ModelConfig(
            language="th",
            model_type="F5",
            checkpoint="hf://biodatlab/ThonburianTTS/megaF5/mega_f5_last.safetensors",
            vocab_file="hf://biodatlab/ThonburianTTS/megaF5/mega_vocab.txt",
            vocoder="vocos",
            device=device
        )

        audio_config = AudioConfig(
            silence_threshold=-45,
            cfg_strength=2.5,
            speed=1.0,
            nfe_step=32,
            target_rms=0.1,
            cross_fade_duration=0.15,
            min_silence_len=500,
            keep_silence=200,
        )

        tts_pipeline = FlowTTSPipeline(
            model_config=model_config,
            audio_config=audio_config,
            temp_dir=str(TEMP_DIR)
        )

        # โหลด default reference voice
        logger.info("🎵 กำลังโหลด reference voice เริ่มต้น...")
        default_ref_path = REF_DIR / "default_ref.wav"
        if not default_ref_path.exists():
            # ลอง path ต่างๆ จาก HuggingFace
            ref_hf_paths = [
                "hf://ThuraAung1601/E2-F5-TTS/ref_samples/ref_sample.wav",
                "hf://biodatlab/ThonburianTTS/megaF5/ref_sample.wav",
            ]
            loaded = False
            for hf_path in ref_hf_paths:
                try:
                    import shutil
                    ref_hf_path = cached_path(hf_path)
                    shutil.copy(ref_hf_path, default_ref_path)
                    loaded = True
                    logger.info(f"✅ โหลด ref voice จาก: {hf_path}")
                    break
                except Exception as ref_e:
                    logger.warning(f"⚠️ ไม่พบ ref voice ที่ {hf_path}: {ref_e}")
            if not loaded:
                logger.warning("⚠️ ไม่มี default reference voice — จะต้องอัปโหลด ref audio ทุกครั้ง")
        
        if default_ref_path.exists():
            DEFAULT_REF_VOICE = str(default_ref_path)
            DEFAULT_REF_TEXT = "ยินดีที่ได้รู้จัก"
        else:
            DEFAULT_REF_VOICE = None
            DEFAULT_REF_TEXT = None
        logger.info("✅ โหลด Thonburian TTS สำเร็จ!")

    except Exception as e:
        logger.error(f"❌ ไม่สามารถโหลด TTS model: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """โหลด model ตอน startup"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, load_pipeline)
    yield
    logger.info("🛑 Shutting down TTS service...")


# ============================
# FastAPI App
# ============================
app = FastAPI(
    title="🔊 Thonburian TTS API",
    description="Thai Text-to-Speech API based on Thonburian TTS (F5-TTS) — for n8n integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================
# Pydantic Models
# ============================
class TTSRequest(BaseModel):
    text: str
    ref_text: Optional[str] = None
    speed: Optional[float] = 1.0
    cfg_strength: Optional[float] = 2.5
    output_format: Optional[str] = "wav"  # wav หรือ mp3

class TTSResponse(BaseModel):
    success: bool
    file_id: str
    download_url: str
    message: str


# ============================
# Utility Functions
# ============================
def cleanup_old_files():
    """ลบไฟล์ output เก่ากว่า 1 ชั่วโมง"""
    import time
    now = time.time()
    for f in OUTPUT_DIR.glob("*.wav"):
        if now - f.stat().st_mtime > 3600:
            f.unlink()
    for f in OUTPUT_DIR.glob("*.mp3"):
        if now - f.stat().st_mtime > 3600:
            f.unlink()


def convert_to_mp3(wav_path: str) -> str:
    """แปลง WAV เป็น MP3"""
    from pydub import AudioSegment
    mp3_path = wav_path.replace(".wav", ".mp3")
    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3", bitrate="128k")
    return mp3_path


# ============================
# API Endpoints
# ============================

@app.get("/health", tags=["System"])
async def health_check():
    """ตรวจสอบสถานะ API"""
    return {
        "status": "ok",
        "model_loaded": tts_pipeline is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "version": "1.0.0"
    }


@app.get("/", tags=["System"])
async def root():
    """หน้าแรก"""
    return {
        "service": "Thonburian TTS API",
        "description": "Thai Text-to-Speech powered by F5-TTS",
        "docs": "/docs",
        "endpoints": {
            "POST /tts": "สร้างเสียงพูด (text-only, ใช้ default voice)",
            "POST /tts/clone": "สร้างเสียงพูดพร้อม voice cloning (upload ref audio)",
            "GET /audio/{file_id}": "ดาวน์โหลดไฟล์เสียง",
            "DELETE /audio/{file_id}": "ลบไฟล์เสียง",
        }
    }


@app.post("/tts", response_model=TTSResponse, tags=["TTS"])
async def text_to_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    สร้างเสียงพูดภาษาไทย (ใช้ default reference voice)
    
    - **text**: ข้อความภาษาไทยที่ต้องการแปลงเป็นเสียง
    - **ref_text**: transcript ของ reference voice (optional)
    - **speed**: ความเร็วในการพูด (0.5 - 2.0, default=1.0)
    - **cfg_strength**: ความแรงของ classifier-free guidance (default=2.5)
    - **output_format**: รูปแบบไฟล์ (wav หรือ mp3)
    """
    if tts_pipeline is None:
        raise HTTPException(status_code=503, detail="TTS model ยังไม่พร้อม กรุณารอสักครู่")

    if DEFAULT_REF_VOICE is None:
        raise HTTPException(
            status_code=400,
            detail="ไม่มี default reference voice กรุณาใช้ endpoint /tts/clone พร้อมอัปโหลดไฟล์เสียง reference"
        )

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุข้อความ")

    if len(request.text) > 5000:
        raise HTTPException(status_code=400, detail="ข้อความยาวเกินไป (สูงสุด 5000 ตัวอักษร)")

    file_id = str(uuid.uuid4())
    wav_path = str(OUTPUT_DIR / f"{file_id}.wav")

    try:
        logger.info(f"🎤 กำลังสร้างเสียง: '{request.text[:50]}...'")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: tts_pipeline(
                text=request.text,
                ref_voice=DEFAULT_REF_VOICE,
                ref_text=request.ref_text or DEFAULT_REF_TEXT,
                output_file=wav_path,
                speed=request.speed or 1.0,
            )
        )

        output_path = wav_path
        output_ext = "wav"

        if request.output_format == "mp3":
            output_path = await asyncio.get_event_loop().run_in_executor(
                None, convert_to_mp3, wav_path
            )
            output_ext = "mp3"
            file_id_out = f"{file_id}.mp3"
        else:
            file_id_out = f"{file_id}.wav"

        background_tasks.add_task(cleanup_old_files)

        logger.info(f"✅ สร้างเสียงสำเร็จ: {file_id_out}")
        return TTSResponse(
            success=True,
            file_id=file_id_out,
            download_url=f"/audio/{file_id_out}",
            message="สร้างเสียงสำเร็จ"
        )

    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาด: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสร้างเสียง: {str(e)}")


@app.post("/tts/clone", tags=["TTS"])
async def tts_with_voice_clone(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="ข้อความภาษาไทย"),
    ref_text: Optional[str] = Form(None, description="transcript ของ reference audio"),
    speed: Optional[float] = Form(1.0, description="ความเร็ว (0.5-2.0)"),
    output_format: Optional[str] = Form("wav", description="รูปแบบ: wav หรือ mp3"),
    ref_audio: UploadFile = File(..., description="ไฟล์เสียง reference (WAV/MP3, 3-15 วินาที)"),
):
    """
    สร้างเสียงพูดพร้อม Voice Cloning
    
    อัปโหลดไฟล์เสียง reference เพื่อ clone เสียงนั้นมาพูดข้อความที่ต้องการ
    """
    if tts_pipeline is None:
        raise HTTPException(status_code=503, detail="TTS model ยังไม่พร้อม กรุณารอสักครู่")

    if not text.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุข้อความ")

    # ตรวจสอบนามสกุลไฟล์
    allowed_exts = {".wav", ".mp3", ".ogg", ".flac"}
    ext = Path(ref_audio.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"ไฟล์ต้องเป็น {allowed_exts}")

    file_id = str(uuid.uuid4())
    ref_path = str(REF_DIR / f"ref_{file_id}{ext}")
    wav_path = str(OUTPUT_DIR / f"{file_id}.wav")

    try:
        # บันทึก reference audio
        content = await ref_audio.read()
        with open(ref_path, "wb") as f:
            f.write(content)

        # ถ้าไม่มี ref_text ให้ใช้ Whisper ASR ถอดเสียงอัตโนมัติ
        actual_ref_text = ref_text
        if not actual_ref_text:
            logger.info("🎙 กำลังถอดเสียง reference ด้วย Whisper ASR...")
            from transformers import pipeline as hf_pipeline
            device = 0 if torch.cuda.is_available() else "cpu"
            asr_pipe = hf_pipeline(
                task="automatic-speech-recognition",
                model="biodatlab/whisper-th-medium-combined",
                chunk_length_s=30,
                device=device,
            )
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: asr_pipe(ref_path, generate_kwargs={"language": "<|th|>", "task": "transcribe"}, batch_size=8)
            )
            actual_ref_text = result["text"]
            logger.info(f"📝 ASR ได้ข้อความ: {actual_ref_text}")

        logger.info(f"🎤 กำลัง clone เสียงและสร้าง: '{text[:50]}...'")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: tts_pipeline(
                text=text,
                ref_voice=ref_path,
                ref_text=actual_ref_text,
                output_file=wav_path,
                speed=speed or 1.0,
            )
        )

        output_path = wav_path
        if output_format == "mp3":
            output_path = await asyncio.get_event_loop().run_in_executor(
                None, convert_to_mp3, wav_path
            )
            file_id_out = f"{file_id}.mp3"
        else:
            file_id_out = f"{file_id}.wav"

        # ลบไฟล์ ref ชั่วคราว
        background_tasks.add_task(lambda: Path(ref_path).unlink(missing_ok=True))
        background_tasks.add_task(cleanup_old_files)

        logger.info(f"✅ Voice cloning สำเร็จ: {file_id_out}")
        return {
            "success": True,
            "file_id": file_id_out,
            "download_url": f"/audio/{file_id_out}",
            "ref_text_used": actual_ref_text,
            "message": "Voice cloning สำเร็จ"
        }

    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาด: {e}")
        # ลบไฟล์ชั่วคราว
        Path(ref_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


@app.get("/audio/{file_id}", tags=["Files"])
async def download_audio(file_id: str):
    """
    ดาวน์โหลดไฟล์เสียงที่สร้างแล้ว
    
    - **file_id**: ชื่อไฟล์ที่ได้รับจาก /tts หรือ /tts/clone
    """
    # ป้องกัน path traversal
    if ".." in file_id or "/" in file_id:
        raise HTTPException(status_code=400, detail="file_id ไม่ถูกต้อง")

    file_path = OUTPUT_DIR / file_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์เสียง (อาจถูกลบอัตโนมัติแล้ว)")

    media_type = "audio/mpeg" if file_id.endswith(".mp3") else "audio/wav"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_id
    )


@app.delete("/audio/{file_id}", tags=["Files"])
async def delete_audio(file_id: str):
    """ลบไฟล์เสียง"""
    if ".." in file_id or "/" in file_id:
        raise HTTPException(status_code=400, detail="file_id ไม่ถูกต้อง")

    file_path = OUTPUT_DIR / file_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์เสียง")

    file_path.unlink()
    return {"success": True, "message": f"ลบไฟล์ {file_id} สำเร็จ"}


@app.get("/status", tags=["System"])
async def get_status():
    """สถานะโดยละเอียด"""
    output_files = list(OUTPUT_DIR.glob("*.wav")) + list(OUTPUT_DIR.glob("*.mp3"))
    return {
        "status": "running",
        "model_loaded": tts_pipeline is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "cuda_available": torch.cuda.is_available(),
        "output_files_count": len(output_files),
        "default_ref_voice": DEFAULT_REF_VOICE is not None,
    }
