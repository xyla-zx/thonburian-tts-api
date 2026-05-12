# Thonburian TTS - Docker Image
# ใช้ Python 3.10 slim เป็น base image (ลดขนาด image)
FROM python:3.10-slim

# ติดตั้ง system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ตั้ง working directory
WORKDIR /app

# ติดตั้ง Python dependencies (pin versions ที่ compatible)
# torch CPU-only + versions ที่ทำงานกับ flowtts ได้
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "torch==2.3.1" \
        "torchaudio==2.3.1" \
        "torchvision==0.18.1" \
        --index-url https://download.pytorch.org/whl/cpu

# ติดตั้ง transformers เวอร์ชัน stable ที่ compatible
RUN pip install --no-cache-dir \
        "transformers==4.44.2" \
        "huggingface-hub>=0.24.0" \
        "tokenizers>=0.19.0"

# Clone และติดตั้ง thonburian-tts แบบ full (รวม flowtts package)
RUN git clone https://github.com/biodatlab/thonburian-tts.git /tmp/thonburian-tts && \
    cd /tmp/thonburian-tts && \
    pip install --no-cache-dir -e . --no-deps && \
    cp -r flowtts /app/ && \
    cd / && rm -rf /tmp/thonburian-tts

# ติดตั้ง remaining dependencies (ยกเว้น torch/transformers ที่ pin ไว้แล้ว)
RUN pip install --no-cache-dir \
    cached-path \
    f5-tts \
    librosa \
    soundfile \
    pydub \
    vocos \
    pythainlp \
    numpy \
    scipy \
    accelerate \
    safetensors

# ติดตั้ง FastAPI และ dependencies สำหรับ API
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "python-multipart>=0.0.9" \
    "aiofiles>=23.0.0"

# Copy source code ทั้งหมด
COPY . .

# สร้าง directories สำหรับเก็บไฟล์
RUN mkdir -p /app/outputs /app/ref_samples /app/temp /app/models_cache

# ทดสอบ import สำคัญ
RUN python -c "from flowtts.inference import FlowTTSPipeline, ModelConfig, AudioConfig; print('✅ flowtts import OK')"

# ตั้ง environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models_cache
ENV TORCH_HOME=/app/models_cache
ENV TRANSFORMERS_CACHE=/app/models_cache

# เปิด port 8000 สำหรับ FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=60s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# รัน FastAPI server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
