## COVID Dashboard API Documentation

This API provides access to California COVID-19 data, including demographics, case counts, hospitalizations, combined analytics, trends, and user comments. Endpoints support filtering, aggregation, and caching for improved performance.

---

### **1️⃣ /demographics**

**Description:** Get demographics for all counties or a specific county.

**Parameters:**

* `county` (optional, string): Filter by county name.

**Response:**

* List of county demographic objects.
* If a single county is requested, returns a single object.

**Example Response:**

```json
{
  "COUNTY_NAME": "Los Angeles",
  "POPULATION": 1000000,
  "MALE_POPULATION_RATIO": 0.49,
  "FEMALE_POPULATION_RATIO": 0.51,
  ...
}
```

---

### **2️⃣ /cases**

**Description:** Get daily COVID-19 cases optionally filtered by date and/or county.

**Parameters:**

* `date` (optional, string YYYY-MM-DD): Filter by specific date.
* `county` (optional, string): Filter by county name.

**Response:**

* List of case objects.
* If a single county+date is requested, returns a single object.

**Example Response:**

```json
{
  "DATE": "2023-08-01",
  "AREA": "Los Angeles",
  "CASES": 2000,
  "DEATHS": 25
}
```

---

### **3️⃣ /cases-demographics**

**Description:** Get cases broken down by demographic categories.

**Parameters:**

* `date` (optional, string YYYY-MM-DD): Filter by date.
* `category` (optional, string): Demographic category (e.g., age group, race).

**Response:**

* List of objects containing case counts and demographic information.
* Returns single object if both date and category are specified.

**Example Response:**

```json
{
  "REPORT_DATE": "2023-08-01",
  "DEMOGRAPHIC_CATEGORY": "Age 20-49",
  "CASES": 500
}
```

---

### **4️⃣ /hospitals**

**Description:** Get hospitalizations by county and date.

**Parameters:**

* `date` (optional, string YYYY-MM-DD)
* `county` (optional, string)

**Response:**

* List of hospital objects with metrics.
* Returns single object if both date and county are specified.

**Example Response:**

```json
{
  "TODAYS_DATE": "2023-08-01",
  "COUNTY": "Los Angeles",
  "TOTAL_HOSPITALIZED": 120
}
```

---

### **5️⃣ /cases-demographics-view**

**Description:** Combined analytics of cases + demographics with per-100k calculations.

**Parameters:**

* `county` (optional, string): Filter by county.
* `date` (optional, string YYYY-MM-DD)
* `start_date` (optional, string YYYY-MM-DD)
* `end_date` (optional, string YYYY-MM-DD)

**Response:**

* List of combined case + demographic records.
* Returns single object if querying single county+date.

**Example Response:**

```json
{
  "DATE": "2023-08-01",
  "AREA": "Los Angeles",
  "CASES_PER_100K": 200,
  "DEATHS_PER_100K": 5,
  "MALE_POPULATION_RATIO": 0.49,
  ...
}
```

---

### **6️⃣ /summary/county**

**Description:** Top N counties ranked by average cases/deaths per 100k over a date range.

**Parameters:**

* `start_date` (optional, string YYYY-MM-DD)
* `end_date` (optional, string YYYY-MM-DD)
* `metric` (optional, string, default="cases\_per\_100k"): `cases_per_100k` or `deaths_per_100k`
* `limit` (optional, int, default=10)

**Response:**

* List of county summaries with average metrics.

**Example Response:**

```json
[
  {"AREA": "Los Angeles", "avg_cases_per_100k": 250},
  {"AREA": "San Diego", "avg_cases_per_100k": 180}
]
```

---

### **7️⃣ /summary/trend**

**Description:** Daily or monthly trend for cases, deaths, or per-100k metrics.

**Parameters:**

* `county` (optional, string)
* `metric` (optional, string): `cases`, `deaths`, `cases_p_k`, `deaths_p_k`
* `interval` (optional, string, default="day"): `day` or `month`

**Response:**

* List of objects grouped by period.

**Example Response:**

```json
[
  {"period": "2023-08-01", "TOTAL_CASES": 2000, "TOTAL_DEATHS": 25, "CASES_PER_100K": 200, "DEATHS_PER_100K": 5},
  {"period": "2023-08-02", "TOTAL_CASES": 2100, "TOTAL_DEATHS": 30, "CASES_PER_100K": 210, "DEATHS_PER_100K": 6}
]
```

---

### **8️⃣ /comments**

**Description:** Fetch user-added comments for charts on the dashboard. Uses LRU caching.

**Parameters:**

* `chart` (string, required): Chart type (e.g., "Demographic Chart")
* `metric` (optional, string)
* `date` (optional, string YYYY-MM-DD)
* `category` (optional, string)
* `interval` (optional, string)
* `counties` (optional, string)

**Response:**

* List of comment objects, newest first.

**Example Response:**

```json
[
  {"chart": "Demographic Chart", "metric": "cases_per_100k", "text": "Spike observed in young adults", "timestamp": "2023-08-01T12:00:00"},
  {"chart": "Trend Chart", "interval": "day", "text": "Steady increase", "timestamp": "2023-08-02T09:00:00"}
]
```