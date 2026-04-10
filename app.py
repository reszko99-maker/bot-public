import streamlit as st
import requests
from datetime import datetime

# --- KONFIGURACJA ---
TOKEN = "DkgtaLqFUQ85WTQbPYRuCtR7C99CS5cwTM8sUbSudGssIRYMoA9HBLgu9AOf"
LIGI = {
    8: "Ligue 1", 
    564: "Serie A", 
    301: "La Liga", 
    82: "Bundesliga", 
    501: "Eredivisie", 
    462: "Ekstraklasa", 
    2: "Premier League", 
    271: "Superliga"
}

st.set_page_config(page_title="Value Hunter PRO", layout="wide")

# --- FUNKCJA: ANALIZA MOTYWACJI (V3 API) ---
def get_motivation(league_id, home_id, away_id):
    url = f"https://api.sportmonks.com/v3/football/standings/leagues/{league_id}?api_token={TOKEN}"
    try:
        r = requests.get(url).json()
        data = r.get('data', [])
        
        # Inicjalizacja domyślna
        home_m, away_m = (1, "Standardowa"), (1, "Standardowa")
        standings = []

        # Sportmonks v3 zwraca listę, gdzie każdy element to tabela grupy/ligi
        if isinstance(data, list) and len(data) > 0:
            standings = data[0].get('standings', [])
        
        if not standings:
            return (1, "Brak danych"), (1, "Brak danych")

        total_teams = len(standings)
        
        for s in standings:
            # W v3 klucz to często 'participant_id'
            t_id = s.get('participant_id')
            pos = s.get('position')
            
            status = 1
            desc = "Standardowa"
            
            # Logika motywacji
            if pos <= 5: 
                status, desc = 2, "🔥 Puchary/Mistrzostwo"
            elif pos > (total_teams - 4): 
                status, desc = 2, "⚠️ Walka o utrzymanie"
            elif (total_teams // 2 - 2) <= pos <= (total_teams // 2 + 2): 
                status, desc = 0, "🏖️ Środek tabeli (brak celu)"
            
            if t_id == home_id: home_m = (status, desc)
            if t_id == away_id: away_m = (status, desc)
            
        return home_m, away_m
    except:
        return (1, "Błąd danych"), (1, "Błąd danych")

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
        
        long_term_goals = 0
        for f in relevant:
            s = f.get('scores', [])
            long_term_goals += sum(int(x.get('score', {}).get('goals', 0)) for x in s if x.get('description') in ['FT', 'CURRENT'])
        avg_long = long_term_goals / len(relevant)
        
        short_term_goals = 0
        for f in relevant[:2]:
            s = f.get('scores', [])
            short_term_goals += sum(int(x.get('score', {}).get('goals', 0)) for x in s if x.get('description') in ['FT', 'CURRENT'])
        avg_short = short_term_goals / 2
        
        is_underperforming = avg_short < (avg_long * 0.75)
        return avg_long, avg_short, 0, is_underperforming
    except:
        return 0, 0, 0, False

# --- UI ---
st.title("🏹 Value Hunter: Strategia Przełamania & Motywacji")

with st.sidebar:
    st.header("Ustawienia Strategii")
    wybrana_data = st.date_input("Dzień", datetime.now())
    min_avg_sezon = st.slider("Min. Średnia Sezonowa", 1.5, 4.0, 2.5)
    tylko_value = st.checkbox("Tylko sygnały VALUE", value=False)

if st.button("🚀 SKANUJ MECZE"):
    dzien = wybrana_data.strftime('%Y-%m-%d')
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{dzien}?api_token={TOKEN}&include=participants"
    
    with st.spinner('Analizuję formę i sytuację w tabeli...'):
        res = requests.get(url).json()
        mecze = res.get('data', [])
        found = False
        
        for m in mecze:
            l_id = m.get('league_id')
            if l_id in LIGI:
                p = m.get('participants', [])
                if len(p) < 2: continue
                
                # Rozpoznanie Home/Away
                h_team = p[0] if p[0].get('meta', {}).get('location') == 'home' else p[1]
                a_team = p[1] if h_team == p[0] else p[0]
                
                # Staty goli
                avg_l_h, avg_s_h, _, val_h = get_value_stats(h_team['id'], "home")
                avg_l_a, avg_s_a, _, val_a = get_value_stats(a_team['id'], "away")
                
                # Motywacja
                h_mot, a_mot = get_motivation(l_id, h_team['id'], a_team['id'])
                
                srednia_starcia = (avg_l_h + avg_l_a) / 2
                
                if srednia_starcia >= min_avg_sezon:
                    if tylko_value and not (val_h or val_a):
                        continue
                        
                    found = True
                    with st.expander(f"💎 {h_team['name']} vs {a_team['name']} | Średnia: {round(srednia_starcia, 2)}", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader(f"🏠 {h_team['name']}")
                            st.info(f"Sytuacja: {h_mot[1]}")
                            st.write(f"Sezon: {round(avg_l_h, 2)} | Ostatnie 2: {round(avg_s_h, 2)}")
                            if val_h: st.error("📉 NIEDOSZACOWANIE")
                            
                        with col2:
                            st.subheader(f"🚀 {a_team['name']}")
                            st.info(f"Sytuacja: {a_mot[1]}")
                            st.write(f"Sezon: {round(avg_l_a, 2)} | Ostatnie 2: {round(avg_s_a, 2)}")
                            if val_a: st.error("📉 NIEDOSZACOWANIE")
                        
                        # ALERTY SPECJALNE
                        st.divider()
                        
                        # Alert motywacyjny (jeden musi, drugi na wakacjach)
                        if (h_mot[0] == 2 and a_mot[0] == 0) or (a_mot[0] == 2 and h_mot[0] == 0):
                            st.warning(f"⚠️ **ALIBI ALERT:** {h_team['name'] if h_mot[0]==2 else a_team['name']} walczy o stawkę, podczas gdy rywal nie ma już ciśnienia na wynik.")
                        
                        if val_h and val_a:
                            st.success("🔥 **DOUBLE VALUE ALERT** - Obie drużyny poniżej średniej bramkowej. Idealne na przełamanie!")

        if not found: 
            st.info("Brak meczów spełniających kryteria na ten dzień.")
