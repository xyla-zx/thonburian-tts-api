# 🔊 Thonburian TTS API (Standalone)

Thai Text-to-Speech API ที่สร้างจาก [Thonburian TTS](https://github.com/biodatlab/thonburian-tts) (F5-TTS) พร้อม REST API สำเร็จรูปสำหรับการเชื่อมต่อกับระบบภายนอก เช่น n8n, Make.com, หรือแอปพลิเคชันของคุณเอง

## 🌟 จุดเด่น
- 🐳 **พร้อมใช้งานบน Docker:** แค่รัน `docker compose up -d`
- ⚡ **REST API:** ใช้งานผ่าน FastAPI ที่มีโครงสร้างเรียบง่าย
- 👥 **Voice Cloning:** รองรับการทำโคลนเสียงคนพูด (แค่มีไฟล์เสียงต้นฉบับ 3-15 วินาที)
- 📝 **รองรับข้อความยาว:** ประมวลผลข้อความได้สูงสุด 5,000 ตัวอักษรต่อครั้ง
- 🚀 **CPU & GPU Support:** ทำงานได้ทั้งเครื่องธรรมดา และเครื่องที่มี NVIDIA GPU

---

## 🚀 วิธีติดตั้ง (แบบทั่วไป)

หากคุณ Clone Repository นี้มา ให้ใช้คำสั่งต่อไปนี้เพื่อรันระบบ:

```bash
# Build image (ครั้งแรกจะใช้เวลา 5-10 นาที เพราะต้องรวบรวม Dependencies)
docker compose build

# Start service
docker compose up -d

# ดู Logs
docker compose logs -f
```

## 🌐 ทดสอบการทำงาน

- เช็คสถานะ API: `http://localhost:8000/health`
- ดู API Docs (Swagger): `http://localhost:8000/docs`

---

## ☁️ การนำขึ้น Docker Hub (สำหรับใช้งานหลายเครื่อง)

ถ้าคุณต้องการเอา Image ไปใช้เครื่องอื่นๆ โดยไม่ต้องมานั่ง Build ใหม่ให้เสียเวลา สามารถทำตามขั้นตอนนี้ได้เลยครับ:

### 1. ล็อกอินเข้า Docker Hub ใน Terminal
```bash
docker login
# ใส่ Username และ Password ของ Docker Hub ของคุณ
```

### 2. Tag Image
สมมติว่าคุณมี Image ชื่อ `thonburian-tts:latest` และ Username ใน Docker Hub ของคุณคือ `myusername`
```bash
docker tag thonburian-tts:latest myusername/thonburian-tts:latest
```

### 3. Push Image ขึ้น Docker Hub
```bash
docker push myusername/thonburian-tts:latest
```

### 4. วิธีนำไปรันที่เครื่องอื่น
ในเครื่องใหม่ คุณไม่ต้องเอาไฟล์โค้ดไปเลย เพียงแค่สร้างไฟล์ `docker-compose.yml` สั้นๆ แบบนี้:

```yaml
services:
  thonburian-tts:
    image: myusername/thonburian-tts:latest # ใส่ชื่อ Image ของคุณ
    container_name: thonburian-tts
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - tts_outputs:/app/outputs
      - tts_models:/app/models_cache
      - tts_refs:/app/ref_samples
    environment:
      - HF_HOME=/app/models_cache

volumes:
  tts_outputs:
  tts_models:
  tts_refs:
```
แล้วรันคำสั่ง `docker compose up -d` ระบบจะไปดึง Image จาก Docker Hub มาให้ทันทีครับ

---

## 📡 API Endpoints 

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/health` | ตรวจสอบสถานะว่าระบบและ Model พร้อมทำงานหรือไม่ |
| GET | `/status` | เช็คสถานะโดยละเอียด (ไฟล์ค้าง, การ์ดจอ ฯลฯ) |
| POST | `/tts` | ส่งข้อความไปสร้างเสียง (รูปแบบ JSON) |
| POST | `/tts/clone` | ส่งข้อความ + อัพโหลดไฟล์เสียงตัวอย่าง (Multipart Form) |
| GET | `/audio/{file_id}` | ดาวน์โหลดไฟล์เสียง |
| DELETE | `/audio/{file_id}` | ลบไฟล์เสียงออกจากระบบ |

*หมายเหตุ: ไฟล์เสียงที่สร้างจะถูกตั้งเวลาเคลียร์ทิ้งอัตโนมัติหากเกิน 1 ชั่วโมง*

---

## 💡 โครงสร้างไฟล์ใน Repository นี้
```
.
├── Dockerfile              # คำสั่งแพ็คแอปพลิเคชันเป็น Image
├── docker-compose.yml      # สำหรับ Start API แบบ Standalone
├── api.py                  # Source Code หลักของ FastAPI
├── requirements.txt        # ไฟล์ระบุ Dependencies (รวมการล็อคเวอร์ชั่นของ PyTorch เพื่อกัน Error)
└── .dockerignore           # ไฟล์ที่ไม่ต้องการเอาเข้า Image
```

---

## ⚙️ การตั้งค่า GPU (ถ้าเครื่องมี NVIDIA GPU)

เอาเครื่องหมาย `#` ออกในบรรทัดเหล่านี้ของ `docker-compose.yml`:
```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```
