import streamlit as st
import requests
from datetime import datetime

# --- KONFIGURACJA ---
TOKEN = "DkgtaLqFUQ85WTQbPYRuCtR7C99CS5cwTM8sUbSudGssIRYMoA9HBLgu9AOf"
LIGI = {8: "Ligue 1", 564: "Serie A", 301: "La Liga", 82: "Bundesliga", 501: "Eredivisie", 462: "Ekstraklasa", 2: "Premier League", 271: "Superliga"}

st.set_page_config(page_title="Value Hunter PRO", layout="wide")

def get_value_stats(team_id, side):
    url = f"https://api.sportmonks.com/v3/football/teams/{team_id}?api_token={TOKEN}&include=latest.scores;latest.statistics;latest.participants"
    try:
        r = requests.get(url).json()
        fixtures = r.get('data', {})
        if not isinstance(fixtures, list):
            fixtures = fixtures.get('latest', [])
        
        relevant = []
        for f in fixtures:
            participants = f.get('participants', [])
            is_home = any(p['id'] == team_id and p.get('meta', {}).get('location') == 'home' for p in participants)
            if (side == "home" and is_home) or (side == "away" and not is_home):
                relevant.append(f)
            if len(relevant) == 8: break

        if len(relevant) < 3: return 0, 0, 0, False
        
        # Średnia długoterminowa (8 meczów)
        long_term_goals = 0
        for f in relevant:
            s = f.get('scores', [])
            long_term_goals += sum(int(x.get('score', {}).get('goals', 0)) for x in s if x.get('description') in ['FT', 'CURRENT'])
        avg_long = long_term_goals / len(relevant)
        
        # Średnia krótkoterminowa (ostatnie 2 mecze)
        short_term_goals = 0
        for f in relevant[:2]:
            s = f.get('scores', [])
            short_term_goals += sum(int(x.get('score', {}).get('goals', 0)) for x in s if x.get('description') in ['FT', 'CURRENT'])
        avg_short = short_term_goals / 2
        
        # Sygnał Value: Średnia z 2 meczów jest znacznie niższa niż z 8
        is_underperforming = avg_short < (avg_long * 0.75)
        
        return avg_long, avg_short, 0, is_underperforming
    except:
        return 0, 0, 0, False

st.title("🏹 Value Hunter: Strategia Przełamania")

with st.sidebar:
    st.header("Ustawienia Strategii")
    wybrana_data = st.date_input("Dzień", datetime.now())
    min_avg_sezon = st.slider("Min. Średnia Sezonowa", 1.5, 4.0, 2.5)
    tylko_value = st.checkbox("Tylko sygnały VALUE", value=True)

if klik := st.button("🚀 SKANUJ MECZE"):
    dzien = wybrana_data.strftime('%Y-%m-%d')
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{dzien}?api_token={TOKEN}&include=participants"
    
    with st.spinner('Przeszukuję historię pod kątem regresji...'):
        res = requests.get(url).json()
        mecze = res.get('data', [])
        found = False
        
        for m in mecze:
            if m.get('league_id') in LIGI:
                p = m.get('participants', [])
                if len(p) < 2: continue
                
                h_team = p[0] if p[0].get('meta', {}).get('location') == 'home' else p[1]
                a_team = p[1] if h_team == p[0] else p[0]
                
                avg_l_h, avg_s_h, _, val_h = get_value_stats(h_team['id'], "home")
                avg_l_a, avg_s_a, _, val_a = get_value_stats(a_team['id'], "away")
                
                srednia_starcia = (avg_l_h + avg_l_a) / 2
                
                if srednia_starcia >= min_avg_sezon:
                    if tylko_value and not (val_h or val_a):
                        continue
                        
                    found = True
                    with st.expander(f"💎 {h_team['name']} vs {a_team['name']} | Średnia: {round(srednia_starcia, 2)}", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"🏠 **{h_team['name']}**")
                            st.write(f"Sezon: {round(avg_l_h, 2)} | Ostatnie 2: {round(avg_s_h, 2)}")
                            if val_h: st.error("📉 NIEDOSZACOWANIE")
                            
                        with col2:
                            st.write(f"🚀 **{a_team['name']}**")
                            st.write(f"Sezon: {round(avg_l_a, 2)} | Ostatnie 2: {round(avg_s_a, 2)}")
                            if val_a: st.error("📉 NIEDOSZACOWANIE")
                            
                        if val_h and val_a:
                            st.success("🔥 DOUBLE VALUE ALERT - Idealny mecz pod przełamanie serii!")
                        st.divider()
        if not found: st.info("Brak meczów z dołkiem formy na ten dzień.")
        