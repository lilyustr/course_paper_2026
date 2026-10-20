# 🚲 Decision Support System for Spatio-temporal Citi Bike Demand Forecasting

Система підтримки прийняття рішень (СППР) для просторово-часового прогнозування попиту на поїздки мережі Citi Bike у Джерсі-Сіті (Jersey City) з метою оптимізації оперативного ребалансування велосипедів між станціями.

Курсова робота студентки 3-го курсу спеціальності «Комп'ютерні науки»  
**ЛНУ імені Івана Франка**

---

## 📌 Основні можливості (Features)

- **Машинне навчання:** Прогнозування попиту на кожній станції з використанням ансамблевої моделі RandomForestRegressor.
- **Порівняльний аналіз (Baseline Evaluation):** Порівняння результатів із класичними базовими методами (Historical Average, Naive Lag, Linear Regression).
- **Інтерактивна карта:** Візуалізація станцій та рівня ризику нестачі/переповнення за допомогою Leaflet / OpenStreetMap.
- **Аналітична панель:** Виведення точкових прогнозів, поточного лагу попиту та автоматичних рекомендацій щодо оперативного ребалансування.
- **REST API Бекенд:** Високопродуктивний бекенд на FastAPI для видачі геоданих станцій та розрахунку прогнозів у реальному часі.
- **Кросплатформність (PWA):** Підтримка Progressive Web App дозволяє встановлювати застосунок як нативну програму на Windows, macOS, Linux, Android та iOS.

---

## 🛠 Технологічний стек (Tech Stack)

### Data Processing & Machine Learning
- **Python 3.11+**, pandas, numpy, scikit-learn, joblib
- **Датасет:** Citi Bike Jersey City Tripdata (JC-202609-citibike-tripdata.csv)

### Backend
- **FastAPI**, uvicorn, pydantic

### Frontend & Cross-Platform
- **React (Vite)**, Tailwind CSS, Leaflet.js, Lucide Icons
- **PWA Integration:** Service Worker (sw.js) + Web App Manifest (manifest.json)

---

## 📊 Порівняння моделей (Model Evaluation)

| Модель / Метод | MAE (Середня абсолютна помилка) | RMSE (Квадратична помилка) | R² (Коефіцієнт детермінації) |
| :--- | :---: | :---: | :---: |
| **Historical Average** | 1.5213 | 2.1713 | 0.3883 |
| **Naive Lag (1h)** | 1.7783 | 2.6624 | 0.0803 |
| **Linear Regression** | 1.4162 | 2.2250 | 0.3577 |
| **Random Forest (Основна)** | **1.2807** | **1.8140** | **0.5730** |

---

## 🚀 Інструкція із запуску (Getting Started)

### 1. Клонування репозиторію та налаштування середовища
git clone https://github.com/your-username/course_paper_3d-year.git
cd course_paper_3d-year

### 2. Запуск Бекенду (FastAPI)
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

Бекенд буде доступний за адресою: http://127.0.0.1:8000 (Документація Swagger: http://127.0.0.1:8000/docs).

### 3. Запуск Фронтенду (React + Vite)
cd frontend
npm install
npm run dev

Фронтенд буде доступний за адресою: http://localhost:5173.

---

## 📱 Встановлення як PWA (Кросплатформність)

1. Відкрийте застосунок http://localhost:5173 у браузері Google Chrome або Microsoft Edge.
2. Натисніть «Інсталювати цей сайт як програму» у меню Edge (... -> Програми) або іконку в адресному рядку.
3. Застосунок відкриється в окремому автономному вікні та додасть іконку на ваш робочий стіл.