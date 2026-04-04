<<<<<<< HEAD
# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
=======
# Loops AI Moderation System

A modern, full-stack **AI Text and Image Content Moderation Dashboard** built with a premium SaaS design. The system automatically analyzes posts for inappropriate content, visualizes moderation trends, and manages content via a dynamic social-media-style feed.

## 🚀 Key Features

*   **Intelligent Content Moderation:** Automatically analyzes both text and uploaded images using sophisticated machine learning pipelines to immediately accept or block content.
*   **Modern SaaS Interface:** A beautifully crafted, responsive dashboard built with React, Tailwind CSS, and Framer motion, featuring glassmorphism elements, sleek transitions, and a premium cream-and-wood aesthetic.
*   **Dynamic Twitter-style Feed:** User posts form an infinite-scrolling feed, instantly retrieved from the database. Allowed posts blend seamlessly, while "blocked" posts stand out vividly with a distinct red style and precise rejection reasons.
*   **Interactive Analytics Dashboard:** Real-time data visualization showing 7-day trends of allowed vs. blocked posts, built with `recharts`.
*   **Responsive Sidebar Navigation:** Smooth, animated sidebar menu allowing fast switching between Create Post, Feed, and Analytics views.

---

## 🛠️ Technology Stack

**Frontend:**
*   **Framework:** React 18, Vite
*   **Styling:** Tailwind CSS (customized with CSS variables)
*   **Animations:** Framer Motion
*   **Data Visualization:** Recharts
*   **Icons:** Lucide React

**Backend & AI Engine:**
*   **Framework:** FastAPI (Python)
*   **Database:** MongoDB, PyMongo
*   **Machine Learning:** PyTorch, HuggingFace Transformers, CLIP (for text & vision parsing)

---

## ⚙️ Installation & Setup

Before you start, make sure you have the following installed on your machine:
*   [Node.js](https://nodejs.org/) (v16+)
*   [Python](https://www.python.org/) (**v3.10+**)
*   [MongoDB Community Server](https://www.mongodb.com/try/download/community) running locally on the default port `27017`.

### 1. Setup the Backend API
Navigate to the `backend` directory, set up your Python environment, and start the FastAPI server:

```bash
# Move to the backend folder
cd backend

# Create and activate a Virtual Environment (Windows)
python -m venv venv
venv\Scripts\activate
# (For Mac/Linux: source venv/bin/activate)

# Install required dependencies
pip install -r requirements.txt

# Start the uvicorn development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
>>>>>>> e58fdb611b637d48a8a66336b7db4d5fc72f2f54
