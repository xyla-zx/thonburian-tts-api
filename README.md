# 🔊 Thonburian TTS API (Thai Text-to-Speech) - Docker & FastAPI

[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-Ready-blue?logo=docker)](https://hub.docker.com/r/xylamana/thonburian-tts)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Thonburian TTS API** เป็นระบบแปลงข้อความภาษาไทยเป็นเสียงพูด (Thai Text-to-Speech) คุณภาพสูง ที่พัฒนาต่อยอดมาจากโมเดล [Thonburian TTS (F5-TTS)](https://github.com/biodatlab/thonburian-tts) มาพร้อมกับ **REST API** สำเร็จรูปที่สร้างด้วย **FastAPI** ทำให้สามารถเชื่อมต่อกับระบบภายนอกอื่นๆ เช่น **n8n, Make.com, แชทบอท (Chatbot), หรือแอปพลิเคชันของคุณเอง** ได้อย่างง่ายดาย

## ✨ จุดเด่นและฟีเจอร์ (Features)
- 🇹🇭 **เสียงภาษาไทยธรรมชาติ (Thai TTS):** รองรับการแปลงประโยคภาษาไทยเป็นเสียงพูดที่ลื่นไหล
- 👥 **ระบบโคลนเสียง (Voice Cloning):** สามารถจำลองเสียงคนพูดได้ เพียงแค่อัพโหลดไฟล์เสียงต้นฉบับ 3-15 วินาที
- 🐳 **ติดตั้งง่ายด้วย Docker:** แค่โหลดไฟล์ไปรัน `docker compose up -d` ระบบก็พร้อมใช้งาน ไม่ต้องตั้งค่า Environment ให้ยุ่งยาก
- 📝 **รองรับข้อความยาว:** ประมวลผลข้อความได้สูงสุดถึง **5,000 ตัวอักษร** ต่อหนึ่งครั้ง
- 🚀 **CPU & GPU Support:** ทำงานได้บน Server ทั่วไป (CPU) และเครื่องที่มีการ์ดจอ NVIDIA (GPU) เพื่อเร่งความเร็ว

---

## 🚀 วิธีติดตั้งและใช้งาน (Quick Start via Docker Hub)

ระบบนี้ได้ถูกแพ็คเป็น **Docker Image** และอัพโหลดขึ้น Docker Hub เรียบร้อยแล้ว (ชื่อ Image: `xylamana/thonburian-tts:latest`) คุณสามารถรันระบบได้ทันทีโดยทำตามขั้นตอนต่อไปนี้:

### 1. โหลดไฟล์ docker-compose.yml
สร้างไฟล์ `docker-compose.yml` บน Server ของคุณ และใส่โค้ดด้านล่างนี้:

```yaml
services:
  thonburian-tts:
    image: xylamana/thonburian-tts:latest
    container_name: thonburian-tts
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - tts_outputs:/app/outputs        # สำหรับเก็บไฟล์เสียงที่สร้างเสร็จ
      - tts_models:/app/models_cache    # สำหรับเก็บแคชของ AI Model
      - tts_refs:/app/ref_samples       # สำหรับเก็บไฟล์เสียงตัวอย่าง (Voice Cloning)
    environment:
      - HF_HOME=/app/models_cache

volumes:
  tts_outputs:
  tts_models:
  tts_refs:
```

### 2. รันระบบ (Start the API)
เปิด Terminal ในโฟลเดอร์ที่มีไฟล์ `docker-compose.yml` แล้วพิมพ์คำสั่ง:

```bash
docker compose up -d
```
ระบบจะดึง Image และรัน API ให้คุณโดยอัตโนมัติ!

---

## 🌐 ทดสอบการทำงาน (Testing the API)

หลังจากรัน Container แล้ว ให้เข้าไปที่เบราว์เซอร์:
- **เช็คสถานะระบบ (Health Check):** `http://localhost:8000/health`
- **ดูคู่มือ API Docs (Swagger UI):** `http://localhost:8000/docs`

---

## 📡 สรุป API Endpoints (API Reference)

| HTTP Method | Endpoint | หน้าที่และการใช้งาน |
|-------------|----------|-------------------|
| **GET** | `/health` | ตรวจสอบสถานะว่าระบบและ AI Model โหลดเสร็จพร้อมทำงานหรือยัง |
| **GET** | `/status` | เช็คสถานะโดยละเอียด (จำนวนไฟล์ค้าง, เช็คการ์ดจอ) |
| **POST** | `/tts` | ส่งข้อความไปสร้างเสียง (รูปแบบ JSON Request) |
| **POST** | `/tts/clone` | ส่งข้อความ พร้อมแนบไฟล์เสียงต้นแบบเพื่อจำลองเสียง (Multipart Form) |
| **GET** | `/audio/{file_id}` | ดาวน์โหลดไฟล์เสียง `.wav` หรือ `.mp3` |
| **DELETE**| `/audio/{file_id}` | ลบไฟล์เสียงออกจาก Server ทันที |

*(💡 เกร็ดความรู้: ไฟล์เสียงที่สร้างเสร็จจะถูกระบบตั้งเวลาลบทิ้งอัตโนมัติเมื่ออายุเกิน 1 ชั่วโมง เพื่อประหยัดพื้นที่ Server)*

---

## 💡 โครงสร้างโฟลเดอร์สำหรับนักพัฒนา (For Developers)
หากคุณต้องการ Build โค้ดเอง:
```
.
├── Dockerfile              # คำสั่งแพ็คแอปพลิเคชันเป็น Docker Image
├── docker-compose.yml      # ไฟล์รัน API
├── api.py                  # Source Code หลัก (FastAPI)
├── requirements.txt        # ไฟล์แพ็คเกจ Python
└── .dockerignore           # ไฟล์ตั้งค่าละเว้น
```

---

## ⚙️ การเปิดใช้งานการ์ดจอ (NVIDIA GPU Support)

หาก Server ของคุณมีการ์ดจอ และติดตั้ง **Nvidia Container Toolkit** เรียบร้อยแล้ว ให้เอาเครื่องหมาย `#` ออกในบรรทัดเหล่านี้ของ `docker-compose.yml`:
```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

### 📌 SEO Keywords
`Thai TTS` `Thai Text to Speech` `ระบบแปลงข้อความเป็นเสียงภาษาไทย` `สร้างเสียงภาษาไทย` `Voice Cloning` `โคลนเสียงภาษาไทย` `F5-TTS` `Thonburian TTS` `FastAPI` `Docker` `n8n integration` `Make.com TTS API` `AI สร้างเสียง`
