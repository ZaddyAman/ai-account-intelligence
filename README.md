# 🎯 AccountIQ - AI Account Intelligence & Enrichment System

<p align="center">
  <img src="https://img.shields.io/badge/AI-Powered-purple" alt="AI Powered">
  <img src="https://img.shields.io/badge/FastAPI-backend-blue" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-frontend-green" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT">
</p>

## 📌 Overview

**AccountIQ** is an AI-powered system that transforms raw website visitor signals or minimal company inputs into comprehensive, sales-ready account intelligence. Built for B2B sales and marketing teams who need to identify, enrich, and prioritize accounts with actionable insights.

---

## 🎯 Problem We Solve

| Challenge | Solution |
|-----------|----------|
| Anonymous website visitors provide no actionable insight | Reverse IP lookup + AI identification |
| Incomplete company data makes prioritization difficult | Multi-source enrichment with confidence scoring |
| Sales teams waste time on manual research | Automated AI research agents |
| Unknown visitor intent leads to missed opportunities | Behavioral analysis with intent scoring |

---

## ✨ Unique Features

### 1. 🔍 Intelligent Company Identification
- **Reverse IP Lookup** - Identifies company from visitor IP addresses
- **AI-Powered Research** - Uses LLM to infer company from minimal inputs
- **Multi-Source Validation** - Cross-references multiple data sources

### 2. 👤 Persona Inference
- Analyzes visitor browsing behavior to infer roles
- Pages visited → Role mapping (e.g., /pricing → Decision Maker)
- Confidence scoring for persona predictions

### 3. 📊 Intent Scoring
- Calculates buyer's journey stage (0-10 scale)
- Factors: page visits, time on site, repeat visits, page depth
- Real-time scoring with stage classification

### 4. 🏢 Company Profile Enrichment
- **Auto-discovered fields:**
  - Company Name & Domain
  - Industry classification
  - Company size (employee count)
  - Headquarters location
  - Founding year
  - Business description

### 5. 💻 Technology Stack Detection
- Identifies CRM (Salesforce, HubSpot, Pipedrive)
- Detects Marketing Automation tools
- Finds Analytics platforms (Google Analytics, Mixpanel)
- Discovers CMS and Cloud infrastructure

### 6. 🚀 Business Signals Detection
- **Active hiring** - Job posting analysis
- **Funding activity** - Recent rounds, IPO news
- **Market expansion** - New locations, markets
- **Product launches** - New features, releases
- **Partnerships** - Strategic alliances

### 7. 👑 Leadership Discovery
- Identifies C-Suite executives (CEO, CTO, CFO)
- Finds VP-level decision makers (Sales, Marketing, Operations)
- Provides contact context and confidence scores
- Uses current date awareness for up-to-date info

### 8. 📝 AI Summary Generation
- Concise research summaries
- Key findings highlighted
- Actionable insights included

### 9. 💬 Automated Outreach Composition
- Personalized cold outreach generation
- Context-aware messaging
- Multiple tone options

### 10. 📈 Multi-Agent Research Workflow
- Orchestrated research pipeline
- Parallel processing for speed
- Confidence-weighted results

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │Visitors  │  │ Company  │  │  Batch   │  │   History    │  │
│  │  Input   │  │  Input   │  │ Process  │  │   Panel      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
└───────┼─────────────┼──────────────┼───────────────┼──────────┘
        │             │              │               │
        └─────────────┴──────────────┴───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   FastAPI Backend  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐   ┌────────▼────────┐   ┌────────▼────────┐
│    Company    │   │     Visitor     │   │     Batch      │
│   Identifier  │   │    Analyzer     │   │    Processor   │
└───────┬───────┘   └────────┬────────┘   └────────┬────────┘
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼────────┐   ┌────────▼────────┐
│   IP Lookup   │   │   Web Scraper  │   │    LLM Service │
│   Service     │   │    (Multi-tier)│   │    (Kilo/Gemini)│
└───────────────┘   └─────────────────┘   └────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite, CSS3 |
| **Backend** | FastAPI, Python 3.12 |
| **LLM** | Kilo Code (primary), Gemini (fallback) |
| **Scraping** | BeautifulSoup, Playwright, Firecrawl (optional) |
| **Caching** | In-memory cache for performance |
| **Deployment** | Docker, Railway (backend), Netlify (frontend) |

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- Python 3.12+
- Kilo Code API key (or Gemini API key as fallback)

### Local Development

#### 1. Clone the Repository
```bash
git clone https://github.com/ZaddyAman/ai-account-intelligence.git
cd ai-account-intelligence
```

#### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env and add your API keys:
# KILO_API_KEY=your_kilo_key
# GEMINI_API_KEY=your_gemini_key  # optional

