#!/usr/bin/env python3
"""
Cross-Category Product Association Sync Script

This script regenerates the UrunBirliktelikleri table with only cross-category
product associations, filtering out same-category substitutes.

Requirements:
- The script should be run when Django backend is stopped to avoid DB locks
- Creates associations between products from DIFFERENT main categories only
- Examples: pasta + tomato sauce, coffee + milk, yogurt + granola
- Excludes: pasta + pasta, different brands of same product, etc.

Usage:
    python sync_cross_category_associations.py
"""

import sqlite3
import os
import sys
from datetime import datetime

def get_db_path():
    """Get the path to the sales_cache.db database"""
    from models import DB_PATH
    return DB_PATH

def check_database_availability():
    """Check if database is available"""
    from models import get_connection, DB_BACKEND
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        if DB_BACKEND == "sqlite" and "database is locked" in str(e):
            print("Database is locked! Please stop Django backend first.")
            return False
        print(f"Database error: {e}")
        return False

def generate_cross_category_associations():
    """Generate cross-category product associations using SQL"""
    print("🔄 Generating cross-category product associations...")
    
    from models import get_connection, DB_BACKEND
    conn = get_connection()
    cursor = conn.cursor()
    
    print("📊 Analyzing sales data...")
    
    # Step 1: Clear existing associations
    cursor.execute("DELETE FROM urunbirliktelikleri")
    print("🧹 Cleared existing associations")
    
    # Step 2: Generate cross-category associations
    print("🔗 Finding cross-category product pairs...")
    
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
    
    cursor.execute(f"""
        INSERT INTO urunbirliktelikleri 
        (urun_id_1, urun_id_2, confidence, lift, ortak_fis_sayisi, tip, analiz_tarihi)
        WITH 
        -- Count products per basket
        basket_products AS (
            SELECT fis_no, urun_id
            FROM satislar
            WHERE tutar > 0
            GROUP BY fis_no, urun_id
        ),
        -- Cross-category pairs (products from different main categories in same basket)
        cross_pairs AS (
            SELECT 
                bp1.urun_id as urun_id_1,
                bp2.urun_id as urun_id_2,
                COUNT(DISTINCT bp1.fis_no) as ortak_fis_sayisi,
                k1.ana as kategori_1_ana,
                k2.ana as kategori_2_ana
            FROM basket_products bp1
            JOIN basket_products bp2 ON bp1.fis_no = bp2.fis_no AND bp1.urun_id < bp2.urun_id
            JOIN urunler u1 ON bp1.urun_id = u1.id
            JOIN urunler u2 ON bp2.urun_id = u2.id
            JOIN kategoriler k1 ON u1.kategori_id = k1.id
            JOIN kategoriler k2 ON u2.kategori_id = k2.id
            WHERE k1.ana IS NOT NULL 
              AND k2.ana IS NOT NULL
              AND k1.ana != k2.ana  -- MUST be different main categories
              -- Exclude noise categories (low-value/high-frequency items)
              AND k1.ana NOT IN ('Manav', 'Ekmek', 'Su', 'Poşet', 'Cam Şişe', 'Pet Şişe')
              AND k2.ana NOT IN ('Manav', 'Ekmek', 'Su', 'Poşet', 'Cam Şişe', 'Pet Şişe')
            GROUP BY bp1.urun_id, bp2.urun_id, k1.ana, k2.ana
            HAVING COUNT(DISTINCT bp1.fis_no) >= 8
        ),
        -- Calculate metrics
        metrics AS (
            SELECT 
                cp.urun_id_1,
                cp.urun_id_2,
                cp.ortak_fis_sayisi,
                -- Total receipts for lift calculation
                (SELECT COUNT(DISTINCT fis_no) FROM satislar WHERE tutar > 0) as total_baskets,
                -- Individual product frequencies
                (SELECT COUNT(DISTINCT fis_no) FROM satislar WHERE urun_id = cp.urun_id_1 AND tutar > 0) as freq1,
                (SELECT COUNT(DISTINCT fis_no) FROM satislar WHERE urun_id = cp.urun_id_2 AND tutar > 0) as freq2
            FROM cross_pairs cp
        )
        SELECT 
            urun_id_1,
            urun_id_2,
            -- Average confidence
            ((ortak_fis_sayisi / CAST(freq1 AS FLOAT)) + (ortak_fis_sayisi / CAST(freq2 AS FLOAT))) / 2 as confidence,
            -- Lift calculation
            (ortak_fis_sayisi / CAST(total_baskets AS FLOAT)) / 
            ((freq1 / CAST(total_baskets AS FLOAT)) * (freq2 / CAST(total_baskets AS FLOAT))) as lift,
            ortak_fis_sayisi,
            'CROSS_CATEGORY_SYNC' as tip,
            {now_func} as analiz_tarihi
        FROM metrics
        WHERE 
            ((ortak_fis_sayisi / CAST(freq1 AS FLOAT)) + (ortak_fis_sayisi / CAST(freq2 AS FLOAT))) / 2 >= 0.05
            AND (ortak_fis_sayisi / CAST(total_baskets AS FLOAT)) / ((freq1 / CAST(total_baskets AS FLOAT)) * (freq2 / CAST(total_baskets AS FLOAT))) >= 1.2
        ORDER BY lift DESC, ortak_fis_sayisi DESC
        LIMIT 3000
    """)
    
    inserted_count = cursor.rowcount
    conn.commit()
    print(f"✅ Generated {inserted_count} cross-category associations")
    
    # Show sample results
    if inserted_count > 0:
        cursor.execute("""
            SELECT u1.ad as urun1, k1.ana as kat1, u2.ad as urun2, k2.ana as kat2, 
                   b.ortak_fis_sayisi, b.confidence, b.lift
            FROM urunbirliktelikleri b
            JOIN urunler u1 ON b.urun_id_1 = u1.id
            JOIN urunler u2 ON b.urun_id_2 = u2.id
            JOIN kategoriler k1 ON u1.kategori_id = k1.id
            JOIN kategoriler k2 ON u2.kategori_id = k2.id
            ORDER BY b.lift DESC
            LIMIT 15
        """)
        
        results = cursor.fetchall()
        print(f"\n📋 Sample cross-category associations:")
        print(f"{'Product 1':<30} {'Category 1':<15} {'Product 2':<30} {'Category 2':<15} {'Co-occur':<8} {'Conf':<6} {'Lift':<6}")
        print("-" * 120)
        
        for row in results:
            print(f"{row[0][:28]:<30} {row[1][:13]:<15} {row[2][:28]:<30} {row[3][:13]:<15} {row[4]:<8} {row[5]:.3f} {row[6]:.2f}")
        
        # Show category distribution
        cursor.execute("""
            SELECT k1.ana, k2.ana, COUNT(*) as count
            FROM UrunBirliktelikleri b
            JOIN urunler u1 ON b.urun_id_1 = u1.id
            JOIN urunler u2 ON b.urun_id_2 = u2.id
            JOIN kategoriler k1 ON u1.kategori_id = k1.id
            JOIN kategoriler k2 ON u2.kategori_id = k2.id
            GROUP BY k1.ana, k2.ana
            ORDER BY count DESC
            LIMIT 10
        """)
        
        category_pairs = cursor.fetchall()
        print(f"\n🎯 Top category pairings (cross-category):")
        for cat1, cat2, count in category_pairs:
            print(f"   {cat1} + {cat2}: {count} associations")
    
    conn.close()
    return inserted_count

def main():
    """Main function"""
    print("=" * 60)
    print("Cross-Category Product Association Sync")
    print("=" * 60)
    
    try:
        # Check database availability
        if not check_database_availability():
            sys.exit(1)
        
        # Generate associations
        start_time = datetime.now()
        count = generate_cross_category_associations()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        print(f"\nSync completed successfully!")
        print(f"   Generated: {count} cross-category associations")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Time: {end_time.strftime('%H:%M:%S')}")
        
        print(f"\nThe UrunBirliktelikleri table now contains only")
        print(f"   cross-category associations (complementary products)")
        print(f"   Examples: pasta + sauce, coffee + milk, etc.")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()