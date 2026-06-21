# 🌍 WHO AFRO Regional Data Hub - Vulnerability Dashboard

A comprehensive health systems vulnerability dashboard for the WHO African Region, featuring interactive maps, health indicators, and data-driven vulnerability scoring.

## 📋 Overview

This project provides a complete solution for analyzing health system vulnerability across 20 African countries. It includes:

- **Database Schema**: PostgreSQL with PostGIS for spatial data
- **ETL Pipeline**: Python scripts for data loading and cleaning
- **Vulnerability Analysis**: Composite scoring using Exposure, Sensitivity, and Adaptive Capacity
- **Interactive Dashboard**: Streamlit web application with maps and visualizations

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

# 2. Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate.bat
# On Linux/Mac:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt
