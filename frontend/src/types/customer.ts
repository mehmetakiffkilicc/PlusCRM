export interface BeklenenMusteri {
    musteri_id: number
    ad_soyad: string | null
    telefon: string | null
    rfm_segment: string | null
    ort_aralik_gun: number
    toplam_ziyaret: number
    son_ziyaret_tarihi: string | null
    tahmini_ziyaret_tarihi: string | null
    gecikme_gun: number
    guven_skoru: string | null
    durum: string | null
    toplam_harcama: number
    ortalama_sepet_tutari: number
    tahmini_alisveris_tutari: number
    magaza_id?: string | null
    magaza_adi?: string | null
}

export interface BeklenenMusteriResponse {
    toplam: number
    musteriler: BeklenenMusteri[]
}

export interface Customer {
    id: number
    ad: string
    telefon: string
    tip: string
    rfm_segment: string
    kayit_tarihi: string
}

export interface CustomerDetail {
    info: any
    kpis: {
        total_visits: number
        total_spend: number
        total_units: number
        last_shopping_date: string
        first_shopping_date: string
        avg_basket: number
        ltv: number
        churn_risk: number
        trend: string
        activity_status: string
        fav_category: string
        fav_brand: string
        fav_store: string
        fav_product: string
        preferred_hour: string
        preferred_day: string
        spend_30d: number
        spend_90d: number
        loyalty_ratio: number
        morning_count: number
        noon_count: number
        evening_count: number
        night_count: number
        churn_reason?: string
        days_since_last_visit?: number
        visits_30d?: number
        visits_90d?: number
        customer_age_days?: number
        basket_diversity?: number
    }
    fav_brands: any[]
    fav_categories: any[]
    history: any[]
    time_dist: any[]
    day_distribution?: { day_name: string; day_num: number; count: number; total_spend: number }[]
    spending_trend?: { week: string; week_start: string; total_spend: number; visit_count: number }[]
    rfm_scores?: { recency: number; frequency: number; monetary: number; segment: string }
    campaign_suggestions?: { type: string; title: string; description: string; priority: string; icon: string }[]
    hybrid_recommendations?: any[]
    category_distribution?: { name: string; revenue: number }[]
    last_receipt?: {
        fis_no: string
        date: string
        time: string
        store: string
        total: number
        items: any[]
    }
    associations?: any[]
    fis_listesi?: any[]
    total_fis?: number
    labels?: any
    churn_skoru?: number | null
    segment_benchmark?: { avg_basket: number; avg_spend: number; avg_visits: number; customer_count: number }
    cross_sell_cats?: { kategori_ad: string; alt_kategori?: string; ana_kategori?: string; confidence: number; lift: number }[]
    fiyat_ozeti?: {
        indirim_oran_yuzde: number
        ort_indirim_yuzde: number
        toplam_indirim_tutari: number
        toplam_brut_tutar: number
        hassasiyet_seviye: 'Yüksek' | 'Orta' | 'Düşük'
        onerilen_indirim_araligi: string
    } | null
    donem_karsilastirma?: {
        harcama_3ay: number
        harcama_onceki3ay: number
        harcama_degisim_3ay: number
        ziyaret_3ay: number
        ziyaret_onceki3ay: number
        ziyaret_degisim_3ay: number
        harcama_degisim_6ay: number
        ziyaret_degisim_6ay: number
        terk_edilen_kategori: number
    } | null
    kategori_dagilimi?: {
        ana_kategori: string
        fis_sayisi: number
        toplam_harcama: number
        alt_kategori_sayisi: number
        oran: number
    }[]
}
