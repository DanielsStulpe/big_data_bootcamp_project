import os
from fastapi import FastAPI, Query
from pymongo import MongoClient
import snowflake.connector
from typing import Optional
from dotenv import load_dotenv
from functools import lru_cache
from typing import Tuple


load_dotenv()

CACHE_SIZE = 128  # number of unique queries to cache

# --- Snowflake connection setup ---
def get_snowflake_connection():
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE")
    )
    return conn

# --- Query fetching helper function ---
def fetch_query(query: str, params: tuple = ()):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    cursor.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

# --- Cached query helper ---
@lru_cache(maxsize=512)
def fetch_query_cached(query: str, params: Tuple = ()) -> list:
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    cursor.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


app = FastAPI()


# --- Endpoint 1: demographics ---
@app.get("/demographics")
def get_demographics(county: str = Query(None)):
    query = "SELECT * FROM CALIFORNIA_COVID_ANALYTICS.RAW.CA_COUNTY_DEMOGRAPHICS_2020 WHERE 1=1"
    params = []
    if county:
        query += " AND COUNTY_NAME = %s"
        params.append(county)

    result = fetch_query_cached(query, tuple(params))
    if not result:
        return {"error": "No demographics found"}
    return result if not county else result[0]


# --- Endpoint 2: cases ---
@app.get("/cases")
def get_cases(date: str = Query(None), county: str = Query(None)):
    query = "SELECT * FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.CASES WHERE 1=1"
    params = []
    if county:
        query += " AND AREA = %s"
        params.append(county)
    if date:
        query += " AND DATE = %s"
        params.append(date)

    result = fetch_query_cached(query, tuple(params))
    if not result:
        return {"error": "No cases found"}
    return result if not (county and date) else result[0]


# --- Endpoint 3: cases demographics ---
@app.get("/cases-demographics")
def get_cases_demographics(date: str = Query(None), category: str = Query(None)):
    query = "SELECT * FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.CASES_DEMOGRAPHICS WHERE 1=1"
    params = []
    if category:
        query += " AND DEMOGRAPHIC_CATEGORY = %s"
        params.append(category)
    if date:
        query += " AND REPORT_DATE = %s"
        params.append(date)

    result = fetch_query_cached(query, tuple(params))
    if not result:
        return {"error": "No cases demographics found"}
    return result if not (category and date) else result[0]


# --- Endpoint 4: hospitals ---
@app.get("/hospitals")
def get_hospitals(date: str = Query(None), county: str = Query(None)):
    query = "SELECT * FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.HOSPITALS_BY_COUNTY WHERE 1=1"
    params = []
    if county:
        query += " AND COUNTY = %s"
        params.append(county)
    if date:
        query += " AND TODAYS_DATE = %s"
        params.append(date)

    result = fetch_query_cached(query, tuple(params))
    if not result:
        return {"error": "No hospital data found"}
    return result if not (county and date) else result[0]


# --- Endpoint 5: cases + demographics (analytics view) ---
@app.get("/cases-demographics-view")
def get_cases_demographics_view(county: str = Query(None), date: str = Query(None),
                                start_date: str = Query(None), end_date: str = Query(None)):
    query = "SELECT * FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.CA_CASES_DEMOGRAPHICS_VIEW WHERE 1=1"
    params = []
    if county:
        query += " AND AREA = %s"
        params.append(county)
    if date:
        query += " AND DATE = %s"
        params.append(date)
    if start_date and end_date:
        query += " AND DATE BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    result = fetch_query_cached(query, tuple(params))
    if not result:
        return {"error": "No data found with given filters"}
    if county and (date or (start_date and end_date and start_date == end_date)):
        return result[0]
    return result


# --- Endpoint 6: Summary by county ---
@app.get("/summary/county")
def get_cases_summary_by_county(start_date: str = Query(None), end_date: str = Query(None),
                                metric: str = Query("cases_per_100k"), limit: int = Query(10)):
    query = f"SELECT AREA, AVG({metric}) AS avg_{metric} FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.CA_CASES_DEMOGRAPHICS_AGG WHERE 1=1"
    params = []
    if start_date:
        query += " AND DATE >= %s"
        params.append(start_date)
    if end_date:
        query += " AND DATE <= %s"
        params.append(end_date)
    query += f" GROUP BY AREA ORDER BY avg_{metric} DESC LIMIT %s"
    params.append(limit)

    result = fetch_query_cached(query, tuple(params))
    return result


# --- Endpoint 7: Summary by trend ---
@app.get("/summary/trend")
def get_trend(county: str = Query(None), metric: str = Query(None), interval: str = Query("day")):
    valid_metrics = {"cases": "TOTAL_CASES", "deaths": "TOTAL_DEATHS",
                     "cases_p_k": "CASES_PER_100K", "deaths_p_k": "DEATHS_PER_100K"}

    if metric and metric not in valid_metrics:
        return {"error": f"Invalid metric '{metric}'. Choose from {list(valid_metrics.keys())}"}

    if metric:
        if metric in ["cases", "deaths"]:
            select_clause = f"SUM({valid_metrics[metric]}) AS total_{metric}"
        else:
            select_clause = f"AVG({valid_metrics[metric]}) AS {valid_metrics[metric]}"
    else:
        select_clause = "SUM(TOTAL_CASES) AS TOTAL_CASES, SUM(TOTAL_DEATHS) AS TOTAL_DEATHS, " \
                        "AVG(CASES_PER_100K) AS CASES_PER_100K, AVG(DEATHS_PER_100K) AS DEATHS_PER_100K"

    date_expr = "DATE_TRUNC('month', DATE)" if interval == "month" else "DATE"
    query = f"SELECT {date_expr} AS period, {select_clause} FROM CALIFORNIA_COVID_ANALYTICS.ANALYTICS.CA_TREND_MV WHERE 1=1"
    params = []
    if county:
        query += " AND AREA = %s"
        params.append(county)

    result = fetch_query_cached(query, tuple(params))
    return result


# --- Endpoint 8: Comments for charts ---
@lru_cache(maxsize=512)
@app.get("/comments")
def get_comments(
    chart: str = Query(..., description="Chart type (e.g., 'Demographic Chart')"),
    metric: Optional[str] = Query(None, description="Metric name, if applicable"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, if applicable"),
    category: Optional[str] = Query(None, description="Category (for Demographic Chart)"),
    interval: Optional[str] = Query(None, description="Interval (for Trend Chart)"),
    counties: Optional[str] = Query(None, description="Counties (for Trend Chart)")
):
    """
    Get comments added by users on the dashboard, filtered by chart and other parameters.
    """
    
    # --- Local MongoDB connection ---
    client = MongoClient("mongodb://localhost:27017")
    
    # --- Clustered MongoDB connection (commented) ---
    # MONGO_USER = os.getenv("MONGO_USER")
    # MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    # MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")  # e.g., cluster0.abcde.mongodb.net
    # client = MongoClient(f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority")
    
    db = client["covid_dashboard"]
    comments_col = db["annotations"]

    # Build dynamic filter based on provided query parameters
    filter_criteria = {"chart": chart}
    if metric:
        filter_criteria["metric"] = metric
    if date:
        filter_criteria["date"] = date
    if category:
        filter_criteria["category"] = category
    if interval:
        filter_criteria["interval"] = interval
    if counties:
        filter_criteria["counties"] = counties

    # Fetch matching comments, newest first
    comments = list(comments_col.find(filter_criteria, {"_id": 0}).sort("timestamp", -1))

    client.close()
    return comments