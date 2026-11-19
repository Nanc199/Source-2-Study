# 🧠 StudyMind AI

**Upload Anything. Learn Everything. Prepare Smarter.**

An AI-powered RAG-based Learning and Exam Preparation Platform that transforms your study materials into summaries, quizzes, flashcards, and a smart duplicate-free question bank.

![Tech Stack](https://img.shields.io/badge/Next.js-14-black) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue) ![Gemini](https://img.shields.io/badge/Google_Gemini-AI-orange)

---

## ✨ Features

### 📤 Multi-Source Upload
Upload PDFs, DOCX, PPTX, Images (OCR), Website URLs, and YouTube videos. All processed and indexed for AI retrieval.

### 💬 AI Chat Assistant (RAG)
Ask questions about your uploaded materials. Get sourced, accurate answers powered by Retrieval-Augmented Generation.

### 📚 Study Material Generator
Auto-generate: Short Summaries, Detailed Summaries, Short Answers, Long Answers, MCQs, Important Questions, Flashcards, Chapter Notes.

### 🔍 Smart Duplicate Question Detection (Signature Feature)
Upload multiple question papers → AI detects semantically equivalent questions → Get one consolidated document with zero repeats.

- Semantic similarity using sentence-transformer embeddings
- LLM verification for ambiguous matches
- Frequency analysis and year-wise tracking
- Export consolidated question bank as PDF/DOCX/TXT

### 📝 Interactive Quizzes
AI-generated quizzes with timer, difficulty levels, MCQ/True-False, instant scoring, and detailed explanations.

### 🃏 Flashcards
Interactive flip cards for quick revision with favorites support.

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 14 + TypeScript |
| UI | Tailwind CSS + Lucide Icons |
| Backend | Python FastAPI |
| Database | SQLite (SQLAlchemy) |
| Vector DB | ChromaDB |
| AI Model | Google Gemini API |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| RAG | ChromaDB + Gemini |
| OCR | Tesseract |
| PDF Processing | PyMuPDF |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or pnpm

### 1. Clone and Setup

```bash
cd RS
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Configure API Key

Edit `backend/.env` and add your Google Gemini API key:
```
GCP_API_KEY=YOUR_GCP_API_KEY
```

Get your API key from: https://makersuite.google.com/app/apikey

### 4. Start Backend

```bash
cd backend
python main.py
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at: http://localhost:3000

### 6. Start Using

1. Open http://localhost:3000
2. Create an account (Sign Up)
3. Create a Collection (e.g., "Artificial Intelligence")
4. Upload study materials (PDFs, DOCX, PPTX, etc.)
5. Wait for processing to complete
6. Use AI Chat, Study Generator, Quiz, or Duplicate Detector!

---

## 📁 Project Structure

```
RS/
├── .env.example              # Environment variables template
├── README.md                 # This file
├── backend/                  # Python FastAPI Backend
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings/configuration
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # JWT authentication
│   ├── requirements.txt     # Python dependencies
│   ├── routers/             # API route handlers
│   │   ├── auth_router.py
│   │   ├── collections_router.py
│   │   ├── sources_router.py
│   │   ├── chat_router.py
│   │   ├── study_router.py
│   │   ├── questions_router.py
│   │   ├── quiz_router.py
│   │   ├── dashboard_router.py
│   │   └── export_router.py
│   └── services/            # Business logic
│       ├── document_processor.py  # File extraction
│       ├── rag_service.py         # RAG + Gemini
│       ├── duplicate_detector.py  # Duplicate detection
│       ├── quiz_service.py        # Quiz generation
│       └── export_service.py      # PDF/DOCX/TXT export
└── frontend/                 # Next.js Frontend
    ├── package.json
    ├── tailwind.config.ts
    └── src/
        ├── app/             # Pages (App Router)
        │   ├── page.tsx     # Landing page
        │   ├── login/
        │   ├── signup/
        │   ├── dashboard/
        │   ├── collections/
        │   ├── chat/
        │   ├── study-generator/
        │   ├── duplicate-detector/
        │   ├── quiz/
        │   ├── flashcards/
        │   ├── question-bank/
        │   └── settings/
        ├── components/      # Reusable components
        ├── contexts/        # Auth context
        └── lib/             # API client
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Get profile |
| GET/POST | `/api/collections` | List/Create collections |
| GET/PUT/DELETE | `/api/collections/{id}` | Collection CRUD |
| POST | `/api/collections/{id}/sources/upload` | Upload files |
| POST | `/api/collections/{id}/sources/url` | Add URL |
| POST | `/api/collections/{id}/sources/youtube` | Add YouTube |
| POST | `/api/collections/{id}/chat/sessions` | Create chat |
| POST | `/api/chat/sessions/{id}/messages` | Send message |
| POST | `/api/collections/{id}/generate` | Generate study material |
| POST | `/api/collections/{id}/detect-duplicates` | Detect duplicates |
| GET | `/api/collections/{id}/duplicate-groups` | Get groups |
| POST | `/api/collections/{id}/quiz/generate` | Generate quiz |
| POST | `/api/quiz/submit` | Submit quiz |
| POST | `/api/export/pdf` | Export as PDF |
| GET | `/api/dashboard/stats` | Dashboard stats |

Full API docs available at `http://localhost:8000/docs` (Swagger UI)

---

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection | `sqlite:///./studymind.db` |
| `SECRET_KEY` | JWT signing key | Auto-generated |
| `GEMINI_API_KEY` | Google Gemini API key | Required for AI |
| `UPLOAD_DIR` | File upload directory | `./uploads` |
| `CHROMA_DIR` | ChromaDB storage | `./chroma_db` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `SIMILARITY_THRESHOLD` | Duplicate detection threshold | `0.85` |

---

## 🧪 Notes

- **Without GEMINI_API_KEY**: The app runs fully, but AI features (chat, generation, quiz, duplicate verification) will show a configuration message. All upload, processing, and UI features work.
- **OCR (Tesseract)**: For image OCR, install Tesseract OCR on your system. Without it, image upload will fail gracefully with an error message.
- **First time**: The embedding model (`all-MiniLM-L6-v2`) downloads automatically on first use (~90MB).

---

## 📝 License

Built for educational purposes. Use freely.
