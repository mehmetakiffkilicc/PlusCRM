# 🚀 MarketFlow: Next-Generation AI-Powered Customer Relationship Management

Welcome to **MarketFlow**, a state-of-the-art, data-driven CRM dashboard application. This project demonstrates a full-stack, enterprise-grade application featuring advanced product analytics, customer segmentation, and AI-driven campaign recommendations. 

*Note: This repository contains an anonymized version of the project created for demonstration purposes. Real customer data and sensitive credentials have been removed or replaced with mock structures.*

## ✨ Key Features
- **📊 Real-time Product Analytics**: Comprehensive insights into sales trends, category performance, and inventory health with sub-second query performance.
- **🎯 Intelligent Customer Segmentation (RFM)**: Automated analysis using Recency, Frequency, and Monetary metrics to generate actionable "Customer Scorecards" (Müşteri Karnesi).
- **🤖 AI-Powered Campaign Recommendations**: Dynamic suggestion engine generating targeted marketing campaigns based on deep behavioral analysis.
- **📈 Interactive Dashboards**: Premium UI built with modern React components and high-performance charting libraries (ECharts/Recharts).
- **🛡️ Scalable Backend Architecture**: Robust Python-based APIs handling complex aggregations and data pipelines seamlessly.

## 🛠️ Technology Stack
### Frontend
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS & Custom Glassmorphism UI
- **Data Visualization**: Apache ECharts
- **Build Tool**: Vite

### Backend
- **Framework**: Python (Django / FastAPI)
- **Database**: PostgreSQL / SQLite (Mocked for Demo)
- **Data Processing**: Pandas, NumPy
- **Containerization**: Docker & Docker Compose

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Docker (optional, for containerized setup)

### Local Development Setup

#### 1. Clone the repository
```bash
git clone https://github.com/mehmetakiffkilicc/market_analitik.git
cd market_analitik
```

#### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows use: .venv\Scripts\activate
source .venv/bin/activate  
pip install -r requirements.txt
# Start server
python manage.py runserver
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`.

## 📸 Screenshots

![Dashboard Overview](screenshots/dashboard_overview.png)
![Customer Analysis](screenshots/customer_segmentation.png)
![Product Analytics](screenshots/product_analytics.png)
![Campaign Recommendations](screenshots/campaign_recommendations.png)

## 🔒 Data Anonymization & Privacy
This repository is a sanitized version of the original production application. 
- All database dumps have been scrubbed of Personally Identifiable Information (PII).
- Hardcoded keys, tokens, and environments have been removed.
- Certain proprietary AI models and internal business logic modules have been replaced with stubs to protect intellectual property.

## 📄 License
This project is intended for demonstration purposes. All rights reserved.

