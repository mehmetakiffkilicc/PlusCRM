import React, { ReactNode } from 'react';

export interface LabelCategory {
    key: string;
    ad: string;
    renk: string;
    icon: ReactNode;
    etiketler: { label: string; value: string }[];
}

export const LABEL_KATEGORILER: LabelCategory[] = [
    { key: 'ziyaret', ad: 'Ziyaret Davranışı', renk: '#6366f1', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>,
      etiketler: [
        { label: 'Sabah Alışverişçisi', value: 'sabah_alisveriscisi' },
        { label: 'Akşam Alışverişçisi', value: 'aksam_alisveriscisi' },
        { label: 'Gece Alışverişçisi', value: 'gece_alisveriscisi' },
        { label: 'Hafta Sonu Alışverişçisi', value: 'hafta_sonu_alisveriscisi' },
        { label: 'Hafta İçi Alışverişçisi', value: 'hafta_ici_alisveriscisi' },
        { label: 'Aylık Düzenli Alıcı', value: 'aylik_duzenli_alici' },
        { label: 'Maaş Günü Alışverişçisi', value: 'maas_gunu_alisveriscisi' },
        { label: 'Günlük Uğrayan', value: 'gunluk_ugrayan' },
        { label: 'Seyrek Alışverişçi', value: 'seyrek_alisverisci' },
    ]},
    { key: 'sepet', ad: 'Sepet & Harcama', renk: '#10b981', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>,
      etiketler: [
        { label: 'Büyük Sepet Alışverişçisi', value: 'buyuk_sepet_alisveriscisi' },
        { label: 'Küçük Sepet Alışverişçisi', value: 'kucuk_sepet_alisveriscisi' },
        { label: 'Premium Harcayıcı', value: 'premium_harcayici' },
        { label: 'Ekonomik Harcayıcı', value: 'ekonomik_harcayici' },
        { label: 'B2B Mahalle Esnafı', value: 'b2b_mahalle_esnafi' },
        { label: 'Stokçu Alıcı', value: 'stokcu_alici' },
        { label: 'Tekli Ürün Alışverişçisi', value: 'tekli_urun_alisveriscisi' },
    ]},
    { key: 'fiyat', ad: 'Fiyat & Kampanya', renk: '#f59e0b', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>,
      etiketler: [
        { label: 'İndirim Avcısı', value: 'indirim_avcisi' },
        { label: 'Promosyon Bağımlı', value: 'promosyon_bagimli' },
        { label: 'Fiyat Hassas', value: 'fiyat_hassas' },
        { label: 'Fiyata Duyarsız', value: 'fiyata_duyarsiz' },
        { label: 'Çoklu Alım Fırsatçısı', value: 'coklu_alim_firsatcisi' },
        { label: 'Enflasyon Stokçusu', value: 'enflasyon_stokcusu' },
        { label: 'Kampanya Tepkisi Düşük', value: 'kampanya_tepkisi_dusuk' },
    ]},
    { key: 'taze_gida', ad: 'Taze Gıda', renk: '#22c55e', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><path d="M12 2a10 10 0 100 20A10 10 0 0012 2z"/><path d="M12 6v6l4 2"/></svg>,
      etiketler: [
        { label: 'Kasap Odaklı', value: 'kasap_odakli' },
        { label: 'Manav Odaklı', value: 'manav_odakli' },
        { label: 'Fırıncı Odaklı', value: 'firinci_odakli' },
        { label: 'Şarküteri Odaklı', value: 'sarkuteri_odakli' },
        { label: 'Sadece Taze Gıdacı', value: 'sadece_taze_gidaci' },
        { label: 'Yöresel Ürün Meraklısı', value: 'yoresel_urun_meraklisi' },
        { label: 'Taze Gıda Kaçınanı', value: 'taze_gida_kacinani' },
    ]},
    { key: 'kategori', ad: 'Kategori İlgileri', renk: '#8b5cf6', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>,
      etiketler: [
        { label: 'Sağlıklı Yaşam Eğilimli', value: 'saglikli_yasam_egilimli' },
        { label: 'Hazır Tüketim Eğilimli', value: 'hazir_tuketim_egilimli' },
        { label: 'Protein Odaklı', value: 'protein_odakli' },
        { label: 'Kafein Yoğun Tüketici', value: 'kafein_yogun_tuketici' },
        { label: 'Atıştırmalık Tüketicisi', value: 'atistirmalik_tuketicisi' },
        { label: 'Temizlik & Hijyen Odaklı', value: 'temizlik_hijyen_odakli' },
        { label: 'Kişisel Bakım Tutkunu', value: 'kisisel_bakim_tutkunu' },
        { label: 'Misafir Sofrası Kurucusu', value: 'misafir_sofrasi_kurucusu' },
    ]},
    { key: 'kanal', ad: 'Kanal & Kampanya Tepkisi', renk: '#3b82f6', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
      etiketler: [
        { label: 'Winback Adayı', value: 'winback_adayi' },
        { label: 'Reaktivasyon Potansiyeli', value: 'reaktivasyon_potansiyeli' },
        { label: 'Yeniden Kazanılmış', value: 'yeniden_kazanilmis' },
        { label: 'Kampanya Duyarlı', value: 'kampanya_duyarli' },
        { label: 'Kampanyasız Sadık', value: 'kampanyasiz_sadik' },
    ]},
    { key: 'odeme', ad: 'Ödeme & Finansal', renk: '#06b6d4', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
      etiketler: [
        { label: 'Yemek Kartı Kullanıcısı', value: 'yemek_karti_kullanicisi' },
        { label: 'Ay Sonu YK Harcayıcısı', value: 'ay_sonu_yemek_karti_harcayicisi' },
        { label: 'Fatura Müşterisi', value: 'fatura_musterisi' },
    ]},
    { key: 'sadakat', ad: 'Sadakat & Risk', renk: '#ef4444', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
      etiketler: [
        { label: 'Sadık Müşteri', value: 'sadik_musteri' },
        { label: 'Soğuyan Müşteri', value: 'soguyan_musteri' },
        { label: 'Kaybedilme Riski Yüksek', value: 'kaybedilme_riski_yuksek' },
        { label: 'Tamamen Kaybedilmiş', value: 'tamamen_kaybedilmis' },
        { label: 'Yeniden Kazanılmış', value: 'yeniden_kazanilmis_saglik' },
        { label: 'Gidip Gelen Müşteri', value: 'gidip_gelen_musteri' },
        { label: 'Sepeti Daralan', value: 'sepeti_daralan' },
        { label: 'Kategori Terk Eden', value: 'kategori_terk_eden' },
        { label: 'Marjı Düşüren', value: 'marji_dusuran' },
        { label: 'Gizli Risk', value: 'gizli_risk' },
        { label: '⭐ Kaybedilmemesi Gereken', value: 'kaybedilmemesi_gereken' },
    ]},
    { key: 'hane', ad: 'Hane Yapısı', renk: '#ec4899', icon: <svg xmlns="http://www.w3.org/2000/svg" width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
      etiketler: [
        { label: 'Bekar Hanesi', value: 'hane_bekar_skoru' },
        { label: 'Çift Hanesi', value: 'hane_cift_skoru' },
        { label: 'Aile Hanesi', value: 'hane_aile_skoru' },
        { label: 'Çocuklu Hane', value: 'hane_cocuklu_skoru' },
        { label: 'Bebekli Hane', value: 'hane_bebek_skoru' },
        { label: 'Yaşlı Hanesi', value: 'hane_yasli_skoru' },
        { label: 'Evcil Hayvanlı', value: 'hane_evcil_hayvan_skoru' },
        { label: 'Arabalı Hane', value: 'hane_araba_skoru' },
        { label: 'Toplu Alıcı Hanesi', value: 'hane_toplu_alim_skoru' },
    ]},
];

export const LABEL_DISPLAY: Record<string, string> = Object.fromEntries(
    LABEL_KATEGORILER.flatMap(k => k.etiketler.map(e => [e.value, e.label]))
);
