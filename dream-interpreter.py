import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import time
from datetime import datetime
import re

# Konfigurasi halaman
st.set_page_config(
    page_title="🌙 Dream Interpreter - AI Penafsir Mimpi",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan yang menarik
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .dream-input {
        background-color: #f8f9fc;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .interpretation-box {
        background-color: #fff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #764ba2;
    }
    .symbol-card {
        background: #f1f3f4;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .dream-journal-entry {
        background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: #2d3436;
    }
</style>
""", unsafe_allow_html=True)

# Header aplikasi
st.markdown("""
<div class="main-header">
    <h1>🌙 Dream Interpreter AI</h1>
    <p>Jelajahi makna tersembunyi di dalam mimpi Anda dengan bantuan AI dan psikologi</p>
</div>
""", unsafe_allow_html=True)

# Load database symbols (dalam aplikasi nyata, ini akan dari file CSV)
@st.cache_data
def load_dream_symbols():
    """Load database simbol mimpi"""
    try:
        df = pd.read_csv("dream_symbols.csv")
        symbols = {}
        for _, row in df.iterrows():
            symbols[row['symbol']] = {
                "meaning": row['meaning'],
                "contexts": json.loads(row['contexts'])
            }
        return symbols
    except FileNotFoundError:
        st.error("File 'dream_symbols.csv' tidak ditemukan. Pastikan file berada di folder yang sama.")
        return {}


def find_dream_symbols(dream_text, symbols_db):
    """Mencari simbol-simbol dalam teks mimpi"""
    found_symbols = []
    dream_lower = dream_text.lower()
    
    for symbol, data in symbols_db.items():
        if symbol in dream_lower:
            found_symbols.append({
                "symbol": symbol,
                "meaning": data["meaning"],
                "contexts": data["contexts"]
            })
            
        # Cek konteks spesifik
        for context, meaning in data["contexts"].items():
            if context in dream_lower:
                found_symbols.append({
                    "symbol": f"{symbol} ({context})",
                    "meaning": meaning,
                    "contexts": {}
                })
    
    return found_symbols

def safe_gemini_call(prompt, api_key):
    """Panggil Gemini API dengan rate limiting"""
    if not api_key:
        return "⚠️ API Key Gemini belum dimasukkan. Silakan masukkan di sidebar."
    
    # Rate limiting check
    if 'last_api_call' in st.session_state:
        time_diff = time.time() - st.session_state.last_api_call
        if time_diff < 12:  # 5 RPM = 12 detik interval
            return f"⏳ Tunggu {12-time_diff:.1f} detik lagi untuk menghindari batas API..."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        st.session_state.last_api_call = time.time()
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        return f"❌ Error calling Gemini API: {str(e)}"

# Sidebar untuk konfigurasi
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    # API Key input
    api_key = st.text_input("🔑 Gemini API Key", type="password", help="Dapatkan API key gratis di https://ai.google.dev/")
    
    # Mode interpretasi
    st.subheader("🎯 Mode Interpretasi")
    interpretation_mode = st.selectbox(
        "Pilih pendekatan interpretasi:",
        ["Psikologi Umum", "Jungian", "Freudian", "Simbolisme Budaya", "Personal Growth"]
    )
    
    # Pengaturan tambahan
    st.subheader("🔧 Pengaturan Lanjutan")
    include_emotions = st.checkbox("Analisis emosi dalam mimpi", value=True)
    include_symbols = st.checkbox("Deteksi simbol otomatis", value=True)
    save_to_journal = st.checkbox("Simpan ke jurnal mimpi", value=True)
    
    # Statistik penggunaan
    if 'total_interpretations' not in st.session_state:
        st.session_state.total_interpretations = 0
    
    st.subheader("📊 Statistik")
    st.metric("Total Interpretasi", st.session_state.total_interpretations)
    
    if 'api_calls_today' not in st.session_state:
        st.session_state.api_calls_today = 0
    st.metric("API Calls Hari Ini", st.session_state.api_calls_today)
    st.progress(min(st.session_state.api_calls_today / 250, 1.0))  # Free tier limit

# Initialize session state
if 'dream_journal' not in st.session_state:
    st.session_state.dream_journal = []

if 'current_interpretation' not in st.session_state:
    st.session_state.current_interpretation = None

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💭 Ceritakan Mimpi Anda")
    
    with st.container():
        st.markdown('<div class="dream-input">', unsafe_allow_html=True)
        
        dream_text = st.text_area(
            "Ketik detail mimpi Anda di sini...",
            height=200,
            placeholder="Contoh: Saya bermimpi terbang di atas laut yang jernih, lalu tiba-tiba jatuh ke dalam air yang dalam...",
            help="Semakin detail mimpi yang Anda ceritakan, semakin akurat interpretasinya"
        )
        
        # Input tambahan untuk konteks
        st.subheader("🎯 Konteks Tambahan (Opsional)")
        
        col_emotion, col_context = st.columns(2)
        
        with col_emotion:
            dream_emotion = st.selectbox(
                "Perasaan dominan dalam mimpi:",
                ["Tidak yakin", "Bahagia", "Takut", "Sedih", "Marah", "Bingung", "Tenang", "Cemas", "Excited", "Nostalgic"]
            )
        
        with col_context:
            life_situation = st.text_input(
                "Situasi hidup saat ini:",
                placeholder="Contoh: Sedang mencari kerja, baru putus, stress kerja..."
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.subheader("🔮 Quick Symbols")
    
    # Load symbols
    symbols_db = load_dream_symbols()
    
    if dream_text and include_symbols and symbols_db:
        found_symbols = find_dream_symbols(dream_text, symbols_db)
        
        if found_symbols:
            st.write("**Simbol yang terdeteksi:**")
            for symbol in found_symbols[:3]:  # Limit to 3 symbols
                with st.expander(f"🎭 {symbol['symbol'].title()}"):
                    st.write(symbol['meaning'])
        else:
            st.info("Tidak ada simbol umum yang terdeteksi. Gunakan interpretasi AI untuk analisis lengkap.")
    
    # Tips interpretasi cepat
    st.subheader("💡 Tips Interpretasi")
    st.info("🌟 **Ingat:** Mimpi sangat personal. AI ini memberikan panduan umum, tapi makna sesungguhnya tergantung pada pengalaman dan perasaan Anda sendiri.")

# Tombol interpretasi
if st.button("🔍 Interpretasikan Mimpi Saya", type="primary", use_container_width=True):
    if not dream_text.strip():
        st.error("❌ Mohon ceritakan mimpi Anda terlebih dahulu!")
    else:
        with st.spinner("🤖 AI sedang menganalisis mimpi Anda..."):
            # Buat prompt untuk Gemini
            prompt = f"""
            Anda adalah AI Dream Interpreter yang ahli dalam psikologi dan analisis mimpi. 
            
            Pendekatan interpretasi: {interpretation_mode}
            
            Detail mimpi:
            "{dream_text}"
            
            Perasaan dominan: {dream_emotion}
            Konteks hidup: {life_situation if life_situation else 'Tidak disebutkan'}
            
            Berikan interpretasi yang:
            1. Menganalisis simbol-simbol utama dalam mimpi
            2. Menjelaskan kemungkinan makna psikologis
            3. Menghubungkan dengan konteks hidup saat ini (jika ada)
            4. Memberikan insight untuk pengembangan diri
            5. Menggunakan bahasa Indonesia yang mudah dipahami
            
            Struktur respons:
            
            ## 🔮 Interpretasi Utama
            [Makna keseluruhan mimpi]
            
            ## 🎭 Analisis Simbol
            [Analisis simbol-simbol penting]
            
            ## 💡 Insight & Saran
            [Insight untuk kehidupan sehari-hari]
            
            ## ⚡ Aksi yang Bisa Diambil
            [Saran praktis berdasarkan interpretasi]
            
            Ingat: Interpretasi mimpi bersifat personal dan subjektif. Gunakan ini sebagai panduan untuk refleksi diri.
            """
            
            # Call Gemini API
            interpretation = safe_gemini_call(prompt, api_key)
            
            # Simpan interpretasi
            st.session_state.current_interpretation = {
                "dream": dream_text,
                "interpretation": interpretation,
                "emotion": dream_emotion,
                "context": life_situation,
                "timestamp": datetime.now(),
                "mode": interpretation_mode
            }
            
            # Update counters
            st.session_state.total_interpretations += 1
            st.session_state.api_calls_today += 1
            
            # Simpan ke jurnal jika diaktifkan
            if save_to_journal:
                st.session_state.dream_journal.append(st.session_state.current_interpretation)

# Display interpretation
if st.session_state.current_interpretation:
    st.markdown("---")
    st.subheader("📖 Hasil Interpretasi")
    
    with st.container():
        st.markdown('<div class="interpretation-box">', unsafe_allow_html=True)
        
        # Tampilkan interpretasi
        if st.session_state.current_interpretation['interpretation'].startswith('⚠️') or \
           st.session_state.current_interpretation['interpretation'].startswith('⏳') or \
           st.session_state.current_interpretation['interpretation'].startswith('❌'):
            st.error(st.session_state.current_interpretation['interpretation'])
        else:
            st.markdown(st.session_state.current_interpretation['interpretation'])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tombol aksi
        col_save, col_share, col_new = st.columns(3)
        
        with col_save:
            if st.button("💾 Simpan ke Jurnal"):
                if st.session_state.current_interpretation not in st.session_state.dream_journal:
                    st.session_state.dream_journal.append(st.session_state.current_interpretation)
                    st.success("✅ Disimpan ke jurnal!")
        
        with col_share:
            interpretation_text = f"""
            Mimpi: {st.session_state.current_interpretation['dream'][:100]}...
            
            Interpretasi: {st.session_state.current_interpretation['interpretation'][:200]}...
            
            Generated by Dream Interpreter AI
            """
            st.download_button("📤 Download Interpretasi", interpretation_text, file_name=f"dream_interpretation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with col_new:
            if st.button("🔄 Interpretasi Baru"):
                st.session_state.current_interpretation = None
                st.rerun()

# Dream Journal Section
if st.session_state.dream_journal:
    st.markdown("---")
    st.subheader("📔 Jurnal Mimpi Anda")
    
    # Statistik jurnal
    total_dreams = len(st.session_state.dream_journal)
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        st.metric("Total Mimpi", total_dreams)
    
    with col_stats2:
        emotions = [dream['emotion'] for dream in st.session_state.dream_journal if dream['emotion'] != 'Tidak yakin']
        if emotions:
            most_common_emotion = max(set(emotions), key=emotions.count)
            st.metric("Emosi Tersering", most_common_emotion)
    
    with col_stats3:
        modes = [dream['mode'] for dream in st.session_state.dream_journal]
        if modes:
            most_used_mode = max(set(modes), key=modes.count)
            st.metric("Mode Tersering", most_used_mode)
    
    # Tampilkan jurnal
    for i, dream in enumerate(reversed(st.session_state.dream_journal[-5:])):  # Show last 5 dreams
        with st.expander(f"🌙 Mimpi #{total_dreams-i} - {dream['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
            st.markdown(f"**Mimpi:** {dream['dream'][:200]}{'...' if len(dream['dream']) > 200 else ''}")
            st.markdown(f"**Emosi:** {dream['emotion']} | **Mode:** {dream['mode']}")
            
            if st.button(f"Lihat Interpretasi Lengkap", key=f"view_{i}"):
                st.markdown('<div class="dream-journal-entry">', unsafe_allow_html=True)
                st.markdown(dream['interpretation'])
                st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8em;">
    <p>🌙 Dream Interpreter AI - Dibuat dengan ❤️ menggunakan Streamlit & Gemini API</p>
    <p>⚠️ Interpretasi mimpi bersifat subjektif dan untuk tujuan hiburan/refleksi diri. Tidak menggantikan konsultasi profesional.</p>
</div>
""", unsafe_allow_html=True)
