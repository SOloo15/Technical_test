"""
WHO AFRO Regional Data Hub - Vulnerability Dashboard
"""

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="WHO AFRO - Vulnerability Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS
# ==========================================

st.markdown("""
    <style>
        .stApp { background-color: #87CEEB; }
        .header-container {
            background-color: #1a2a6c;
            padding: 20px 30px;
            border-radius: 10px;
            margin-bottom: 5px;
        }
        h1 { color: white !important; }    
        .header-title {
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin: 0;
        }
        .header-subtitle {
            color: #87CEEB; 
            font-size: 16px;
            font-weight: 400;
            margin: 0;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: #1a2a6c;
            padding: 10px 20px;
            border-radius: 10px 10px 0 0;
            margin-top: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #87CEEB;
            font-weight: 500;
            font-size: 16px;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: white;
            background-color: #2a3a7c;
            border-radius: 5px;
            padding: 5px 15px;
        }
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        .element-container { margin-bottom: 0rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# HEADER
# ==========================================

st.markdown("""
    <div class="header-container">
        <div style="display: flex; align-items: center; gap: 20px;">
            <div style="background-color: #2a3a7c; padding: 10px 15px; border-radius: 10px;">
                <span style="color: white; font-size: 28px;">🌍</span>
            </div>
            <div>
                <h1 class="header-title">WHO AFRO Regional Data Hub</h1>
                <p class="header-subtitle">Health Systems</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# DATABASE CONNECTION
# ==========================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'who_regional_health_surveillance_db',
    'user': 'postgres',
    'password': 'Coachez@2026',
    'port': 5432
}

def execute_query(query):
    """Execute a query and return results as DataFrame"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.warning(f"Query error: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

@st.cache_resource
def get_connection():
    """Create cached database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

@st.cache_data(ttl=300)
def load_vulnerability_data():
    """Load vulnerability data from database"""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
        SELECT 
            v.iso3, v.year, v.country_name, v.afro_subregion, v.priority_country,
            v.exposure_score, v.sensitivity_score, v.adaptive_capacity_score,
            v.vulnerability_score, v.vulnerability_category, v.vulnerability_driver,
            c.latitude, c.longitude
        FROM vulnerability v
        LEFT JOIN countries c ON v.iso3 = c.iso3
        ORDER BY v.year DESC, v.vulnerability_score DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if 'priority_country' in df.columns:
        df['priority_country_label'] = df['priority_country'].apply(
            lambda x: 'Yes' if x == 1 else 'No'
        )
    
    return df

@st.cache_data(ttl=300)
def get_available_years(df):
    """Get available years from data"""
    if df.empty:
        return []
    return sorted(df['year'].unique(), reverse=True)

# ==========================================
# LOAD DATA
# ==========================================

with st.spinner("Loading data from database..."):
    df = load_vulnerability_data()

if df.empty:
    st.error("❌ No data available. Please run the vulnerability analysis script first.")
    st.info("Run: python create_vulnerability_table.py")
    st.stop()

# ==========================================
# INITIALIZE SESSION STATE
# ==========================================

if 'tab2_map_df' not in st.session_state:
    st.session_state.tab2_map_df = pd.DataFrame()
if 'tab2_score_value' not in st.session_state: 
    st.session_state.tab2_score_value = 'vulnerability_score'
if 'tab2_score_display' not in st.session_state:
    st.session_state.tab2_score_display = 'Vulnerability Score'

# ==========================================
# TABS
# ==========================================

tab1, tab2 = st.tabs(["📊 Health Indicators", "🛡️ Health System Vulnerability"])

# ==========================================
# TAB 1: HEALTH INDICATORS
# ==========================================

