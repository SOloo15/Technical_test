"""
NULL Value Checker
"""

import psycopg2

DB_NAME = "who_regional_health_surveillance_db"
DB_USER = "postgres"
DB_PASSWORD = "Coachez@2026"
DB_HOST = "localhost"
DB_PORT = "5432"

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

cursor = conn.cursor()

# Get all tables
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY tablename
""")
tables = cursor.fetchall()

print("="*60)
print("🔍 NULL VALUE CHECKER (Simple Version)")
print("="*60)

tables_with_nulls = []

for table in tables:
    table_name = table[0]
    
    # Get columns for this table
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = cursor.fetchall()
    
    has_nulls = False
    null_info = []
    
    for col in columns:
        col_name = col[0]
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN {col_name} IS NULL THEN 1 ELSE 0 END) as null_count
            FROM {table_name}
        """)
        result = cursor.fetchone()
        total = result[0]
        null_count = result[1]
        
        if null_count > 0:
            has_nulls = True
            null_info.append(f"{col_name}: {null_count} NULLs ({null_count/total*100:.1f}%)")
    
    if has_nulls:
        tables_with_nulls.append(table_name)
        print(f"\n📋 {table_name}:")
        for info in null_info:
            print(f"   - {info}")

if tables_with_nulls:
    print(f"\n⚠️  Tables with NULL values: {', '.join(tables_with_nulls)}")
else:
    print("\n✅ No NULL values found in any table!")

cursor.close()
conn.close()