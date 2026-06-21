"""
Simple Data Loader - Just loads CSV data into PostgreSQL
"""

import pandas as pd
import psycopg2

# ==========================================
# CONFIGURATION - UPDATE THESE!
# ==========================================

DB_NAME = "who_regional_health_surveillance_db"
DB_USER = "postgres"
DB_PASSWORD = "Coachez@2026"  
DB_HOST = "localhost"
DB_PORT = "5432"

CSV_PATH = "C:/Users/Administrator/Documents/Stephen Oloo/Applications/WHO/Technical test/test_project/data/"

# ==========================================
# CONNECT TO DATABASE
# ==========================================

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

cursor = conn.cursor()

print("="*50)
print("🚀 LOADING DATA...")
print("="*50)

# ==========================================
# LOAD EACH CSV FILE
# ==========================================

# 1. Countries
print("\n📥 Loading countries...")
df = pd.read_csv(f"{CSV_PATH}countries.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO countries (iso3, country_name, afro_subregion, latitude, longitude, priority_country)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso3) DO NOTHING
    """, (row['iso3'], row['country_name'], row.get('afro_subregion'), 
          row.get('latitude'), row.get('longitude'), row.get('priority_country')))
print(f"✅ Loaded {len(df)} countries")

# 2. Population
print("\n📥 Loading population...")
df = pd.read_csv(f"{CSV_PATH}population.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO population (iso3, year, total_population, under5_population, urban_population_pct)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year) DO NOTHING
    """, (row['iso3'], row['year'], 
          int(row['total_population']) if pd.notna(row.get('total_population')) else None,
          int(row['under5_population']) if pd.notna(row.get('under5_population')) else None,
          row.get('urban_population_pct')))
print(f"✅ Loaded {len(df)} population records")

# 3. Disease Surveillance
print("\n📥 Loading disease surveillance...")
df = pd.read_csv(f"{CSV_PATH}disease_surveillance.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO disease_surveillance (iso3, year, disease, cases_reported, deaths_reported, 
                                         attack_rate_per_100k, case_fatality_ratio_pct)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year, disease) DO NOTHING
    """, (row['iso3'], row['year'], row['disease'], 
          int(row['cases_reported']) if pd.notna(row.get('cases_reported')) else 0, 
          int(row['deaths_reported']) if pd.notna(row.get('deaths_reported')) else 0, 
          row.get('attack_rate_per_100k'), row.get('case_fatality_ratio_pct')))
print(f"✅ Loaded {len(df)} disease surveillance records")

# 4. Outbreaks
print("\n📥 Loading outbreaks...")
df = pd.read_csv(f"{CSV_PATH}outbreaks.csv")

# Auto-detect date format
# If dates are in DD/MM/YYYY format like 24/01/2021
try:
    df['start_date'] = pd.to_datetime(df['start_date'], format='%d/%m/%Y')
except:
    # If dates are in YYYY-MM-DD format like 2021-01-24
    try:
        df['start_date'] = pd.to_datetime(df['start_date'])
    except:
        # If mixed formats, let pandas figure it out
        df['start_date'] = pd.to_datetime(df['start_date'], format='mixed')

print(f"   Date format detected and converted")

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO outbreaks (outbreak_id, iso3, year, disease, start_date, 
                              duration_days, time_to_detection_days, cases, deaths)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (outbreak_id) DO NOTHING
    """, (row['outbreak_id'], row['iso3'], row['year'], row['disease'], 
          row['start_date'], 
          int(row['duration_days']) if pd.notna(row.get('duration_days')) else None,
          int(row['time_to_detection_days']) if pd.notna(row.get('time_to_detection_days')) else None,
          int(row['cases']) if pd.notna(row.get('cases')) else 0,
          int(row['deaths']) if pd.notna(row.get('deaths')) else 0))
print(f"✅ Loaded {len(df)} outbreaks")

# 5. Laboratory Capacity
print("\n📥 Loading laboratory capacity...")
df = pd.read_csv(f"{CSV_PATH}laboratory_capacity.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO laboratory_capacity (iso3, year, total_public_labs, labs_iso15189_accredited,
                                        iso15189_accreditation_pct, avg_turnaround_time_days, 
                                        diagnostic_tests_per_100k)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year) DO NOTHING
    """, (row['iso3'], row['year'], 
          int(row['total_public_labs']) if pd.notna(row.get('total_public_labs')) else None,
          int(row['labs_iso15189_accredited']) if pd.notna(row.get('labs_iso15189_accredited')) else None,
          row.get('iso15189_accreditation_pct'), row.get('avg_turnaround_time_days'), 
          row.get('diagnostic_tests_per_100k')))
print(f"✅ Loaded {len(df)} laboratory capacity records")

# 6. Reporting Metrics
print("\n📥 Loading reporting metrics...")
df = pd.read_csv(f"{CSV_PATH}reporting_metrics.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO reporting_metrics (iso3, year, timeliness_pct, completeness_pct, idsr_weekly_compliance_pct)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year) DO NOTHING
    """, (row['iso3'], row['year'], row.get('timeliness_pct'), 
          row.get('completeness_pct'), row.get('idsr_weekly_compliance_pct')))
print(f"✅ Loaded {len(df)} reporting metrics records")

# 7. Workforce
print("\n📥 Loading workforce...")
df = pd.read_csv(f"{CSV_PATH}workforce.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO workforce (iso3, year, epidemiologists_total, epidemiologists_per_100k,
                              feltp_trained_total, feltp_trained_pct, lab_technicians_total,
                              lab_technicians_per_100k)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year) DO NOTHING
    """, (row['iso3'], row['year'], 
          int(row['epidemiologists_total']) if pd.notna(row.get('epidemiologists_total')) else None,
          row.get('epidemiologists_per_100k'),
          int(row['feltp_trained_total']) if pd.notna(row.get('feltp_trained_total')) else None,
          row.get('feltp_trained_pct'),
          int(row['lab_technicians_total']) if pd.notna(row.get('lab_technicians_total')) else None,
          row.get('lab_technicians_per_100k')))
print(f"✅ Loaded {len(df)} workforce records")

# 8. Funding
print("\n📥 Loading funding...")
df = pd.read_csv(f"{CSV_PATH}funding.csv")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO funding (iso3, year, total_funding_usd, domestic_funding_usd, external_funding_usd,
                            funding_per_capita_usd, domestic_funding_share_pct)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso3, year) DO NOTHING
    """, (row['iso3'], row['year'], 
          float(row['total_funding_usd']) if pd.notna(row.get('total_funding_usd')) else None,
          float(row['domestic_funding_usd']) if pd.notna(row.get('domestic_funding_usd')) else None,
          float(row['external_funding_usd']) if pd.notna(row.get('external_funding_usd')) else None,
          float(row['funding_per_capita_usd']) if pd.notna(row.get('funding_per_capita_usd')) else None,
          float(row['domestic_funding_share_pct']) if pd.notna(row.get('domestic_funding_share_pct')) else None))
print(f"✅ Loaded {len(df)} funding records")

# ==========================================
# COMMIT AND CLOSE
# ==========================================

conn.commit()
cursor.close()
conn.close()

print("\n" + "="*50)
print("✅ ALL DATA LOADED SUCCESSFULLY!")
print("="*50)