# Run the backend
uvicorn backend.main:app --reload
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### 4. Access the App
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/visitors` | GET | Get visitor dataset |
| `/api/analyze/visitor` | POST | Analyze single visitor |
| `/api/analyze/company` | POST | Analyze single company |
| `/api/analyze/batch` | POST | Analyze multiple companies |
| `/api/history` | GET | Get analysis history |

---

## 🎨 Features in Action

### Input Options

**1. Visitor Analysis**
```json
{
  "visitor_id": "001",
  "ip_address": "34.201.xxx.xxx",
  "pages_visited": ["/pricing", "/ai-sales-agent", "/case-studies"],
  "time_on_site": "3m 42s",
  "visits_this_week": 3
}
```

**2. Company Analysis**
```
Acme Corporation
TechStart Inc
Global Solutions Ltd
```

### Output Example

```json
{
  "company_name": "Acme Mortgage",
  "domain": "acmemortgage.com",
  "industry": "Mortgage Lending",
  "company_size": "200 employees",
  "headquarters": "Austin, Texas, USA",
  "founding_year": "2015",
  "description": "Digital mortgage platform...",
  "persona": {
    "role": "VP of Sales Operations",
    "confidence": 0.72
  },
  "intent_score": 8.4,
  "intent_stage": "Evaluation",
  "tech_stack": [
    {"category": "CRM", "technology": "Salesforce", "confidence": 0.85},
    {"category": "Marketing", "technology": "HubSpot", "confidence": 0.78}
  ],
  "leadership": [
    {"name": "John Smith", "title": "CEO", "department": "Executive", "confidence": 0.9},
    {"name": "Sarah Johnson", "title": "VP Sales", "department": "Sales", "confidence": 0.82}
  ],
  "business_signals": [
    {"signal_type": "hiring", "description": "Active hiring for engineering roles", "confidence": 0.75},
    {"signal_type": "funding", "description": "Series B funding announced in 2024", "confidence": 0.88}
  ],
  "ai_summary": "Acme Mortgage is a mid-sized digital lender...",
  "recommended_action": "Schedule demo with VP of Sales..."
}
```

---

## 🔄 Scraping Architecture

Our system uses a **4-tier scraping approach** for maximum reliability:

| Tier | Method | Use Case |
|------|--------|----------|
| **Tier 0** | Sitemap Discovery | Fast URL collection |
| **Tier 1** | API Detection | Structured data extraction |
| **Tier 2** | Playwright | JavaScript-rendered pages |
| **Tier 3** | BeautifulSoup | HTML parsing (fallback) |

**Smart Fallback:** If scraping fails, our LLM agents use current web knowledge to fill in the gaps.

---

## 🌟 Uniqueness Factors

### 1. **Multi-Agent Orchestration**
- Specialized agents for each enrichment task
- Parallel execution for speed
- Confidence-weighted aggregation

### 2. **Current-Date Awareness**
- LLM prompts include current date
- Gets latest leadership & business signals
- Avoids stale training data

### 3. **Cost-Effective Architecture**
- **Local scraping** as primary (no API costs)
- **Firecrawl** as optional enhancement
- **Kilo Code** free tier for LLM

### 4. **Offline-First Design**
- Works without external APIs (local scraping)
- Falls back to LLM knowledge when needed
- Caches results for performance

### 5. **Hackathon-Ready**
- Fast to set up
- Docker deployment ready
- Clear API documentation

---

## 🚢 Deployment

### Docker (Recommended)
```bash
# Build and run
docker build -t accountiq .
docker run -p 8000:8000 -e KILO_API_KEY=your_key accountiq
```

### Railway + Netlify
1. **Backend:** Deploy to Railway using the included `Dockerfile`
2. **Frontend:** Deploy to Netlify using `frontend/netlify.toml`

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

---

## 📁 Project Structure

```
├── backend/
│   ├── agents/           # AI research agents
│   │   ├── business_signals.py
│   │   ├── company_enricher.py
│   │   ├── competitor_detector.py
│   │   ├── leadership.py
│   │   ├── orchestrator.py
│   │   ├── persona_inferrer.py
│   │   ├── tech_detector.py
│   │   └── ...
│   ├── services/         # Core services
│   │   ├── scraper_service.py
│   │   ├── firecrawl_service.py
│   │   ├── llm_service.py
│   │   └── ...
│   ├── models/          # Data models
│   ├── main.py          # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/        # API client
│   │   ├── App.jsx     # Main component
│   │   └── ...
│   ├── package.json
│   └── netlify.toml
│
├── Dockerfile           # Backend container
├── railway.json         # Railway config
└── README.md
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - feel free to use this project for your own purposes.

---

## 🙏 Acknowledgments

- Built for the **Fello AI Builder Hackathon**
- Powered by **Kilo Code** AI
- Inspired by real B2B sales challenges

---

<p align="center">
  <strong>Ship fast. Be creative. Build something interesting.</strong>
</p>
