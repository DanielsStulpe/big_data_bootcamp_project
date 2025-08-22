import os
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

# -----------------------------
# Step 1: Process California Demographics
# -----------------------------
# Load Kaggle demographics file
df = pd.read_csv("county_demographics.csv")

# Ensure FIPS are zero-padded strings
df["fips"] = df["fips"].astype(str).str.zfill(5)

# Filter for California (FIPS starting with 06) and year 2020
df_ca_2020 = df[(df["year"] == 2020) & (df["fips"].str.startswith("06"))].copy()

# Create grouped age categories
df_ca_2020["age_0_19_population"] = df_ca_2020[["age0_population","age1_population","age2_population","age3_population","age4_population"]].sum(axis=1)
df_ca_2020["age_20_49_population"] = df_ca_2020[["age5_population","age6_population","age7_population","age8_population","age9_population","age10_population"]].sum(axis=1)
df_ca_2020["age_50_64_population"] = df_ca_2020[["age11_population","age12_population","age13_population"]].sum(axis=1)
df_ca_2020["age_65_plus_population"] = df_ca_2020[["age14_population","age15_population","age16_population","age17_population","age18_population"]].sum(axis=1)

df_ca_2020["age_0_19_population_ratio"] = df_ca_2020[["age0_population_ratio","age1_population_ratio","age2_population_ratio","age3_population_ratio","age4_population_ratio"]].sum(axis=1)
df_ca_2020["age_20_49_population_ratio"] = df_ca_2020[["age5_population_ratio","age6_population_ratio","age7_population_ratio","age8_population_ratio","age9_population_ratio","age10_population_ratio"]].sum(axis=1)
df_ca_2020["age_50_64_population_ratio"] = df_ca_2020[["age11_population_ratio","age12_population_ratio","age13_population_ratio"]].sum(axis=1)
df_ca_2020["age_65_plus_population_ratio"] = df_ca_2020[["age14_population_ratio","age15_population_ratio","age16_population_ratio","age17_population_ratio","age18_population_ratio"]].sum(axis=1)

# Select relevant columns
relevant_columns = [
    'fips', 'population', 'w_population','b_population','o_population','nh_population','hi_population','na_population',
    'male_population','female_population','age_0_19_population','age_20_49_population','age_50_64_population','age_65_plus_population',
    'w_population_ratio','b_population_ratio','o_population_ratio','nh_population_ratio','hi_population_ratio','na_population_ratio',
    'male_population_ratio','female_population_ratio','age_0_19_population_ratio','age_20_49_population_ratio','age_50_64_population_ratio','age_65_plus_population_ratio'
]
df_ca_2020_final = df_ca_2020[relevant_columns]

# Merge with county names
fips_url = "https://raw.githubusercontent.com/kjhealy/fips-codes/master/state_and_county_fips_master.csv"
fips_df = pd.read_csv(fips_url, dtype=str)
ca_fips = fips_df[fips_df['state'] == 'CA'][['fips','name']]
ca_fips['fips'] = ca_fips['fips'].str.zfill(5)
ca_fips['name'] = ca_fips['name'].str.replace(" County$", "", regex=True)

df_ca_2020_named = df_ca_2020_final.merge(ca_fips, on="fips", how="left")
df_ca_2020_named.rename(columns={"name": "county_name"}, inplace=True)
df_ca_2020_named.columns = [col.upper() for col in df_ca_2020_named.columns]

# Save CSV (optional)
# df_ca_2020_named.to_csv("california_demographics_2020.csv", index=False)
# print("California demographics processed successfully!")

# -----------------------------
# Step 2: Upload to Snowflake
# -----------------------------
# Load environment variables
load_dotenv()

# Connect to Snowflake
conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE")  # optional
)

# Upload DataFrame to Snowflake
success, nchunks, nrows, _ = write_pandas(conn, df_ca_2020_named, "CA_COUNTY_DEMOGRAPHICS_2020")
if success:
    print(f"Upload complete! {nrows} rows inserted in {nchunks} chunks.")

conn.close()
