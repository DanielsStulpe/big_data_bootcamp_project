# COVID-19 California Dashboard & Analytics

This project provides an **end-to-end pipeline** for exploring and analyzing California COVID-19 data using Snowflake, FastAPI, Dash, and Streamlit.
It combines official demographic datasets with COVID-19 case, death, and hospitalization data, and exposes an API layer that powers interactive dashboards and advanced analytics.

---

## 📂 Project Structure

```
.
├── API_DOCS.md              # API documentation for all endpoints
├── snf_script.sql           # SQL script to set up Snowflake database, schemas, tables, and views
├── county_demographics.csv  # Official demographic dataset from Kaggle (1990–2020)
├── ca_demographics_etl.py   # ETL script: extracts, transforms, and loads county demographic data into Snowflake
├── api.py                   # FastAPI app serving California COVID-19 data through REST endpoints
├── visualization.py         # Dash app for interactive visualizations powered by API (optionally MongoDB)
├── analytics.py             # Streamlit app for advanced analytics, trends, and dashboards
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation (this file)
```

---

## 📄 File Descriptions

* **API\_DOCS.md** → Provides detailed documentation for the FastAPI endpoints (`/demographics`, `/cases`, `/cases-demographics`, `/hospitals`, `/cases-demographics-view`, `/summary/county`, `/summary/trend`, `/comments`).

* **snf\_script.sql** → Snowflake setup script. Creates the database `CALIFORNIA_COVID_ANALYTICS`, schemas (`RAW`, `ANALYTICS`), tables, views, and materialized views. Prepares aggregated and trend tables for analytics.

* **county\_demographics.csv** → Official Kaggle dataset ([link](https://www.kaggle.com/datasets/glozab/county-level-us-demographic-data-1990-2020/data)) containing U.S. county-level demographic data for 1990–2020. Used by the ETL process.

* **ca\_demographics\_etl.py** → ETL pipeline that:

  * **Extracts** the latest county demographics data from `county_demographics.csv`
  * **Transforms** the dataset to compute population ratios by race, age, and gender
  * **Loads** the transformed data into the Snowflake `RAW.CA_COUNTY_DEMOGRAPHICS_2020` table for downstream use.

* **api.py** → Implements a **FastAPI backend** for accessing Snowflake data. Supports demographic queries, case counts, hospitalizations, combined analytics, trends, and user-added comments (optionally backed by MongoDB).

* **visualization.py** → A **Dash application** that consumes the API to produce interactive COVID-19 dashboards (charts, filters, summaries). Can use MongoDB as a caching layer for performance if enabled.

* **analytics.py** → A **Streamlit application** for in-depth exploration and visualization of California COVID-19 trends, metrics, and comparisons across counties.

* **requirements.txt** → Lists all dependencies required to run the project (FastAPI, Snowflake connector, Dash, Streamlit, MongoDB, etc.).

* **README.md** → This documentation file.

---

## ⚙️ Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env` file

Create a `.env` file in the project root with the following variables:

```ini
# Snowflake connection
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=CALIFORNIA_COVID_ANALYTICS
SNOWFLAKE_SCHEMA=RAW

# Optional: MongoDB (Atlas)
MONGO_USER=your_username
MONGO_PASSWORD=your_password
MONGO_CLUSTER=cluster0.abcde.mongodb.net
```

🔹 If you want to use **clustered MongoDB (Atlas)**:

* Uncomment the MongoDB connection code in `api.py` and `visualization.py`
* For Dash (`visualization.py`), set `get_mongo_client(local=False)`

🔹 If you want to use **local MongoDB**:

* Install [MongoDB Community Server](https://www.mongodb.com/try/download/community)
* Run `mongod` in the terminal where MongoDB is installed
* Keep `get_mongo_client(local=True)` in `visualization.py`

### 3. Prepare Snowflake database

1. Add the free **CALIFORNIA\_COVID19\_DATASETS** dataset from Snowflake Marketplace.
2. Run `snf_script.sql` in a Snowflake worksheet to set up schemas, tables, and views.

### 4. Load demographics data

Run the ETL pipeline to load and transform county demographics:

```bash
python ca_demographics_etl.py
```

### 5. Start the API

Run the FastAPI server:

```bash
uvicorn api:app --reload
```

API docs will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) and also in [API\_DOCS.md](API_DOCS.md).

### 6. Run Dash visualizations

```bash
python visualization.py
```

Open the dashboard in your browser at the printed local URL.

### 7. Run Streamlit analytics

```bash
streamlit run analytics.py
```

