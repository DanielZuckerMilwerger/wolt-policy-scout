import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import feedparser

# Base Settings
KEYWORDS = ["שליחים", "עצמאיים", "פלטפורמות", "דו גלגלי", "גיג", "משלוחים", "עסקים קטנים", "עובדים זרים", "מבקשי מקלט", "הקצאת", "תחרות"]
KEYWORDS_EN = ["couriers", "riders", "delivery", "wolt", "gig economy", "freelancers", "small business", "foreign workers"]
NEGATIVE_KEYWORDS = ["כלבת", "נשכו", "תנים", "כלב", "חתול"]
PRIORITY_COMMITTEES = ["הכלכלה", "הכספים", "העבודה", "המדע", "זרים"]

NEWS_FEEDS = [
    ("Davar", "https://www.davar1.co.il/feed/"),
    ("Calcalist", "https://www.calcalist.co.il/GeneralRSS/0,16154,L-8,00.xml"),
    ("Globes", "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederFeed?c=2"),
    ("TheMarker", "https://www.themarker.com/srv/rss/all"),
    ("Ynet", "https://www.ynet.co.il/Integration/StoryRss538.xml"),
    ("Maariv", "https://www.maariv.co.il/Rss/RssFeedsMivzakim"),
    ("MakorRishon", "https://www.makorrishon.co.il/category/news/feed/"),
    ("Kipa", "https://www.kipa.co.il/rss/news.xml"),
    ("TimesOfIsrael", "https://www.timesofisrael.com/il/feed/"),
    ("JPost", "https://www.jpost.com/rss/israelnews")
]

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide", page_icon="🛵")
st.title("Wolt Israel 🛵")
st.subheader("Public Policy Scout")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    password = st.text_input("Enter Access Password:", type="password")
    if password == "WoltPolicy2026":
        st.session_state["authenticated"] = True
        st.success("Accepted! Click Enter:")
        if st.button("Enter"):
            st.rerun()
    elif password:
        st.error("Denied.")
    st.stop()

def analyze_with_gemini(source, category, title):
    if not model: return "No API key."
    prompt = f"You are a public policy manager at Wolt Israel. Analyze this in Hebrew (up to 3 lines) for risks or opportunities: Source: {source}, Category: {category}, Title: {title}"
    try:
        return model.generate_content(prompt).text
    except:
        return "AI temporary unavailable."

def fetch_knesset_data():
    events = []
    try:
        start_dt = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%dT00:00:00')
        url = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Agenda"
        params = {'$filter': f"StartDate ge datetime'{start_dt}'", '$orderby': "StartDate asc", '$top': '999', '$format': "json"}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            for item in res.json().get('value', []):
                session_name = item.get('CommitteeSessionName', '') or ''
                subject = item.get('Subject', '') or ''
                committee = item.get('CommitteeName', '') or 'General'
                txt = f"{session_name} {subject} {committee}"
                
                match_kw = any(w in txt for w in KEYWORDS)
                match_comm = any(c in committee for c in PRIORITY_COMMITTEES)
                
                if match_kw or match_comm:
                    title_to_show = session_name if session_name else subject
                    if not title_to_show: title_to_show = f"Meeting: {committee}"
                    date_parsed = datetime.strptime(item['StartDate'], '%Y-%m-%dT%H:%M:%S')
                    
                    events.append({
                        "source": "Knesset", "cat": committee, "title": title_to_show,
                        "date": date_parsed.strftime('%d/%m/%Y %H:%M'),
                        "priority": "High" if match_comm else "Normal",
                        "link": "https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgendas.aspx"
                    })
    except: pass
    return events

def fetch_tazkirim_data():
    tazkirim = []
    try:
        url = "https://data.gov.il/api/3/action/datastore_search"
        params = {'resource_id': "9207e37d-b6bd-4df5-91db-fc539dfbbf76", 'limit': 50, 'sort': 'PublishDate desc'}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            for item in res.json().get('result', {}).get('records', []):
                title = item.get('TazkirName', '') or item.get('Subject', '') or ''
                if any(w in title for w in KEYWORDS):
                    tazkirim.append({
                        "source": "Tazkirim", "cat": item.get('PublishingMinistry', 'Gov'), "title": title,
                        "date": str(item.get('PublishDate', ''))[:10], "priority": "High", "link": "https://www.tazkirim.gov.il/"
                    })
    except: pass
    return tazkirim

def fetch_news_data():
    news_alerts = []
    try:
        for name, url in NEWS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                full_text = f"{title} {summary}".lower()
                if any(w in full_text for w in KEYWORDS) and not any(nw in full_text for nw in NEGATIVE_KEYWORDS):
                    news_alerts.append({
                        "source": name, "cat": "Media", "title": title, "date": str(entry.get('published', ''))[:16],
                        "priority": "Media Scan", "link": entry.get('link', '')
                    })
    except: pass
    return news_alerts

# Render UI
tab1, tab2, tab3 = st.tabs(["Knesset & Legislation", "PDF Document Scanner", "News Radar"])

with tab1:
    st.write("### Knesset Committees & Government Updates")
    alerts = fetch_knesset_data() + fetch_tazkirim_data()
    if not alerts:
        st.info("No relevant updates found matching Wolt policy targets.")
    for a in alerts:
        with st.container(border=True):
            st.markdown(f"#### {a['source']} | {a['cat']} ({a['priority']})")
            st.info(f"Topic: {a['title']}")
            st.write(f"Date: {a['date']}")
            st.markdown(f"[Go to Source]({a['link']})")
            with st.expander("Gemini AI Analysis"):
                st.write(analyze_with_gemini(a['source'], a['cat'], a['title']))

with tab2:
    st.write("### Government PDF Scanner")
    uploaded_file = st.file_uploader("Upload Government Decision PDF", type=["pdf"])
    if uploaded_file and model:
        with st.spinner("Analyzing..."):
            try:
                res = model.generate_content([{"mime_type": "application/pdf", "data": uploaded_file.read()}, "You are a policy manager at Wolt Israel. Summarize in Hebrew any risks or opportunities in this PDF."])
                st.success(res.text)
            except Exception as e: st.error(f"Error: {e}")

with tab3:
    st.write("### Media Tracking Radar")
    news = fetch_news_data()
    if not news:
        st.info("No current media articles match core keywords.")
    for n in news:
        with st.container(border=True):
            st.markdown(f"#### {n['source']}")
            st.warning(f"Article: {n['title']}")
            st.write(f"Published: {n['date']}")
            st.markdown(f"[Read Article]({n['link']})")
            with st.expander("Gemini AI Spin Analysis"):
                st.write(analyze_with_gemini(n['source'], "Media", n['title']))
