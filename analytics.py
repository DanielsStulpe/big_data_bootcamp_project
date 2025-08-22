import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from statsmodels.tsa.arima.model import ARIMA

API_URL = "http://localhost:8000"  # replace with your API URL

st.set_page_config(page_title="COVID-19 Analytics", layout="wide")
st.title("Analytical Features of California COVID-19 Dataset")

# --------------------------
# Load counties
# --------------------------
@st.cache_data
def get_counties():
    res = requests.get(f"{API_URL}/demographics")
    if res.ok:
        return [c["COUNTY_NAME"] for c in res.json()]
    return []

counties = get_counties()
metrics = ["cases", "deaths", "cases_p_k", "deaths_p_k"]

# --------------------------
# Sidebar
# --------------------------
st.sidebar.title("Analytics Options")
option = st.sidebar.radio("Choose Feature:", ["Time Series Forecasting", "Clustering Counties"])

# --------------------------
# Time Series Forecasting
# --------------------------
if option == "Time Series Forecasting":
    st.markdown("<h2 style='padding-bottom:20px;'>1️⃣ Time Series Forecasting</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        selected_county = st.selectbox(
            "Select County", 
            counties, 
            index=counties.index("Los Angeles") if "Los Angeles" in counties else 0
        )
    with col2:
        selected_metric = st.selectbox("Select Metric", metrics)

    forecast_horizon = st.slider("Forecast Horizon (days)", 1, 60, 14)

    if st.button("Run Forecast"):
        st.write(f"Forecasting {selected_metric} for {selected_county} for next {forecast_horizon} days...")

        res = requests.get(f"{API_URL}/summary/trend", params={
            "county": selected_county, 
            "metric": selected_metric, 
            "interval": "day"
        })

        if res.ok and res.json():
            df = pd.DataFrame(res.json())

            metric_map = {
                "cases": "TOTAL_CASES",
                "deaths": "TOTAL_DEATHS",
                "cases_p_k": "CASES_PER_100K",
                "deaths_p_k": "DEATHS_PER_100K"
            }
            metric_col = metric_map[selected_metric]

            if metric_col not in df.columns:
                st.warning(f"No data available for {selected_metric} in {selected_county}.")
            else:
                df.rename(columns={'PERIOD': 'period', metric_col: 'value'}, inplace=True)
                df['period'] = pd.to_datetime(df['period'], errors='coerce')
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df = df.dropna(subset=['period', 'value']).set_index('period')

                if df.empty:
                    st.warning(f"No valid {selected_metric} data available for {selected_county}.")
                else:
                    try:
                        model = ARIMA(df['value'], order=(1,1,1))
                        model_fit = model.fit()
                        forecast = model_fit.forecast(steps=forecast_horizon)
                        forecast_dates = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=forecast_horizon)
                        forecast_df = pd.DataFrame({'value': forecast}, index=forecast_dates)

                        df['type'] = 'Observed'
                        forecast_df['type'] = 'Forecast'
                        combined = pd.concat([df, forecast_df])

                        fig = px.line(
                            combined,
                            x=combined.index,
                            y='value',
                            color='type',
                            labels={'index': 'Date', 'value': selected_metric.capitalize(), 'type': 'Data Type'},
                            title=f"{selected_metric.capitalize()} Forecast for {selected_county}"
                        )
                        fig.update_traces(selector=dict(name='Forecast'), line=dict(color='red', dash='dash'))
                        st.plotly_chart(fig)
                    except Exception as e:
                        st.error(f"Forecast error: {e}")
        else:
            st.warning("No trend data available for this county/metric.")

# --------------------------
# Clustering Counties
# --------------------------
elif option == "Clustering Counties":
    st.markdown("<h2 style='padding-bottom:20px;'>2️⃣ Clustering Counties</h2>", unsafe_allow_html=True)

    selected_features = st.multiselect(
        "Select Features for Clustering (use metrics like CASES_PER_100K, DEATHS_PER_100K or population ratios)",
        [
            "CASES_PER_100K",
            "DEATHS_PER_100K",
            "MALE_POPULATION_RATIO",
            "FEMALE_POPULATION_RATIO",
            "W_POPULATION_RATIO",
            "B_POPULATION_RATIO",
            "O_POPULATION_RATIO",
            "NH_POPULATION_RATIO",
            "HI_POPULATION_RATIO",
            "NA_POPULATION_RATIO",
            "AGE_0_19_POPULATION_RATIO",
            "AGE_20_49_POPULATION_RATIO",
            "AGE_50_64_POPULATION_RATIO",
            "AGE_65_PLUS_POPULATION_RATIO"
        ],
        default=["CASES_PER_100K", "DEATHS_PER_100K"]
    )

    num_clusters = st.slider("Number of Clusters", 2, 10, 3)

    if st.button("Run Clustering"):
        if not selected_features or len(selected_features) < 2:
            st.warning("Please select at least two features for clustering.")
        else:
            res = requests.get(f"{API_URL}/cases-demographics-view", params={})
            if res.ok and res.json():
                cluster_data = pd.DataFrame(res.json()).set_index('AREA')
                cluster_data = cluster_data[selected_features].dropna()

                scaler = StandardScaler()
                cluster_scaled = scaler.fit_transform(cluster_data)

                kmeans = KMeans(n_clusters=num_clusters, random_state=42)
                cluster_labels = kmeans.fit_predict(cluster_scaled)
                cluster_data['Cluster'] = cluster_labels

                x_feature, y_feature = selected_features[:2]

                cluster_data_plot = cluster_data.copy()
                cluster_data_plot[x_feature] = StandardScaler().fit_transform(cluster_data_plot[[x_feature]])
                cluster_data_plot[y_feature] = StandardScaler().fit_transform(cluster_data_plot[[y_feature]])

                fig = px.scatter(
                    cluster_data_plot,
                    x=x_feature,
                    y=y_feature,
                    color='Cluster',
                    hover_name=cluster_data_plot.index,
                    title=f"County Clusters ({num_clusters} groups)",
                    size_max=15
                )
                st.plotly_chart(fig)
            else:
                st.warning("No data available for clustering.")
