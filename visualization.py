import pandas as pd
import requests
import datetime
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, ctx  
from pymongo import MongoClient


# ------------------------------
# MongoDB Helper Functions
# ------------------------------
def get_mongo_client(local=True):
    """
    Returns a MongoClient. By default connects to local MongoDB.
    Set local=False to use credentials from .env for a cluster.
    """
    if local:
        return MongoClient("mongodb://localhost:27017/")
    else:
        # Clustered MongoDB connection
        # from dotenv import load_dotenv
        # load_dotenv()
        # MONGO_USER = os.getenv("MONGO_USER")
        # MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
        # MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
        # return MongoClient(
        #     f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"
        # )
        raise NotImplementedError("Cluster connection not implemented in this example.")

def insert_comment(chart, comment_text, **kwargs):
    """
    Insert a comment into the MongoDB annotations collection.
    kwargs can include metric, date, category, interval, counties, etc.
    """
    if not comment_text or comment_text.strip() == "":
        return "⚠️ Please enter a comment before submitting."

    client = get_mongo_client(local=True)
    db = client["covid_dashboard"]
    annotations_col = db["annotations"]

    doc = {
        "chart": chart,
        "comment": comment_text.strip(),
        "timestamp": datetime.datetime.utcnow()
    }
    doc.update(kwargs)  # add extra fields dynamically

    try:
        annotations_col.insert_one(doc)
        return "✅ Comment submitted successfully!"
    except Exception as e:
        return f"❌ Error saving comment: {str(e)}"
    finally:
        client.close()


def fetch_comments(chart, **filters):
    """
    Fetch comments for a chart with optional filters.
    Returns a list of Dash HTML elements for display.
    """
    client = get_mongo_client(local=True)
    db = client["covid_dashboard"]
    annotations_col = db["annotations"]

    try:
        comments = list(
            annotations_col.find({"chart": chart, **filters}).sort("timestamp", -1)
        )
    finally:
        client.close()

    if not comments:
        return [html.P("No comments yet for this selection.", style={'color': 'gray'})]

    comments_list = [
        html.Div([
            html.P(f"📝 {c['comment']}", style={'margin': '2px 0'}),
            html.Small(c['timestamp'].strftime("%Y-%m-%d %H:%M:%S UTC"), style={'color': 'gray'})
        ], style={'padding': '6px', 'borderBottom': '1px solid #ddd'})
        for c in comments
    ]
    return comments_list


# --- FastAPI API base URL ---
API_BASE = "http://127.0.0.1:8000"

# ---------- Dash App ----------
app = Dash(__name__)

metrics = {
    'Cases': 'CASES',
    'Deaths': 'DEATHS',
    'Cases per 100k': 'CASES_PER_100K',
    'Deaths per 100k': 'DEATHS_PER_100K'
}

comparison_metrics = {
    'Cases per 100k': 'CASES_PER_100K',
    'Deaths per 100k': 'DEATHS_PER_100K'    
}

demographic_categories = ['Race Ethnicity', 'Age Group', 'Gender']

demographic_metrics = {
    'Cases': 'TOTAL_CASES',
    'Percent Cases': 'PERCENT_CASES',
    'Deaths': 'DEATHS',
    'Percent Deaths': 'PERCENT_DEATHS'
}

counties_list = [
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras", "Colusa", "Contra Costa", "Del Norte", "El Dorado", "Fresno", "Glenn", "Humboldt",
    "Imperial", "Inyo", "Kern", "Kings", "Lake", "Lassen", "Los Angeles", "Madera", "Marin", "Mariposa", "Mendocino", "Merced", "Modoc", "Mono",
    "Monterey", "Napa", "Nevada", "Orange", "Placer", "Plumas", "Riverside","Sacramento", "San Benito", "San Bernardino", "San Diego", 
    "San Francisco", "San Joaquin", "San Luis Obispo", "San Mateo", "Santa Barbara", "Santa Clara","Santa Cruz", "Shasta", "Sierra", "Siskiyou", 
    "Solano", "Sonoma", "Stanislaus", "Sutter", "Tehama", "Trinity", "Tulare", "Tuolumne", "Ventura", "Yolo", "Yuba"
]