with tab1:
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.markdown("**Select Table**")
        table_options = [
            'countries', 'population', 'disease_surveillance', 'outbreaks',
            'laboratory_capacity', 'reporting_metrics', 'workforce', 'funding'
        ]
        selected_table = st.selectbox("Table", options=table_options, index=0, key="tab1_table", label_visibility="collapsed")
        
        st.markdown("**Select Diseases**")
        disease_options = ['Cholera', 'Malaria', 'Measles', 'Ebola', 'Yellow Fever', 'Meningitis', 'Polio', 'COVID-19']
        is_disease_table = selected_table in ['disease_surveillance', 'outbreaks']
        selected_diseases = st.multiselect(
            "Diseases", options=disease_options, default=[],
            key="tab1_diseases", label_visibility="collapsed", disabled=not is_disease_table
        )
        
        st.markdown("---")
        st.markdown("**Select Column**")
        
        numeric_columns = {
            'countries': ['priority_country'],
            'population': ['total_population', 'under5_population', 'urban_population_pct'],
            'disease_surveillance': ['cases_reported', 'deaths_reported', 'attack_rate_per_100k', 'case_fatality_ratio_pct'],
            'outbreaks': ['duration_days', 'time_to_detection_days', 'cases', 'deaths'],
            'laboratory_capacity': ['total_public_labs', 'labs_iso15189_accredited', 'iso15189_accreditation_pct', 'avg_turnaround_time_days', 'diagnostic_tests_per_100k'],
            'reporting_metrics': ['timeliness_pct', 'completeness_pct', 'idsr_weekly_compliance_pct'],
            'workforce': ['epidemiologists_total', 'epidemiologists_per_100k', 'feltp_trained_total', 'feltp_trained_pct', 'lab_technicians_total', 'lab_technicians_per_100k'],
            'funding': ['total_funding_usd', 'domestic_funding_usd', 'external_funding_usd', 'funding_per_capita_usd', 'domestic_funding_share_pct']
        }
        
        available_cols = numeric_columns.get(selected_table, [])
        selected_column = st.selectbox("Column", options=available_cols, index=0 if available_cols else None, key="tab1_column", label_visibility="collapsed")
        
        st.markdown("**Select Year**")
        years = get_available_years(df)
        selected_year_tab1 = st.selectbox("Year", options=years, index=0 if years else None, key="tab1_year", label_visibility="collapsed")
        
        st.markdown("---")
        st.caption("Select options to update the map and summary")
    
    with col2:
        try:
            if selected_table == 'countries':
                query = f"SELECT iso3, country_name, {selected_column}, latitude, longitude FROM {selected_table}"
            else:
                query = f"""
                    SELECT c.iso3, c.country_name, t.{selected_column}, c.latitude, c.longitude 
                    FROM {selected_table} t 
                    JOIN countries c ON t.iso3 = c.iso3 
                    WHERE t.year = {selected_year_tab1}
                """
                if is_disease_table and selected_diseases:
                    disease_filter = "', '".join(selected_diseases)
                    query += f" AND t.disease IN ('{disease_filter}')"
            
            map_df = execute_query(query)
            
            if not map_df.empty and 'latitude' in map_df.columns:
                fig = px.choropleth(
                    map_df, locations='iso3', color=selected_column,
                    hover_name='country_name', hover_data={selected_column: ':.3f'},
                    color_continuous_scale='RdYlGn_r',
                    title=f'{selected_column} - {selected_year_tab1}',
                    projection='natural earth'
                )
                fig.update_layout(
                    height=550, paper_bgcolor='#87CEEB', plot_bgcolor='#87CEEB',
                    geo=dict(
                        showframe=False, showcoastlines=True, coastlinecolor='black', coastlinewidth=1.5,
                        showland=True, landcolor='lightgray', showocean=True, oceancolor='#87CEEB',
                        showcountries=True, countrycolor='black', countrywidth=1.5,
                        projection_type='natural earth', center=dict(lat=-4.0, lon=15.0),
                        lonaxis_range=[-20, 55], lataxis_range=[-36, 40]
                    ),
                    margin=dict(l=0, r=0, t=50, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
                if is_disease_table and selected_diseases:
                    st.caption(f"🦠 Diseases: {', '.join(selected_diseases)}")
            else:
                st.info("No data available for the selected filters")
        except Exception as e:
            st.warning(f"Unable to load map data: {str(e)}")
    
    with col3:
        try:
            if selected_table == 'countries':
                query = f"SELECT {selected_column} FROM {selected_table}"
            else:
                query = f"SELECT {selected_column} FROM {selected_table} WHERE year = {selected_year_tab1}"
                if is_disease_table and selected_diseases:
                    disease_filter = "', '".join(selected_diseases)
                    query += f" AND disease IN ('{disease_filter}')"
            
            summary_df = execute_query(query)
            
            if not summary_df.empty and selected_column in summary_df.columns:
                data = summary_df[selected_column].dropna()
                if not data.empty:
                    st.metric("Count", len(data))
                    st.metric("Mean", f"{data.mean():.3f}")
                    st.metric("Median", f"{data.median():.3f}")
                    st.metric("Min", f"{data.min():.3f}")
                    st.metric("Max", f"{data.max():.3f}")
                    st.metric("Std Dev", f"{data.std():.3f}")
                    null_count = summary_df[selected_column].isna().sum()
                    if null_count > 0:
                        st.caption(f"⚠️ {null_count} null values")
                else:
                    st.info("No numeric data available")
            else:
                st.info("No data available for summary")
        except Exception as e:
            st.warning(f"Unable to load summary: {str(e)}")
    
    st.markdown("---")
    col_table1, col_table2 = st.columns([3, 1])
    
    with col_table1:
        st.markdown(f"""
            <div style="background-color: #f0f4f8; padding: 15px; border-radius: 10px;">
                <h4 style="color: #1a2a6c; margin-top: 0;">Data Table: {selected_table.replace('_', ' ').title()}</h4>
            </div>
        """, unsafe_allow_html=True)
    
    with col_table2:
        st.markdown("<br>", unsafe_allow_html=True)
        download_csv_tab1 = st.button("📥 Download CSV", key="download_csv_tab1", use_container_width=True)
    
    try:
        if selected_table == 'countries':
            query = f"SELECT * FROM {selected_table}"
        else:
            query = f"SELECT * FROM {selected_table} WHERE year = {selected_year_tab1}"
            if is_disease_table and selected_diseases:
                disease_filter = "', '".join(selected_diseases)
                query += f" AND disease IN ('{disease_filter}')"
        
        table_df = execute_query(query)
        
        if not table_df.empty:
            st.dataframe(table_df, use_container_width=True, height=350, hide_index=True)
            st.caption(f"Showing {len(table_df)} records")
            
            if download_csv_tab1:
                csv = table_df.to_csv(index=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{selected_table}_{selected_year_tab1}_{timestamp}.csv"
                st.download_button(label="📥 Click to Download", data=csv, file_name=filename, mime="text/csv", key="download_csv_tab1_btn")
        else:
            st.info("No data available for the selected filters")
    except Exception as e:
        st.warning(f"Unable to load table data: {str(e)}")

# ==========================================
# TAB 2: HEALTH SYSTEM VULNERABILITY
# ==========================================

with tab2:
    score_options = {
        'exposure_score': 'Exposure Score',
        'sensitivity_score': 'Sensitivity Score',
        'adaptive_capacity_score': 'Adaptive Capacity Score',
        'vulnerability_score': 'Vulnerability Score'
    }
    
    if 'tab2_score' not in st.session_state:
        st.session_state.tab2_score = 'vulnerability_score'
    if 'tab2_year' not in st.session_state:
        years = get_available_years(df)
        st.session_state.tab2_year = years[0] if years else None
    
    col1, col2, col3 = st.columns([1, 2.5, 1.5])
    
    with col1:
        st.markdown("**Select Score**")
        selected_score = st.selectbox(
            "Score Type", options=list(score_options.keys()),
            format_func=lambda x: score_options[x], key="tab2_score_widget", label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("**Select Year**")
        years = get_available_years(df)
        selected_year_tab2 = st.selectbox(
            "Year", options=years, index=0 if years else None,
            key="tab2_year_widget", label_visibility="collapsed"
        )
        st.markdown("---")
        st.caption("Select options to update the map and summary")
    
    with col2:
        try:
            selected_score = st.session_state.tab2_score_widget
            selected_year_tab2 = st.session_state.tab2_year_widget
            
            query = f"""
                SELECT 
                    v.iso3 AS iso3, v.country_name AS country_name,
                    v.{selected_score} AS selected_score,
                    v.vulnerability_category AS vulnerability_category,
                    c.latitude AS latitude, c.longitude AS longitude
                FROM vulnerability v
                LEFT JOIN countries c ON v.iso3 = c.iso3
                WHERE v.year = {selected_year_tab2}
            """
            
            map_df = execute_query(query)
            
            if 'selected_score' in map_df.columns:
                map_df.rename(columns={'selected_score': selected_score}, inplace=True)
            
            score_display_name = score_options[selected_score]
            
            if not map_df.empty and 'iso3' in map_df.columns:
                fig = px.choropleth(
                    map_df, locations='iso3', color=selected_score,
                    hover_name='country_name',
                    hover_data={selected_score: ':.3f', 'vulnerability_category': True},
                    color_continuous_scale='RdYlGn_r', range_color=[0, 1],
                    title=f'{score_display_name} - {selected_year_tab2}',
                    projection='natural earth'
                )
                fig.update_layout(
                    height=550, paper_bgcolor='#87CEEB', plot_bgcolor='#87CEEB',
                    geo=dict(
                        showframe=False, showcoastlines=True, coastlinecolor='black', coastlinewidth=1.5,
                        showland=True, landcolor='lightgray', showocean=True, oceancolor='#87CEEB',
                        showcountries=True, countrycolor='black', countrywidth=1.5,
                        projection_type='natural earth', center=dict(lat=-4.0, lon=15.0),
                        lonaxis_range=[-20, 55], lataxis_range=[-36, 40]
                    ),
                    margin=dict(l=0, r=0, t=50, b=0)
                )
                fig.update_traces(marker_line_color='black', marker_line_width=1.5)
                st.plotly_chart(fig, use_container_width=True)
                
                st.session_state.tab2_map_df = map_df
                st.session_state.tab2_score_value = selected_score
                st.session_state.tab2_score_display = score_display_name
            else:
                st.info("No data available for the selected filters")
        except Exception as e:
            st.warning(f"Unable to load map data: {str(e)}")
    
    with col3:
        if 'tab2_map_df' in st.session_state:
            map_df = st.session_state.tab2_map_df
            selected_score = st.session_state.tab2_score_value
            score_display_name = st.session_state.tab2_score_display
            
            if not map_df.empty:
                st.markdown("**📈 Key Metrics**")
                st.metric("Countries", f"{len(map_df)}")
                avg_score = map_df[selected_score].mean()
                st.metric(f"Avg {score_display_name}", f"{avg_score:.3f}")
                min_score = map_df[selected_score].min()
                max_score = map_df[selected_score].max()
                st.metric("Range", f"{min_score:.3f} - {max_score:.3f}")
                
                st.markdown("---")
                st.markdown("**Top 3 Highest**")
                top3 = map_df.nlargest(3, selected_score)[['country_name', selected_score]]
                for _, row in top3.iterrows():
                    st.caption(f"• {row['country_name']}: {row[selected_score]:.3f}")
            else:
                st.warning("No data available for the selected filters")
        else:
            st.info("Select options to load data")