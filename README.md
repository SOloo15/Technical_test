# 🌍 WHO AFRO Regional Data Hub - Vulnerability Dashboard

A comprehensive health systems vulnerability dashboard for the WHO African Region, featuring interactive maps, health indicators, and data-driven vulnerability scoring.

## 📋 Overview

This project provides a complete solution for analysing health system vulnerability across 20 African countries. It includes:

- **Database Schema**: PostgreSQL with PostGIS for spatial data
- **ETL Pipeline**: Python scripts for data loading and cleaning
- **Vulnerability Analysis**: Composite scoring using Exposure, Sensitivity, and Adaptive Capacity
- **Interactive Dashboard**: Streamlit web application with maps and visualisations

## 🚀 Quick Start

### Prerequisites

- **PostgreSQL** 14+ with PostGIS 3.0+
- **Python** 3.9+
- **Git** (for cloning the repository)

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/who-afro-dashboard.git
cd who-afro-dashboard

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate.bat
# On Linux/Mac:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt
```
### Database Setup
```bash
# 1. Create the database
Create a database called "who_regional_health_surveillance_db" using pgAdmin 4

# 2. Create tables and views
In the Query Tool run "who_regional_health_surveillance_db_sql.sql" OR restore using "who_regional_health_surveillance_db_backup.backup"
```
### Data Loading
```bash
# 1. Place your CSV files in the data/ directory
# Required files: countries.csv, population.csv, disease_surveillance.csv,
# outbreaks.csv, laboratory_capacity.csv, reporting_metrics.csv,
# workforce.csv, funding.csv

# 2. Load data into the database
python 01_load_data.py

# 3. Clean population and funding data (if needed)
python 02_check_null_values.py
python 03_clean_population_data.py
python 04_clean_funding_data.py
```
### Vulnerability Analysis
```bash
python 05_create_vulnerability_table.py
```
### Launch Dashboard
```bash
streamlit run 06_dashboard.py
```
The dashboard will open at http://localhost:8501
