"""
Funding Data Cleaning Script
Cleans funding data with the following rules:
1. If total_funding_usd is NULL: Compute by adding domestic_funding_usd + external_funding_usd
2. If domestic_funding_usd is NULL: Check if can compute from total - external
3. If external_funding_usd is NULL: Check if can compute from total - domestic
4. If funding_per_capita_usd is NULL: Compute using Total Population / Total Funding
   (Get total_population from population table)
5. If domestic_funding_share_pct is NULL: Compute as (domestic_funding_usd / total_funding_usd) * 100
6. Track update timestamp for modified rows
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
DB_PASSWORD = "Coachez@2026"  # CHANGE THIS!
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

def get_funding_data():
    """Fetch funding data from database"""
    conn = get_connection()
    query = """
        SELECT 
            iso3,
            year,
            total_funding_usd,
            domestic_funding_usd,
            external_funding_usd,
            funding_per_capita_usd,
            domestic_funding_share_pct,
            created_at,
            updated_at
        FROM funding
        ORDER BY iso3, year
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_population_data():
    """Fetch population data from database"""
    conn = get_connection()
    query = """
        SELECT 
            iso3,
            year,
            total_population
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

def update_funding_data(updates):
    """Update funding data in database"""
    if not updates:
        print("   No updates to apply")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    update_count = 0
    for update in updates:
        # Convert numpy types to Python native types
        total_funding = convert_to_python_type(update.get('total_funding_usd'))
        domestic_funding = convert_to_python_type(update.get('domestic_funding_usd'))
        external_funding = convert_to_python_type(update.get('external_funding_usd'))
        funding_per_capita = convert_to_python_type(update.get('funding_per_capita_usd'))
        domestic_share = convert_to_python_type(update.get('domestic_funding_share_pct'))
        
        cursor.execute("""
            UPDATE funding
            SET 
                total_funding_usd = %s,
                domestic_funding_usd = %s,
                external_funding_usd = %s,
                funding_per_capita_usd = %s,
                domestic_funding_share_pct = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE iso3 = %s AND year = %s
        """, (
            total_funding,
            domestic_funding,
            external_funding,
            funding_per_capita,
            domestic_share,
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

def clean_total_funding(df):
    """
    Clean total_funding_usd
    
    Rule: If total_funding_usd is NULL, compute by adding domestic_funding_usd + external_funding_usd
    """
    print("\n💰 Cleaning total_funding_usd...")
    updates = []
    
    # Find rows with missing total_funding
    missing_total = df[df['total_funding_usd'].isna()]
    
    if len(missing_total) == 0:
        print("   No missing total_funding values found")
        return updates
    
    for idx, row in missing_total.iterrows():
        domestic = row.get('domestic_funding_usd')
        external = row.get('external_funding_usd')
        
        if pd.notna(domestic) and pd.notna(external):
            # Both available - add them
            total = domestic + external
            print(f"   {row['iso3']} Year {row['year']}: {domestic:,.2f} + {external:,.2f} = {total:,.2f}")
            
            updates.append({
                'iso3': row['iso3'],
                'year': int(row['year']),
                'total_funding_usd': float(total),
                'domestic_funding_usd': float(domestic),
                'external_funding_usd': float(external),
                'funding_per_capita_usd': row.get('funding_per_capita_usd'),
                'domestic_funding_share_pct': row.get('domestic_funding_share_pct')
            })
        elif pd.notna(domestic) and pd.isna(external):
            # Only domestic available
            print(f"   {row['iso3']} Year {row['year']}: Only domestic available ({domestic:,.2f}), cannot compute total")
        elif pd.isna(domestic) and pd.notna(external):
            # Only external available
            print(f"   {row['iso3']} Year {row['year']}: Only external available ({external:,.2f}), cannot compute total")
        else:
            print(f"   {row['iso3']} Year {row['year']}: No funding data available")
    
    return updates

def clean_domestic_funding(df):
    """
    Clean domestic_funding_usd
    
    Rule: If domestic_funding_usd is NULL and total_funding_usd and external_funding_usd are available,
    compute as: domestic_funding_usd = total_funding_usd - external_funding_usd
    """
    print("\n🏦 Cleaning domestic_funding_usd...")
    updates = []
    
    # Find rows with missing domestic_funding
    missing_domestic = df[df['domestic_funding_usd'].isna()]
    
    if len(missing_domestic) == 0:
        print("   No missing domestic_funding values found")
        return updates
    
    for idx, row in missing_domestic.iterrows():
        total = row.get('total_funding_usd')
        external = row.get('external_funding_usd')
        
        if pd.notna(total) and pd.notna(external):
            domestic = total - external
            if domestic >= 0:
                print(f"   {row['iso3']} Year {row['year']}: {total:,.2f} - {external:,.2f} = {domestic:,.2f}")
                
                updates.append({
                    'iso3': row['iso3'],
                    'year': int(row['year']),
                    'total_funding_usd': float(total),
                    'domestic_funding_usd': float(domestic),
                    'external_funding_usd': float(external),
                    'funding_per_capita_usd': row.get('funding_per_capita_usd'),
                    'domestic_funding_share_pct': row.get('domestic_funding_share_pct')
                })
            else:
                print(f"   {row['iso3']} Year {row['year']}: Cannot compute (would be negative: {domestic:,.2f})")
        else:
            print(f"   {row['iso3']} Year {row['year']}: Missing total or external funding")
    
    return updates

def clean_external_funding(df):
    """
    Clean external_funding_usd
    
    Rule: If external_funding_usd is NULL and total_funding_usd and domestic_funding_usd are available,
    compute as: external_funding_usd = total_funding_usd - domestic_funding_usd
    """
    print("\n🌍 Cleaning external_funding_usd...")
    updates = []
    
    # Find rows with missing external_funding
    missing_external = df[df['external_funding_usd'].isna()]
    
    if len(missing_external) == 0:
        print("   No missing external_funding values found")
        return updates
    
    for idx, row in missing_external.iterrows():
        total = row.get('total_funding_usd')
        domestic = row.get('domestic_funding_usd')
        
        if pd.notna(total) and pd.notna(domestic):
            external = total - domestic
            if external >= 0:
                print(f"   {row['iso3']} Year {row['year']}: {total:,.2f} - {domestic:,.2f} = {external:,.2f}")
                
                updates.append({
                    'iso3': row['iso3'],
                    'year': int(row['year']),
                    'total_funding_usd': float(total),
                    'domestic_funding_usd': float(domestic),
                    'external_funding_usd': float(external),
                    'funding_per_capita_usd': row.get('funding_per_capita_usd'),
                    'domestic_funding_share_pct': row.get('domestic_funding_share_pct')
                })
            else:
                print(f"   {row['iso3']} Year {row['year']}: Cannot compute (would be negative: {external:,.2f})")
        else:
            print(f"   {row['iso3']} Year {row['year']}: Missing total or domestic funding")
    
    return updates

def clean_funding_per_capita(df, pop_df):
    """
    Clean funding_per_capita_usd
    
    Rule: If funding_per_capita_usd is NULL, compute using:
    Funding Per Capita = Total Population / Total Funding
    Get total_population from population table
    """
    print("\n👤 Cleaning funding_per_capita_usd...")
    updates = []
    
    # Merge funding data with population data
    df_with_pop = df.merge(pop_df, on=['iso3', 'year'], how='left', suffixes=('', '_pop'))
    
    # Find rows with missing funding_per_capita
    missing_per_capita = df_with_pop[df_with_pop['funding_per_capita_usd'].isna()]
    
    if len(missing_per_capita) == 0:
        print("   No missing funding_per_capita values found")
        return updates
    
    for idx, row in missing_per_capita.iterrows():
        total_funding = row.get('total_funding_usd')
        total_population = row.get('total_population')
        
        if pd.notna(total_funding) and pd.notna(total_population) and total_population > 0:
            per_capita = total_funding / total_population
            print(f"   {row['iso3']} Year {row['year']}: {total_funding:,.2f} / {total_population:,} = {per_capita:.2f}")
            
            updates.append({
                'iso3': row['iso3'],
                'year': int(row['year']),
                'total_funding_usd': float(total_funding),
                'domestic_funding_usd': convert_to_python_type(row.get('domestic_funding_usd')),
                'external_funding_usd': convert_to_python_type(row.get('external_funding_usd')),
                'funding_per_capita_usd': float(per_capita),
                'domestic_funding_share_pct': convert_to_python_type(row.get('domestic_funding_share_pct'))
            })
        elif pd.isna(total_funding):
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (total_funding is NULL)")
        elif pd.isna(total_population):
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (population data missing)")
        else:
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (population is 0)")
    
    return updates

def clean_domestic_funding_share(df):
    """
    Clean domestic_funding_share_pct
    
    Rule: If domestic_funding_share_pct is NULL, compute as:
    (domestic_funding_usd / total_funding_usd) * 100
    """
    print("\n📊 Cleaning domestic_funding_share_pct...")
    updates = []
    
    # Find rows with missing domestic_funding_share
    missing_share = df[df['domestic_funding_share_pct'].isna()]
    
    if len(missing_share) == 0:
        print("   No missing domestic_funding_share values found")
        return updates
    
    for idx, row in missing_share.iterrows():
        domestic = row.get('domestic_funding_usd')
        total = row.get('total_funding_usd')
        
        if pd.notna(domestic) and pd.notna(total) and total > 0:
            share = (domestic / total) * 100
            print(f"   {row['iso3']} Year {row['year']}: ({domestic:,.2f} / {total:,.2f}) × 100 = {share:.1f}%")
            
            updates.append({
                'iso3': row['iso3'],
                'year': int(row['year']),
                'total_funding_usd': float(total),
                'domestic_funding_usd': float(domestic),
                'external_funding_usd': convert_to_python_type(row.get('external_funding_usd')),
                'funding_per_capita_usd': convert_to_python_type(row.get('funding_per_capita_usd')),
                'domestic_funding_share_pct': float(round(share, 1))
            })
        elif pd.isna(domestic):
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (domestic_funding is NULL)")
        elif pd.isna(total):
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (total_funding is NULL)")
        else:
            print(f"   {row['iso3']} Year {row['year']}: Cannot compute (total_funding is 0)")
    
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
            for field in ['total_funding_usd', 'domestic_funding_usd', 'external_funding_usd', 
                         'funding_per_capita_usd', 'domestic_funding_share_pct']:
                if existing.get(field) is None and update.get(field) is not None:
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
    print("   Column                       Before    After    Fixed")
    print("   " + "-"*50)
    for col in ['total_funding_usd', 'domestic_funding_usd', 'external_funding_usd', 
                'funding_per_capita_usd', 'domestic_funding_share_pct']:
        before = null_counts_before[col]
        after = null_counts_after[col]
        fixed = before - after
        status = "✅" if fixed > 0 else "➖"
        print(f"   {col:<25} {before:>6}    {after:>6}    {status} {fixed}")
    
    # Check data completeness per country
    print("\n🌍 Data Completeness by Country:")
    print("   Country              Total  Domestic  External  PerCapita  Share")
    print("   " + "-"*70)
    for iso3 in df_cleaned['iso3'].unique():
        country_data = df_cleaned[df_cleaned['iso3'] == iso3]
        total_pop = country_data['total_funding_usd'].notna().sum()
        domestic = country_data['domestic_funding_usd'].notna().sum()
        external = country_data['external_funding_usd'].notna().sum()
        per_capita = country_data['funding_per_capita_usd'].notna().sum()
        share = country_data['domestic_funding_share_pct'].notna().sum()
        print(f"   {iso3:<20} {total_pop:>5}      {domestic:>5}      {external:>5}      {per_capita:>5}       {share:>5}")

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("="*60)
    print("💰 FUNDING DATA CLEANING SCRIPT")
    print("="*60)
    print(f"🗄️  Database: {DB_NAME}")
    print("="*60)
    
    # 1. Load data from database
    print("\n📥 Loading funding data from database...")
    df = get_funding_data()
    print(f"   Loaded {len(df)} records")
    print(f"   Years: {df['year'].min()} - {df['year'].max()}")
    print(f"   Countries: {len(df['iso3'].unique())}")
    
    # Load population data
    print("\n📥 Loading population data for per capita calculations...")
    pop_df = get_population_data()
    print(f"   Loaded {len(pop_df)} population records")
    
    # Store original for comparison
    df_original = df.copy()
    
    # 2. Count missing values
    print("\n📊 Missing Values Before Cleaning:")
    print(f"   total_funding_usd: {df['total_funding_usd'].isna().sum():,} missing")
    print(f"   domestic_funding_usd: {df['domestic_funding_usd'].isna().sum():,} missing")
    print(f"   external_funding_usd: {df['external_funding_usd'].isna().sum():,} missing")
    print(f"   funding_per_capita_usd: {df['funding_per_capita_usd'].isna().sum():,} missing")
    print(f"   domestic_funding_share_pct: {df['domestic_funding_share_pct'].isna().sum():,} missing")
    
    # 3. Apply cleaning functions
    all_updates = []
    
    # Clean total_funding first (it may be needed for other calculations)
    print("\n" + "="*50)
    print("📊 STEP 1: Cleaning total_funding_usd")
    print("="*50)
    total_updates = clean_total_funding(df)
    all_updates = merge_updates(all_updates, total_updates)
    print(f"\n   Found {len(total_updates)} total_funding updates")
    
    # Apply updates to dataframe for subsequent cleaning
    for update in all_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['total_funding_usd'] is not None:
            df.loc[mask, 'total_funding_usd'] = update['total_funding_usd']
    
    # Clean domestic_funding
    print("\n" + "="*50)
    print("📊 STEP 2: Cleaning domestic_funding_usd")
    print("="*50)
    domestic_updates = clean_domestic_funding(df)
    all_updates = merge_updates(all_updates, domestic_updates)
    print(f"\n   Found {len(domestic_updates)} domestic_funding updates")
    
    # Apply domestic updates to dataframe
    for update in domestic_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['domestic_funding_usd'] is not None:
            df.loc[mask, 'domestic_funding_usd'] = update['domestic_funding_usd']
    
    # Clean external_funding
    print("\n" + "="*50)
    print("📊 STEP 3: Cleaning external_funding_usd")
    print("="*50)
    external_updates = clean_external_funding(df)
    all_updates = merge_updates(all_updates, external_updates)
    print(f"\n   Found {len(external_updates)} external_funding updates")
    
    # Apply external updates to dataframe
    for update in external_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['external_funding_usd'] is not None:
            df.loc[mask, 'external_funding_usd'] = update['external_funding_usd']
    
    # Clean funding_per_capita
    print("\n" + "="*50)
    print("📊 STEP 4: Cleaning funding_per_capita_usd")
    print("="*50)
    per_capita_updates = clean_funding_per_capita(df, pop_df)
    all_updates = merge_updates(all_updates, per_capita_updates)
    print(f"\n   Found {len(per_capita_updates)} funding_per_capita updates")
    
    # Apply per_capita updates to dataframe
    for update in per_capita_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['funding_per_capita_usd'] is not None:
            df.loc[mask, 'funding_per_capita_usd'] = update['funding_per_capita_usd']
    
    # Clean domestic_funding_share
    print("\n" + "="*50)
    print("📊 STEP 5: Cleaning domestic_funding_share_pct")
    print("="*50)
    share_updates = clean_domestic_funding_share(df)
    all_updates = merge_updates(all_updates, share_updates)
    print(f"\n   Found {len(share_updates)} domestic_funding_share updates")
    
    # Apply share updates to dataframe
    for update in share_updates:
        mask = (df['iso3'] == update['iso3']) & (df['year'] == update['year'])
        if update['domestic_funding_share_pct'] is not None:
            df.loc[mask, 'domestic_funding_share_pct'] = update['domestic_funding_share_pct']
    
    # 4. Apply updates to database
    print("\n" + "="*50)
    print("💾 Applying updates to database...")
    print("="*50)
    update_count = update_funding_data(all_updates)
    print(f"   ✅ Updated {update_count} rows")
    
    # 5. Validate results
    validate_cleaned_data(df_original, df)
    
    print("\n" + "="*60)
    print("✅ FUNDING DATA CLEANING COMPLETE!")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   Total rows updated: {update_count}")
    print(f"   total_funding_usd fixed: {len(total_updates)}")
    print(f"   domestic_funding_usd fixed: {len(domestic_updates)}")
    print(f"   external_funding_usd fixed: {len(external_updates)}")
    print(f"   funding_per_capita_usd fixed: {len(per_capita_updates)}")
    print(f"   domestic_funding_share_pct fixed: {len(share_updates)}")

if __name__ == "__main__":
    main()