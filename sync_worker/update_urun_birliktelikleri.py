import sqlite3
import pandas as pd
from itertools import combinations
from collections import defaultdict
import math
import os

def get_db_path():
    """Get the path to the sales_cache.db database"""
    from models import DB_PATH
    return DB_PATH

def calculate_cross_category_associations(min_support=0.002, min_confidence=0.1, min_lift=1.2):
    """
    Calculate product-level associations with cross-category filtering only.
    Excludes same-category associations to focus on complementary products.
    """
    from models import get_connection
    conn = get_connection()
    
    print("Loading product data...")
    # Load products with categories
    products_df = pd.read_sql_query("""
        SELECT u.id, u.ad as urun_adi, u.kategori_id, k.ana as ana_kategori, 
               k.alt1 as alt_kategori, m.ad as marka_adi
        FROM urunler u
        LEFT JOIN kategoriler k ON u.kategori_id = k.id
        LEFT JOIN markalar m ON u.marka_id = m.id
    """, conn)
    
    print(f"Loaded {len(products_df)} products")
    
    # Load sales data for association analysis
    print("Loading sales data...")
    sales_df = pd.read_sql_query("""
        SELECT DISTINCT s.fis_no, s.urun_id, u.kategori_id, k.ana as ana_kategori
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        LEFT JOIN kategoriler k ON u.kategori_id = k.id
        WHERE s.tutar > 0
          -- Exclude unwanted categories (Manav, Ekmek, Sarf/Poşet, Sigara)
          AND k.ana NOT IN (
              'Meyve & Sebze - Yeşillik', 
              'Unlu Mamuller & Ekmek', 
              'Sarf & Gider', 
              'Sigara & Gazete',
              'Horeca',
              'İşletici kategorileri'
          )
          -- Exclude specific keywords (Poşet, Ekmek, etc.)
          AND u.ad NOT LIKE '%POŞET%'
          AND u.ad NOT LIKE 'POSET %'
          AND (u.ad NOT LIKE '% SU %' OR k.ana = 'İçecek')
          AND u.ad NOT LIKE '%EKMEK%'
        ORDER BY s.fis_no
    """, conn)
    
    print(f"Loaded {len(sales_df)} sales records")
    
    # Group by fis_no to get baskets
    print("Building baskets...")
    baskets = sales_df.groupby('fis_no').agg({
        'urun_id': lambda x: list(set(x)),  # Unique products per basket
        'kategori_id': lambda x: list(set(x)),  # Unique categories per basket
        'ana_kategori': lambda x: list(set(x))  # Unique main categories per basket
    }).reset_index()
    
    print(f"Built {len(baskets)} baskets")
    
    # Filter baskets: Must have > 1 unique items
    baskets = baskets[baskets['urun_id'].map(len) > 1]
    print(f"Filtered to {len(baskets)} valid baskets (with > 1 unique items)")
    
    # Calculate product frequencies
    print("Calculating product frequencies...")
    product_counts = defaultdict(int)
    category_map = {}  # product_id -> category_id
    ana_category_map = {}  # product_id -> main category
    
    for _, row in products_df.iterrows():
        category_map[row['id']] = row['kategori_id']
        ana_category_map[row['id']] = row['ana_kategori']
    
    for _, basket in baskets.iterrows():
        for product_id in basket['urun_id']:
            product_counts[product_id] += 1
    
    total_baskets = len(baskets)
    print(f"Total baskets: {total_baskets}")
    
    # Calculate cross-category co-occurrence
    print("Calculating cross-category co-occurrences...")
    co_occurrence = defaultdict(int)
    
    for _, basket in baskets.iterrows():
        products = basket['urun_id']
        categories = basket['kategori_id']
        ana_categories = basket['ana_kategori']
        
        # Create mapping for quick category lookup
        product_to_category = dict(zip(products, categories))
        product_to_ana_category = dict(zip(products, ana_categories))
        
        # Only consider pairs from different categories (cross-category)
        for p1, p2 in combinations(products, 2):
            cat1 = product_to_category[p1]
            cat2 = product_to_category[p2]
            ana_cat1 = product_to_ana_category[p1]
            ana_cat2 = product_to_ana_category[p2]
            
            # Must be from different main categories to be considered complementary
            if ana_cat1 and ana_cat2 and ana_cat1 != ana_cat2:
                # Sort product IDs to avoid duplicates
                if p1 < p2:
                    co_occurrence[(p1, p2)] += 1
                else:
                    co_occurrence[(p2, p1)] += 1
    
    print(f"Found {len(co_occurrence)} cross-category co-occurrences")
    
    # Calculate metrics
    print("Calculating association metrics...")
    associations = []
    
    for (p1, p2), co_occurrence_count in co_occurrence.items():
        support = co_occurrence_count / total_baskets
        
        if support < min_support:
            continue
            
        confidence_p1_to_p2 = co_occurrence_count / product_counts[p1] if product_counts[p1] > 0 else 0
        confidence_p2_to_p1 = co_occurrence_count / product_counts[p2] if product_counts[p2] > 0 else 0
        
        # Average confidence
        confidence = (confidence_p1_to_p2 + confidence_p2_to_p1) / 2
        
        if confidence < min_confidence:
            continue
            
        # Calculate lift: higher than 1.0 means positive association
        expected_support = (product_counts[p1] / total_baskets) * (product_counts[p2] / total_baskets)
        lift = (co_occurrence_count / total_baskets) / expected_support if expected_support > 0 else 0
        
        if lift < min_lift:
            continue
        
        associations.append({
            'urun_id_1': p1,
            'urun_id_2': p2,
            'ortak_fis_sayisi': co_occurrence_count,
            'confidence': confidence,
            'lift': lift,
            'support': support,
            'confidence_p1_to_p2': confidence_p1_to_p2,
            'confidence_p2_to_p1': confidence_p2_to_p1
        })
    
    print(f"Generated {len(associations)} cross-category associations")
    
    # Sort by co-occurrence count first, then lift
    associations.sort(key=lambda x: (x['ortak_fis_sayisi'], x['lift']), reverse=True)
    
    # Convert to DataFrame
    associations_df = pd.DataFrame(associations)
    
    if len(associations_df) == 0:
        print("WARNING: No associations found with current thresholds!")
        return associations_df
    
    # Add product details
    associations_df = associations_df.merge(
        products_df[['id', 'urun_adi', 'ana_kategori', 'marka_adi']], 
        left_on='urun_id_1', 
        right_on='id', 
        how='left'
    )
    associations_df = associations_df.rename(columns={
        'urun_adi': 'urun_1_adi',
        'ana_kategori': 'urun_1_kategori',
        'marka_adi': 'urun_1_marka'
    })
    
    associations_df = associations_df.merge(
        products_df[['id', 'urun_adi', 'ana_kategori', 'marka_adi']], 
        left_on='urun_id_2', 
        right_on='id', 
        how='left'
    )
    associations_df = associations_df.rename(columns={
        'urun_adi': 'urun_2_adi',
        'ana_kategori': 'urun_2_kategori',
        'marka_adi': 'urun_2_marka'
    })
    
    # Select and reorder columns
    final_columns = [
        'urun_id_1', 'urun_1_adi', 'urun_1_kategori', 'urun_1_marka',
        'urun_id_2', 'urun_2_adi', 'urun_2_kategori', 'urun_2_marka',
        'ortak_fis_sayisi', 'confidence', 'lift', 'support'
    ]
    associations_df = associations_df[final_columns]
    
    conn.close()
    return associations_df