section_style = {
    'backgroundColor': 'white',
    'padding': '30px',
    'marginBottom': '60px',
    'borderRadius': '12px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
    'maxWidth': '1000px',
    'margin': '40px auto'
}

app.layout = html.Div([
    html.H1("California COVID-19 Dashboard", style={
        'textAlign': 'center',
        'marginBottom': '50px'
    }),

    # ----- Choropleth Map -----
    html.Div([
        html.H2("COVID-19 Metrics per County", style={'textAlign': 'center', 'marginBottom': '30px'}),

        html.Div([
            html.Div([
                html.Label("Select Date:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.DatePickerSingle(id='date-picker-map', date=pd.to_datetime('2022-12-31'))
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Select Metric:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='metric-dropdown',
                    options=[{'label': k, 'value': v} for k, v in metrics.items()],
                    value='CASES_PER_100K',
                    clearable=False,
                    style={'width': '160px', 'height': '47px'}
                )
            ])
        ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),

        dcc.Graph(id='choropleth-map', style={'height': '600px'}),

        # --- Choropleth Comments ---
        html.Div([
            html.Label("Add a Comment:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Textarea(
                id='choropleth-comment-input',
                placeholder="Write your comment here...",
                style={'width': '100%', 'height': 50, 'marginBottom': '10px'}
            ),
            html.Button("Submit Comment", id='choropleth-submit-btn', n_clicks=0,
                        style={'backgroundColor': "#e28b60", 'color': 'white',
                               'padding': '10px 20px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='choropleth-comment-status', style={'marginTop': '10px', 'color': 'green'}),
            html.Hr(),
            html.H4("Comments"),
            html.Div(id='choropleth-comments-list', style={'marginTop': '10px'})
        ], style={'marginTop': '20px'})
    ], style=section_style),

    # ----- Comparative Analysis -----
    html.Div([
        html.H2("Comparative Analysis: Top Counties", style={'textAlign': 'center', 'marginBottom': '30px'}),

        html.Div([
            html.Div([
                html.Label("Select Date:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.DatePickerSingle(id='date-picker-comparison', date=pd.to_datetime('2022-12-31'))
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Top N Counties:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Input(id='top-n-input', type='number', min=1, max=58, step=1, value=5,
                          style={'width': '100px', 'height': '43px', 'textAlign': 'center', 'fontSize': '20px'})
            ], style={'margin': '0 20px'}),

            html.Div([
                html.Label("Select Metric:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='comparison-metric-dropdown',
                    options=[{'label': k, 'value': v} for k, v in comparison_metrics.items()],
                    value='CASES_PER_100K',
                    clearable=False,
                    style={'width': '160px', 'height': '47px'}
                )
            ])
        ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),

        dcc.Graph(id='comparison-bar-chart', style={'height': '500px'}),

        # --- Comparative Comments ---
        html.Div([
            html.Label("Add a Comment:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Textarea(
                id='comparison-comment-input',
                placeholder="Write your comment here...",
                style={'width': '100%', 'height': 50, 'marginBottom': '10px'}
            ),
            html.Button("Submit Comment", id='comparison-submit-btn', n_clicks=0,
                        style={'backgroundColor': "#e28b60", 'color': 'white',
                               'padding': '10px 20px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='comparison-comment-status', style={'marginTop': '10px', 'color': 'green'}),
            html.Hr(),
            html.H4("Comments"),
            html.Div(id='comparison-comments-list', style={'marginTop': '10px'})
        ])
    ], style=section_style),

    # ----- Demographic Analysis -----
    html.Div([
        html.H2("Demographic Analysis", style={'textAlign': 'center', 'marginBottom': '30px'}),

        html.Div([
            html.Div([
                html.Label("Select Date:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.DatePickerSingle(id='date-picker-demographics', date=pd.to_datetime('2020-12-31'))
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Select Category:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='demographic-category-dropdown',
                    options=[{'label': c, 'value': c} for c in demographic_categories],
                    value='Race Ethnicity',
                    clearable=False,
                    style={'width': '160px', 'height': '47px'}
                )
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Select Metric:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='demographic-metric-dropdown',
                    options=[{'label': k, 'value': v} for k, v in demographic_metrics.items()],
                    value='TOTAL_CASES',
                    clearable=False,
                    style={'width': '160px', 'height': '47px'}
                )
            ])
        ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),

        dcc.Graph(id='demographic-bar-chart', style={'height': '500px'}),

        # --- Demographic Comments ---
        html.Div([
            html.Label("Add a Comment:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Textarea(
                id='demographic-analysis-comment-input',
                placeholder="Write your comment here...",
                style={'width': '100%', 'height': 50, 'marginBottom': '10px'}
            ),
            html.Button("Submit Comment", id='demographic-analysis-submit-btn', n_clicks=0,
                        style={'backgroundColor': "#e28b60", 'color': 'white',
                               'padding': '10px 20px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='demographic-analysis-comment-status', style={'marginTop': '10px', 'color': 'green'}),
            html.Hr(),
            html.H4("Comments"),
            html.Div(id='demographic-analysis-comments-list', style={'marginTop': '10px'})
        ], style={'marginTop': '20px'})
    ], style=section_style),

    # ----- Time Series -----
    html.Div([
        html.H2("Time Series / Trend Analysis", style={'textAlign': 'center', 'marginBottom': '30px'}),

        html.Div([
            html.Div([
                html.Label("Select Interval:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='trend-interval',
                    options=[{'label': 'Daily', 'value': 'day'}, {'label': 'Monthly', 'value': 'month'}],
                    value='day', clearable=False, style={'width': '160px', 'height': '47px'}
                )
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Select Metric:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='trend-metric',
                    options=[{'label': 'Cases', 'value': 'cases'}, {'label': 'Deaths', 'value': 'deaths'}],
                    value='cases', clearable=False, style={'width': '160px', 'height': '47px'}
                )
            ], style={'marginRight': '20px'}),

            html.Div([
                html.Label("Select Counties:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
                dcc.Dropdown(
                    id='trend-counties',
                    options=[{'label': c, 'value': c} for c in counties_list],
                    multi=True, value=[], placeholder="Leave empty for California",
                    style={'width': '260px', 'height': '47px'}
                )
            ])
        ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),

        dcc.Graph(id='trend-chart', style={'height': '500px'}),

        # --- Trend Comments ---
        html.Div([
            html.Label("Add a Comment:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Textarea(
                id='trend-comment-input',
                placeholder="Write your comment here...",
                style={'width': '100%', 'height': 50, 'marginBottom': '10px'}
            ),
            html.Button("Submit Comment", id='trend-submit-btn', n_clicks=0,
                        style={'backgroundColor': "#e28b60", 'color': 'white',
                               'padding': '10px 20px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='trend-comment-status', style={'marginTop': '10px', 'color': 'green'}),
            html.Hr(),
            html.H4("Comments"),
            html.Div(id='trend-comments-list', style={'marginTop': '10px'})
        ], style={'marginTop': '20px'})
    ], style=section_style),

    # ----- Scatterplot -----
    html.Div([
        html.H2("Cases vs Deaths Correlation by County", style={'textAlign': 'center', 'marginBottom': '30px'}),

        html.Div([
            html.Label("Select Date:", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '5px', 'textAlign': 'center'}),
            dcc.DatePickerSingle(id='scatter-date-picker', date=pd.to_datetime('2022-12-31'))
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),

        dcc.Graph(id='cases-vs-deaths-scatter', style={'height': '600px'}),

        # --- Scatter Comments ---
        html.Div([
            html.Label("Add a Comment:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Textarea(
                id='correlation-comment-input',
                placeholder="Write your comment here...",
                style={'width': '100%', 'height': 50, 'marginBottom': '10px'}
            ),
            html.Button("Submit Comment", id='correlation-submit-btn', n_clicks=0,
                        style={'backgroundColor': "#e28b60", 'color': 'white',
                               'padding': '10px 20px', 'border': 'none',
                               'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='correlation-comment-status', style={'marginTop': '10px', 'color': 'green'}),
            html.Hr(),
            html.H4("Comments"),
            html.Div(id='correlation-comments-list', style={'marginTop': '10px'})
        ], style={'marginTop': '20px'})
    ], style=section_style)

], style={'backgroundColor': '#f7f9fc', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'})



# ---------- Choropleth Callback  ----------
@app.callback(
    Output('choropleth-map', 'figure'),
    Input('date-picker-map', 'date'),
    Input('metric-dropdown', 'value')
)
def update_map(selected_date, selected_metric): 
    if not selected_date: 
        return {} 
    
    # Convert to YYYY-MM-DD
    try:
        selected_date_fmt = datetime.datetime.fromisoformat(selected_date).strftime("%Y-%m-%d")
    except Exception:
        selected_date_fmt = selected_date  # fallback in case already correct

    api_url = f"{API_BASE}/cases-demographics-view" 
    params = {"date": selected_date} 
    response = requests.get(api_url, params=params) 

    if response.status_code != 200: 
        return {} 
    
    data = response.json() 
    df = pd.DataFrame(data) 
    df['FIPS'] = df['FIPS'].str.zfill(5)

    fig = px.choropleth( 
        df,
        geojson='https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json', 
        locations='FIPS', 
        color=selected_metric, 
        hover_name='AREA', 
        color_continuous_scale="Reds"
    ) 

    fig.update_geos( 
        visible=False, 
        scope="usa", 
        center={"lat": 37.5, "lon": -119.5}, 
        lataxis_range=[32, 42], 
        lonaxis_range=[-125, -114] 
    ) 

    fig.update_layout( 
        title=f"California COVID-19 {selected_metric.replace('_',' ')} on {selected_date_fmt}", 
        margin={"r":0,"t":50,"l":0,"b":0}, 
        plot_bgcolor='#ffffff', 
        paper_bgcolor='#ffffff'
    ) 

    return fig

# ---------- Choropleth Map Comments Callback  ----------
@app.callback(
    [Output('choropleth-comment-status', 'children'),
     Output('choropleth-comments-list', 'children')],
    [Input('choropleth-submit-btn', 'n_clicks'),
     Input('metric-dropdown', 'value'),
     Input('date-picker-map', 'date')],
    [Input('choropleth-comment-input', 'value')]
)
def handle_choropleth_comments(n_clicks, metric, selected_date, comment_text):
    triggered_id = ctx.triggered_id
    status_msg = ""

    if triggered_id == "choropleth-submit-btn" and n_clicks:
        status_msg = insert_comment(
            chart="Choropleth Map",
            comment_text=comment_text,
            metric=metric,
            date=selected_date
        )

    comments_list = fetch_comments(
        chart="Choropleth Map",
        metric=metric,
        date=selected_date
    )

    return status_msg, comments_list


# ---------- Comparative Chart Callback ----------
@app.callback(
    Output('comparison-bar-chart', 'figure'),
    Input('date-picker-comparison', 'date'),
    Input('comparison-metric-dropdown', 'value'),
    Input('top-n-input', 'value')
)
def update_comparison_chart(selected_date, selected_metric, top_n):
    if not selected_date or not selected_metric or not top_n:
        return {}

    # Convert to YYYY-MM-DD
    try:
        selected_date_fmt = datetime.datetime.fromisoformat(selected_date).strftime("%Y-%m-%d")
    except Exception:
        selected_date_fmt = selected_date  # fallback in case already correct

    # Fetch data
    api_url = f"{API_BASE}/cases-demographics-view"
    params = {"date": selected_date}
    response = requests.get(api_url, params=params)
    
    if response.status_code != 200:
        return {}
    
    df = pd.DataFrame(response.json())
    
    # Sort by metric and pick top N
    df_top = df.sort_values(by=selected_metric, ascending=False).head(top_n)

    # Horizontal bar chart
    fig = px.bar(
        df_top,
        x=selected_metric,
        y='AREA',
        orientation='h',
        text=selected_metric,
        color=selected_metric,
        color_continuous_scale='Reds',
        labels={
            'AREA': 'County',
            selected_metric: selected_metric.replace('_', ' ').title()
        }
    )

    fig.update_layout(
        title=f"Top {top_n} California Counties by {selected_metric.replace('_', ' ').title()} on {selected_date_fmt}",
        yaxis={'categoryorder':'total ascending'},
        margin=dict(l=100, r=40, t=60, b=40)
    )

    return fig

# ---------- Comparative Chart Comments Callback  ----------
@app.callback(
    [Output('comparison-comment-status', 'children'),
     Output('comparison-comments-list', 'children')],
    [Input('comparison-submit-btn', 'n_clicks'),
     Input('comparison-metric-dropdown', 'value'),
     Input('date-picker-comparison', 'date')],
    [Input('comparison-comment-input', 'value')]
)
def handle_comparison_comments(n_clicks, metric, selected_date, comment_text):
    triggered_id = ctx.triggered_id
    status_msg = ""

    if triggered_id == "comparison-submit-btn" and n_clicks:
        status_msg = insert_comment(
            chart="Comparative Chart",
            comment_text=comment_text,
            metric=metric,
            date=selected_date
        )

    comments_list = fetch_comments(
        chart="Comparative Chart",
        metric=metric,
        date=selected_date
    )

    return status_msg, comments_list


# Callback for Demographic Chart
@app.callback(
    Output('demographic-bar-chart', 'figure'),
    Input('date-picker-demographics', 'date'),
    Input('demographic-category-dropdown', 'value'),
    Input('demographic-metric-dropdown', 'value')
)
def update_demographic_chart(selected_date, category, metric):
    if not selected_date or not category or not metric:
        return {}

    # Format date
    try:
        selected_date_fmt = pd.to_datetime(selected_date).strftime("%Y-%m-%d")
    except Exception:
        selected_date_fmt = selected_date

    # Fetch data from API
    api_url = f"{API_BASE}/cases-demographics"
    params = {"date": selected_date_fmt}
    response = requests.get(api_url, params=params)

    if response.status_code != 200:
        return {}

    df = pd.DataFrame(response.json())

    # Filter only selected category
    df_filtered = df[df["DEMOGRAPHIC_CATEGORY"] == category]

    # Bar chart
    fig = px.bar(
        df_filtered,
        x="DEMOGRAPHIC_VALUE",
        y=metric,
        text=metric,
        color=metric,
        color_continuous_scale="Reds",
        labels={
            "DEMOGRAPHIC_VALUE": category.replace("_", " ").title(),
            metric: metric.replace("_", " ").title()
        }
    )

    fig.update_layout(
        title=f"COVID-19 {metric.replace('_',' ')} by {category.replace('_',' ')} on {selected_date_fmt}",
        xaxis={'categoryorder': 'total descending'},
        margin=dict(l=40, r=40, t=60, b=80),
        plot_bgcolor='#ffffff',  # background of the plotting area
        paper_bgcolor='#ffffff'  # background outside plotting area
    )

    return fig

# ---------- Demographic Analysis Comments Callback  ----------
@app.callback(
    [Output('demographic-analysis-comment-status', 'children'),
     Output('demographic-analysis-comments-list', 'children')],
    [Input('demographic-analysis-submit-btn', 'n_clicks'),
     Input('demographic-metric-dropdown', 'value'),
     Input('date-picker-demographics', 'date'),
     Input('demographic-category-dropdown', 'value')],
    [Input('demographic-analysis-comment-input', 'value')]
)
def handle_demographic_comments(n_clicks, metric, selected_date, category, comment_text):
    triggered_id = ctx.triggered_id
    status_msg = ""

    if triggered_id == "demographic-analysis-submit-btn" and n_clicks:
        status_msg = insert_comment(
            chart="Demographic Chart",
            comment_text=comment_text,
            metric=metric,
            date=selected_date,
            category=category
        )

    comments_list = fetch_comments(
        chart="Demographic Chart",
        metric=metric,
        date=selected_date,
        category=category
    )

    return status_msg, comments_list


# ---------- Trend Chart Callback  ---------- 
@app.callback(
    Output('trend-chart', 'figure'),
    Input('trend-interval', 'value'),
    Input('trend-metric', 'value'),
    Input('trend-counties', 'value')
)
def update_trend(interval, metric, counties):
    dfs = []

    # If no county → whole CA in one request
    if not counties:
        response = requests.get(f"{API_BASE}/summary/trend", params={
            "metric": metric,
            "interval": interval
        })
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            df["AREA"] = "California"
            dfs.append(df)

    else:
        # One API call per county
        for county in counties:
            response = requests.get(f"{API_BASE}/summary/trend", params={
                "metric": metric,
                "interval": interval,
                "county": county
            })
            if response.status_code == 200:
                df = pd.DataFrame(response.json())
                df["AREA"] = county
                dfs.append(df)

    if not dfs:
        return {}

    df = pd.concat(dfs, ignore_index=True)

    # Ensure consistent column naming
    df.rename(columns={f"TOTAL_{metric.upper()}": "VALUE"}, inplace=True)

    fig = px.line(
        df,
        x="PERIOD",
        y="VALUE",
        color="AREA",
        title=f"{metric.capitalize()} Trend ({'Daily' if interval=='day' else 'Monthly'})"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=f"Total {metric.capitalize()}",
        margin=dict(l=50, r=30, t=50, b=50)
    )

    return fig

# ---------- Trend Chart Comments Callback  ----------
@app.callback(
    [Output('trend-comment-status', 'children'),
     Output('trend-comments-list', 'children')],
    [Input('trend-submit-btn', 'n_clicks'),
     Input('trend-metric', 'value'),
     Input('trend-interval', 'value'),
     Input('trend-counties', 'value')],
    [Input('trend-comment-input', 'value')]
)
def handle_trend_comments(n_clicks, metric, interval, counties, comment_text):
    triggered_id = ctx.triggered_id
    status_msg = ""

    if triggered_id == "trend-submit-btn" and n_clicks:
        status_msg = insert_comment(
            chart="Trend Chart",
            comment_text=comment_text,
            metric=metric,
            interval=interval,
            counties=counties
        )

    comments_list = fetch_comments(
        chart="Trend Chart",
        metric=metric,
        interval=interval,
        counties=counties
    )

    return status_msg, comments_list


# ----------  Callback for Scatterplot  ----------
@app.callback(
    Output('cases-vs-deaths-scatter', 'figure'),
    Input('scatter-date-picker', 'date')
)
def update_scatterplot(selected_date):
    if not selected_date:
        return {}

    api_url = f"{API_BASE}/cases-demographics-view"
    params = {"date": selected_date}
    response = requests.get(api_url, params=params)

    if response.status_code != 200:
        return {}

    data = response.json()
    df = pd.DataFrame(data)

    if df.empty:
        return {}

    # Build scatterplot
    fig = px.scatter(
        df,
        x="CASES_PER_100K",
        y="DEATHS_PER_100K",
        size="TOTAL_TESTS",
        color="AREA",
        hover_name="AREA",
        size_max=50
    )

    # Improve layout
    fig.update_layout(
        title=f"Cases vs Deaths per 100k (Date: {pd.to_datetime(selected_date).strftime('%Y-%m-%d')})",
        xaxis_title="Cases per 100k",
        yaxis_title="Deaths per 100k",
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff'
    )

    return fig

# ---------- Scatter Chart Comments Callback  ----------
@app.callback(
    [Output('correlation-comment-status', 'children'),
     Output('correlation-comments-list', 'children')],
    [Input('correlation-submit-btn', 'n_clicks'),
     Input('scatter-date-picker', 'date')],
    [Input('correlation-comment-input', 'value')]
)
def handle_scatter_comments(n_clicks, selected_date, comment_text):
    triggered_id = ctx.triggered_id
    status_msg = ""

    if triggered_id == "correlation-submit-btn" and n_clicks:
        status_msg = insert_comment(
            chart="Scatter Chart",
            comment_text=comment_text,
            date=selected_date
        )

    comments_list = fetch_comments(
        chart="Scatter Chart",
        date=selected_date
    )

    return status_msg, comments_list


if __name__ == '__main__':
    app.run(debug=True)
