"""
Population Data Cleaning Script
Cleans population data with the following rules:
1. If total_population is NULL: Compute using trend model for specific country
2. If under5_population is NULL: Use average proportion of under5 to total population 
   for specific country × total population of that year
3. If urban_population_pct is NULL: Use the mean value of that country
4. Track update timestamp for modified rows
"""

import pandas as pd
import psycopg2
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURATION
# ==========================================

DB_NAME = "who_regional_health_surveillance_db"
DB_USER = "postgres"
DB_PASSWORD = "Coachez@2026" 
DB_HOST = "localhost"
DB_PORT = "5432"

# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection():
    """Create database connection"""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def get_population_data():
    """Fetch population data from database"""
    conn = get_connection()
    query = """
        SELECT 
            iso3,
            year,
            total_population,
            under5_population,
            urban_population_pct,
            created_at,
            updated_at
        FROM population
        ORDER BY iso3, year
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def convert_to_python_type(value):
    """Convert numpy types to Python native types for PostgreSQL"""
    if value is None:
        return None
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    if isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    return value

def update_population_data(updates):
    """Update population data in database"""
    if not updates:
        print("   No updates to apply")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    update_count = 0
    for update in updates:
        # Convert numpy types to Python native types
        total_pop = convert_to_python_type(update['total_population'])
        under5_pop = convert_to_python_type(update['under5_population'])
        urban_pct = convert_to_python_type(update['urban_population_pct'])
        
        cursor.execute("""
            UPDATE population
            SET 
                total_population = %s,
                under5_population = %s,
                urban_population_pct = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE iso3 = %s AND year = %s
        """, (
            total_pop,
            under5_pop,
            urban_pct,
            update['iso3'],
            update['year']
        ))
        update_count += cursor.rowcount
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return update_count

# ==========================================
# CLEANING FUNCTIONS
# ==========================================

def clean_total_population(df):
    """
    Clean total_population using trend model for each country
    
    Rule: If total_population is NULL, compute using trend model for specific country
    Trend model: Uses linear regression on available years for each country
    """
    print("\n📊 Cleaning total_population...")
    updates = []
    
    # Group by country
    for iso3 in df['iso3'].unique():
        country_data = df[df['iso3'] == iso3].copy()
        
        # Get rows with and without total_population
        has_pop = country_data[country_data['total_population'].notna()]
        missing_pop = country_data[country_data['total_population'].isna()]
        
        if len(missing_pop) == 0:
            continue  # No missing data for this country
        
        if len(has_pop) >= 2:  # Need at least 2 data points for trend
            # Fit linear trend model
            years = has_pop['year'].values
            pops = has_pop['total_population'].values
            
            # Simple linear regression
            z = np.polyfit(years, pops, 1)
            slope, intercept = z[0], z[1]
            
            print(f"   {iso3}: Trend model: y = {slope:.0f}*year + {intercept:.0f}")
            
            # Fill missing values
            for idx, row in missing_pop.iterrows():
                predicted_pop = slope * row['year'] + intercept
                predicted_pop = max(0, int(predicted_pop))  # Ensure non-negative
                
                print(f"      Year {row['year']}: Predicted {predicted_pop:,} (was NULL)")
                
                updates.append({
                    'iso3': iso3,
                    'year': int(row['year']),
                    'total_population': int(predicted_pop),
                    'under5_population': convert_to_python_type(row['under5_population']),
                    'urban_population_pct': convert_to_python_type(row['urban_population_pct'])
                })
        else:
            # Not enough data for trend, use average growth rate from all countries
            print(f"   {iso3}: Not enough data for trend model (only {len(has_pop)} points)")
            
            # Calculate average growth rate from all countries with enough data
            country_growth_rates = []
            for c in df['iso3'].unique():
                c_data = df[df['iso3'] == c].sort_values('year')
                c_data = c_data[c_data['total_population'].notna()]
                if len(c_data) >= 2:
                    # Calculate compound annual growth rate
                    growth_rate = (c_data['total_population'].iloc[-1] / c_data['total_population'].iloc[0]) ** (1/len(c_data)) - 1
                    country_growth_rates.append(growth_rate)
            
            avg_growth_rate = np.mean(country_growth_rates) if country_growth_rates else 0.02
            
            # Fill missing values using last available value and average growth rate
            if len(has_pop) > 0:
                last_year = has_pop['year'].max()
                last_pop = has_pop[has_pop['year'] == last_year]['total_population'].iloc[0]
                
                for _, row in missing_pop.iterrows():
                    years_diff = row['year'] - last_year
                    predicted_pop = last_pop * (1 + avg_growth_rate) ** years_diff
                    predicted_pop = max(0, int(predicted_pop))
                    
                    print(f"      Year {row['year']}: Predicted {predicted_pop:,} (using avg growth rate)")
                    
                    updates.append({
                        'iso3': iso3,
                        'year': int(row['year']),
                        'total_population': int(predicted_pop),
                        'under5_population': convert_to_python_type(row['under5_population']),
                        'urban_population_pct': convert_to_python_type(row['urban_population_pct'])
                    })
    
    return updates

def clean_under5_population(df):
    """
    Clean under5_population using country-specific proportion
    
    Rule: If under5_population is NULL, use average proportion of under5 to total population 
    for specific country × total population of that year
    """
    print("\n👶 Cleaning under5_population...")
    updates = []
    
    for iso3 in df['iso3'].unique():
        country_data = df[df['iso3'] == iso3].copy()
        
        # Calculate average proportion of under5 to total for this country
        valid_data = country_data[
            (country_data['under5_population'].notna()) & 
            (country_data['total_population'].notna()) &
            (country_data['total_population'] > 0)
        ]
        
        if len(valid_data) == 0:
            # If no valid data for this country, use global average
            print(f"   {iso3}: No valid data, using global average")
            global_data = df[(df['under5_population'].notna()) & (df['total_population'].notna())]
            if len(global_data) > 0:
                avg_proportion = (global_data['under5_population'].sum() / global_data['total_population'].sum())
            else:
                avg_proportion = 0.16  # Default fallback (16% under5)
        else:
            avg_proportion = (valid_data['under5_population'].sum() / valid_data['total_population'].sum())
            print(f"   {iso3}: Average under5 proportion = {avg_proportion:.2%}")
        
        # Find rows with missing under5_population
        missing_under5 = country_data[country_data['under5_population'].isna()]
        
        if len(missing_under5) == 0:
            continue
        
        for idx, row in missing_under5.iterrows():
            if pd.notna(row['total_population']) and row['total_population'] > 0:
                # Rule: Average proportion × total population of that year
                predicted_under5 = int(row['total_population'] * avg_proportion)
                print(f"      Year {row['year']}: {row['total_population']:,} × {avg_proportion:.2%} = {predicted_under5:,}")
                
                updates.append({
                    'iso3': iso3,
                    'year': int(row['year']),
                    'total_population': convert_to_python_type(row['total_population']),
                    'under5_population': int(predicted_under5),
                    'urban_population_pct': convert_to_python_type(row['urban_population_pct'])
                })
    
    return updates

def clean_urban_population(df):
    """
    Clean urban_population_pct using country-specific mean
    
    Rule: If urban_population_pct is NULL, use the mean value of that country
    """
    print("\n🏙️  Cleaning urban_population_pct...")
    updates = []
    
    for iso3 in df['iso3'].unique():
        country_data = df[df['iso3'] == iso3].copy()
        
        # Calculate country-specific mean
        valid_urban = country_data[country_data['urban_population_pct'].notna()]
        
        if len(valid_urban) > 0:
            country_mean = valid_urban['urban_population_pct'].mean()
            print(f"   {iso3}: Country mean = {country_mean:.1f}%")
        else:
            # If no data for this country, use global mean
            global_data = df[df['urban_population_pct'].notna()]
            if len(global_data) > 0:
                country_mean = global_data['urban_population_pct'].mean()
            else:
                country_mean = 30.0  # Default fallback
            print(f"   {iso3}: No data, using global mean = {country_mean:.1f}%")
        
        # Find rows with missing urban_population_pct
        missing_urban = country_data[country_data['urban_population_pct'].isna()]
        
        if len(missing_urban) == 0:
            continue
        
        for idx, row in missing_urban.iterrows():
            print(f"      Year {row['year']}: Using {country_mean:.1f}% (country mean)")
            
            updates.append({
                'iso3': iso3,
                'year': int(row['year']),
                'total_population': convert_to_python_type(row['total_population']),
                'under5_population': convert_to_python_type(row['under5_population']),
                'urban_population_pct': float(round(country_mean, 1))
            })
    
    return updates

def merge_updates(existing_updates, new_updates):
    """Merge updates, preferring existing updates"""
    
    # If no existing updates, return new updates
    if not existing_updates:
        return new_updates
    
    # Create lookup of existing updates
    existing_dict = {}
    for update in existing_updates:
        key = (update['iso3'], update['year'])
        existing_dict[key] = update
    
    # Merge updates
    merged = existing_updates.copy()
    for update in new_updates:
        key = (update['iso3'], update['year'])
        if key not in existing_dict:
            merged.append(update)
        else:
            # Keep existing update, but ensure all fields are filled
            existing = existing_dict[key]
            for field in ['total_population', 'under5_population', 'urban_population_pct']:
                if existing[field] is None and update[field] is not None:
                    existing[field] = convert_to_python_type(update[field])
    
    return merged

# ==========================================
# DATA VALIDATION AFTER CLEANING
# ==========================================

def validate_cleaned_data(df_original, df_cleaned):
    """Validate the cleaned data"""
    print("\n" + "="*50)
    print("📊 DATA VALIDATION AFTER CLEANING")
    print("="*50)
    
    # Check for remaining NULLs
    null_counts_before = df_original.isnull().sum()
    null_counts_after = df_cleaned.isnull().sum()
    
    print("\n🔍 NULL Value Check:")
    print("   Column                Before    After    Fixed")
    print("   " + "-"*45)
    for col in ['total_population', 'under5_population', 'urban_population_pct']:
        before = null_counts_before[col]
        after = null_counts_after[col]
        fixed = before - after
        status = "✅" if fixed > 0 else "➖"
        print(f"   {col:<22} {before:>6}    {after:>6}    {status} {fixed}")
    
    # Check for negative values
    print("\n📈 Value Check:")
    if len(df_cleaned['total_population'].dropna()) > 0:
        print(f"   Total Population Min: {df_cleaned['total_population'].min():,}")
        print(f"   Total Population Max: {df_cleaned['total_population'].max():,}")
    if len(df_cleaned['under5_population'].dropna()) > 0:
        print(f"   Under5 Population Min: {df_cleaned['under5_population'].min():,}")
        print(f"   Under5 Population Max: {df_cleaned['under5_population'].max():,}")
    if len(df_cleaned['urban_population_pct'].dropna()) > 0:
        print(f"   Urban Population Mean: {df_cleaned['urban_population_pct'].mean():.1f}%")
    
    # Check data completeness per country
    print("\n🌍 Data Completeness by Country:")
    print("   Country              Records  TotalPop  Under5    Urban")
    print("   " + "-"*55)
    for iso3 in df_cleaned['iso3'].unique():
        country_data = df_cleaned[df_cleaned['iso3'] == iso3]
        records = len(country_data)
        total_pop = country_data['total_population'].notna().sum()
        under5 = country_data['under5_population'].notna().sum()
        urban = country_data['urban_population_pct'].notna().sum()
        print(f"   {iso3:<20} {records:>6}    {total_pop:>6}    {under5:>6}    {urban:>6}")

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("="*60)
    print("🧹 POPULATION DATA CLEANING SCRIPT")
    print("="*60)
    print(f"🗄️  Database: {DB_NAME}")
    print("="*60)
    
    # 1. Load data from database
    print("\n📥 Loading population data from database...")
    df = get_population_data()
    print(f"   Loaded {len(df)} records")
    print(f"   Years: {df['year'].min()} - {df['year'].max()}")
    print(f"   Countries: {len(df['iso3'].unique())}")
    
    # Store original for comparison
    df_original = df.copy()
    
    # 2. Count missing values
    print("\n📊 Missing Values Before Cleaning:")
    print(f"   total_population: {df['total_population'].isna().sum():,} missing")
    print(f"   under5_population: {df['under5_population'].isna().sum():,} missing")
    print(f"   urban_population_pct: {df['urban_population_pct'].isna().sum():,} missing")
    
    # 3. Apply cleaning functions
    all_updates = []
    
    # Clean total_population first (it's needed for other cleanings)
    print("\n" + "="*50)
    print("📊 STEP 1: Cleaning total_population")
    print("="*50)
    pop_updates = clean_total_population(df)
    all_updates = merge_updates(all_updates, pop_updates)
    print(f"\n   Found {len(pop_updates)} total_population updates")
    
    # Apply updates to dataframe for subsequent cleaning
    for update in all_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['total_population'] is not None:
            df.loc[mask, 'total_population'] = update['total_population']
    
    # Clean under5_population
    print("\n" + "="*50)
    print("📊 STEP 2: Cleaning under5_population")
    print("="*50)
    under5_updates = clean_under5_population(df)
    all_updates = merge_updates(all_updates, under5_updates)
    print(f"\n   Found {len(under5_updates)} under5_population updates")
    
    # Apply under5 updates to dataframe
    for update in under5_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['under5_population'] is not None:
            df.loc[mask, 'under5_population'] = update['under5_population']
    
    # Clean urban_population_pct
    print("\n" + "="*50)
    print("📊 STEP 3: Cleaning urban_population_pct")
    print("="*50)
    urban_updates = clean_urban_population(df)
    all_updates = merge_updates(all_updates, urban_updates)
    print(f"\n   Found {len(urban_updates)} urban_population_pct updates")
    
    # Apply urban updates to dataframe
    for update in urban_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['urban_population_pct'] is not None:
            df.loc[mask, 'urban_population_pct'] = update['urban_population_pct']
    
    # 4. Apply updates to database
    print("\n" + "="*50)
    print("💾 Applying updates to database...")
    print("="*50)
    update_count = update_population_data(all_updates)
    print(f"   ✅ Updated {update_count} rows")
    
    # 5. Validate results
    validate_cleaned_data(df_original, df)
    
    print("\n" + "="*60)
    print("✅ DATA CLEANING COMPLETE!")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   Total rows updated: {update_count}")
    print(f"   total_population fixed: {len(pop_updates)}")
    print(f"   under5_population fixed: {len(under5_updates)}")
    print(f"   urban_population_pct fixed: {len(urban_updates)}")

if __name__ == "__main__":
    main()