def update_urun_birliktelikleri_table():
    """
    Update the UrunBirliktelikleri table with cross-category associations only
    """
    print("Starting cross-category product association analysis...")
    
    # Calculate associations - use higher thresholds for initial testing
    associations_df = calculate_cross_category_associations(
        min_support=0.01,       # Higher support threshold for faster processing
        min_confidence=0.1,     # Higher confidence threshold
        min_lift=1.5           # Higher lift threshold
    )
    
    if len(associations_df) == 0:
        print("No associations to write to database")
        return
    
    print(f"Generated {len(associations_df)} cross-category associations")
    print("\nSample associations:")
    print(associations_df.head(10)[['urun_1_adi', 'urun_2_adi', 'urun_1_kategori', 'urun_2_kategori', 'lift']].to_string(index=False))
    
    # Connect to database
    from models import get_connection, DB_BACKEND
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\nClearing existing urunbirliktelikleri table...")
    cursor.execute("DELETE FROM urunbirliktelikleri")
    
    print("Writing new cross-category associations...")
    inserted_count = 0
    
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
    for _, row in associations_df.iterrows():
        cursor.execute(f"""
            INSERT INTO urunbirliktelikleri 
            (urun_id_1, urun_id_2, confidence, lift, ortak_fis_sayisi, tip, analiz_tarihi)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {now_func})
        """, [
            row['urun_id_1'],
            row['urun_id_2'], 
            round(row['confidence'], 4),
            round(row['lift'], 2),
            row['ortak_fis_sayisi'],
            'CROSS_CATEGORY_FP_GROWTH'
        ])
        inserted_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully updated urunbirliktelikleri table with {inserted_count} cross-category associations!")
    print("These associations focus on complementary products from DIFFERENT categories")
    print("Examples: pasta + tomato sauce, yogurt + granola, coffee + milk")
    
    # Show category distribution
    print("\n📊 Category distribution of associations:")
    category_pairs = associations_df.groupby(['urun_1_kategori', 'urun_2_kategori']).size().sort_values(ascending=False)
    for (cat1, cat2), count in category_pairs.head(10).items():
        print(f"  {cat1} + {cat2}: {count} associations")

if __name__ == "__main__":
    update_urun_birliktelikleri_table()