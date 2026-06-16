import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import feedparser

# ==========================================
# 1. אבטחה ומפתחות API (Streamlit Secrets)
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
else:
    st.warning("Warning: Gemini API Key is missing in Secrets.")
    model = None

# ==========================================
# 2. עיצוב ומיתוג סופר-וולטי (Custom CSS)
# ==========================================
st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide", page_icon="🛵")

st.markdown("""
    <style>
    /* עיצוב כללי ויישור לעברית */
    .stApp { direction: rtl; text-align: right; background-color: #ffffff; color: #202125; }
    
    /* כותרות בצבע תכלת וולט רשמי */
    h1, h2, h3 { color: #00c2e8 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800; text-align: right; }
    
    /* עיצוב כרטיסיות המידע של וולט */
    .wolt-card {
        background-color: #f3fafd;
        border-right: 6px solid #00c2e8;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: right;
    }
    .wolt-card h4 { color: #00c2e8 !important; margin-top: 0; font-size: 18px; text-align: right; }
    .wolt-card p { font-size: 15px; color: #202125; line-height: 1.6; text-align: right; }
    
    /* כפתורים ולינקים */
    a { color: #00c2e8 !important; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
    
    /* יישור שדות קלט */
    .stTextInput, .stFileUploader { direction: rtl; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# לוגו Wolt רשמי ושלם - מוטמע ישירות כקוד וקטורי (SVG) פנימי. חסין חסימות אינטרנט לנצח!
wolt_svg_logo = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 115.4 34.2" width="140" style="margin-bottom: 10px; display: block; float: right;">
    <path fill="#00c2e8" d="M14.3 33.6c-3.1 0-5.7-.9-7.7-2.6C4.6 29.3 3.5 26.7 3.5 23V.7h5.7V23c0 2.2.6 3.8 1.7 4.7s2.7 1.4 4.7 1.4c1.9 0 3.4-.5 4.5-1.4s1.7-2.5 1.7-4.7V.7h5.7V23c0 3.7-1.1 6.3-3.2 8-2.1 1.7-4.9 2.6-8 2.6zM46.7 34.2c-4.1 0-7.4-1.3-9.9-3.9-2.5-2.6-3.7-6.2-3.7-10.7s1.2-8.1 3.7-10.7c2.5-2.6 5.8-3.9 9.9-3.9s7.4 1.3 9.9 3.9c2.5 2.6 3.7 6.2 3.7 10.7s-1.2 8.1-3.7 10.7c-2.5 2.6-5.8 3.9-9.9 3.9zm0-5c2.3 0 4.2-.8 5.6-2.5s2.1-4.2 2.1-7.1-.7-5.4-2.1-7.1-3.3-2.5-5.6-2.5-4.2.8-5.6 2.5-2.1 4.2-2.1 7.1.7 5.4 2.1 7.1 3.3 2.5 5.6 2.5zM67.7 33.5V.7h5.7v32.8h-5.7zM86.4 29c1.9 0 3.3-.5 4.3-1.4 1-.9 1.5-2.4 1.5-4.4V10.2h5.7V23c0 3.6-1.1 6.3-3.2 8-2.1 1.7-4.9 2.6-8.3 2.6-3.2 0-5.8-.9-7.8-2.6-2-1.7-3-4.4-3-8V.7h5.7V23c0 2 .5 3.5 1.5 4.4s2.3 1.6 3.6 1.6zm1-23.7V.7h5.7v4.6h-5.7z"/>
</svg>
"""

# הזרקת הלוגו והכותרות המיושרות פיקס לימין
st.markdown(wolt_svg_logo, unsafe_allow_html=True)

st.markdown("""
    <div style="direction: rtl; text-align: right; width: 100%; clear: both; padding-top: 10px;">
        <h1 style="margin: 0; padding: 0; color: #00c2e8; font-size: 42px;">Public Policy Scout</h1>
        <p style="margin: 5px 0 0 0; color: #808080; font-size: 18px; font-weight: 500;">מערכת ארגונית חכמה לניטור סיכונים והזדמנויות רגולטוריות בישראל</p>
    </div>
    <hr style="border: 0; height: 2px; background: #00c2e8; margin-bottom: 30px; margin-top: 20px;">
""", unsafe_allow_html=True)

# ==========================================
# 3. מנגנון בקרת כניסה (הגנת סיסמה)
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.write("### 🔒 כניסה מאובטחת לעובדי וולט")
        password = st.text_input("אנא הכנס סיסמת גישה:", type="password")
        if password == "WoltPolicy2026":
            st.session_state["authenticated"] = True
            st.rerun()
        elif password:
            st.error("⚠️ סיסמה שגויה. הגישה חסומה.")
        return False
    return True

if check_password():

    # ==========================================
    # 4. הגדרות ופילטרים (מילות מפתח)
    # ==========================================
    KEYWORDS = [
        "שליחים", "עצמאיים", "שליחים עצמאיים", "פלטפורמות דיגיטליות", 
        "דו גלגלי", "כלי רכב קלים", "חלטורה", "גיג אקונומי", "מזון", "משלוחים", "פארם", "תרופות"
    ]
    
    KEYWORDS_EN = [
        "couriers", "riders", "delivery", "wolt", "gig economy", 
        "freelancers", "self-employed", "independent contractors", "food delivery", "pharmacy delivery"
    ]
    
    NEGATIVE_KEYWORDS = ["כלבת", "נשכו", "תנים", "כלב", "חתול", "אושפז", "ננשך"]
    
    PRIORITY_COMMITTEES = ["ועדת הכלכלה", "ועדת הכספים", "ועדת העבודה והרווחה"]

    # ==========================================
    # 5. מוח ה-AI (Gemini)
    # ==========================================
    def analyze_with_gemini(source, category, title, text_content=""):
        if not model:
            return "ניתוח ה-AI אינו זמין מכיוון שמפתח ה-API לא הוגדר ב-Secrets."
            
        prompt = f"""
        אתה מנהל מדיניות ציבורית בכיר ויועץ רגולטורי של חברת וולט (Wolt) ישראל.
        להלן פרסום/ידיעה חדשה מהרשת או מהממשלה:
        מקור: {source} ({category})
        כותרת/נושא: {title}
        תוכן נוסף (אם יש): {text_content[:500]}
        
        נתח את הפרסום בקצרצר (עד 3 שורות). קבע האם יש כאן סיכון או הזדמנות למודל של וולט.
        תשובתך חייבת להיות בעברית, מקצועית וממוקדת למנהלים בחברה.
        """
        try:
            response = model.generate_content(prompt)
            return response.text
        except:
            return "לא ניתן לייצר ניתוח AI כרגע."

    # ==========================================
    # 6. צינורות מקורות המידע (Data Pipelines)
    # ==========================================
    
    def fetch_knesset_data():
        url = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Agenda"
        params = {
            '$filter': "StartDate ge datetime'" + datetime.now().strftime('%Y-%m-%dT00:00:00') + "'",
            '$orderby': "StartDate asc",
            '$format': "json"
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                events = []
                for item in response.json().get('value', []):
                    title = item.get('CommitteeSessionName', '') or item.get('Subject', '') or ''
                    committee = item.get('CommitteeName', 'ועדה כללית')
                    
                    if any(word in title for word in KEYWORDS):
                        events.append({
                            "מקור": "🏛️ כנסת ישראל",
                            "קטגוריה": committee,
                            "כותרת": title,
                            "תאריך": datetime.strptime(item['StartDate'], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M'),
                            "עדיפות": "🔥 גבוהה" if committee in PRIORITY_COMMITTEES else "🔵 רגילה",
                            "קישור": "https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgendas.aspx"
                        })
                return events
            return []
        except:
            return []

    def fetch_tazkirim_data():
        resource_id = "9207e37d-b6bd-4df5-91db-fc539dfbbf76"
        url = "https://data.gov.il/api/3/action/datastore_search"
        params = {'resource_id': resource_id, 'limit': 40, 'sort': 'PublishDate desc'}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                records = response.json().get('result', {}).get('records', [])
                tazkirim = []
                for item in records:
                    title = item.get('TazkirName', '') or item.get('Subject', '') or ''
                    ministry = item.get('PublishingMinistry', 'משרד ממשלתי')
                    publish_date = item.get('PublishDate', '')
                    
                    if any(word in title for word in KEYWORDS):
                        tazkirim.append({
                            "מקור": "📜 מאגר החקיקה (תזכירים)",
                            "קטגוריה": ministry,
                            "כותרת": title,
                            "תאריך": publish_date[:10] if publish_date else "לא צוין",
                            "עדיפות": "🔥 גבוהה",
                            "קישור": "https://www.tazkirim.gov.il/"
                        })
                return tazkirim
            return []
        except:
            return []

    def fetch_news_data():
        config_list = [
            ("Davar", "https://www.davar1.co.il/feed/"),
            ("Calcalist", "https://www.calcalist.co.il/GeneralRSS/0,16154,L-8,00.xml"),
            ("Globes", "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederFeed?c=2"),
            ("TheMarker", "https://www.themarker.com/srv/rss/all"),
            ("Ynet", "https://www.ynet.co.il/Integration/StoryRss538.xml"),
            ("Maariv", "https://www.maariv.co.il/Rss/RssFeedsMivzakim"),
            ("Makor Rishon", "https://www.makorrishon.co.il/category/news/feed/"),
            ("Kipa", "https://www.kipa.co.il/rss/news.xml"),
            ("The Times of Israel", "https://www.timesofisrael.com/il/feed/"),
            ("The Jerusalem Post", "https://www.jpost.com/rss/israelnews")
        ]
        
        news_alerts = []
        for name, url in config_list:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or entry.get('description', '') or ''
                    link = entry.get('link', '')
                    pub_date = entry.get('published', '') or entry.get('updated', '') or "---"
                    
                    full_text_lower = f"{title} {summary}".lower()
                    match_he = any(word in full_text_lower for word in KEYWORDS)
                    match_en = any(word in full_text_lower for word in KEYWORDS_EN)
                    has_negative = any(neg_word in full_text_lower for neg_word in NEGATIVE_KEYWORDS)
                    
                    if (match_he or match_en) and not has_negative:
                        if not any(alert['קישור'] == link for alert in news_alerts):
                            news_alerts.append({
                                "מקור": f"{name}",
                                "קטגוריה": "מדיה ואקטואליה",
                                "כותרת": title,
                                "תאריך": pub_date[:16] if len(pub_date) > 16 else pub_date,
                                "עדיפות": "🔵 מעקב מדיה",
                                "קישור": link
                            })
            except:
                continue
        return news_alerts

    # ==========================================
    # 7. בניית ממשק המשתמש (Tabs Layout)
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["🏛️ חקיקה וּועדות (אוטומטי)", "📂 סורק מסמכי ממשלה (PDF)", "📰 רדאר חדשות חי"])

    # טאב 1: כנסת וחקיקה
    with tab1:
        st.write("### 🏛️ עדכוני כנסת ישראל ומאגר החקיקה הלאומי")
        with st.spinner("סורק מאגרים ממשלתיים..."):
            gov_alerts = []
            gov_alerts.extend(fetch_knesset_data())
            gov_alerts.extend(fetch_tazkirim_data())
            
        if not gov_alerts:
            st.info("לא נמצאו דיונים או תזכירי חוק קרובים התואמים את מילות המפתח של וולט.")
        else:
            for alert in gov_alerts:
                st.markdown(f"""
                    <div class="wolt-card">
                        <h4>{alert['מקור']} | {alert['קטגוריה']}</h4>
                        <p><b>נושא הדיון:</b> {alert['כותרת']}</p>
                        <p style="font-size: 13px; color: #606060; margin-bottom: 10px;">📅 תאריך: {alert['תאריך']} | 📊 עדיפות: {alert['עדיפות']}</p>
                        <a href="{alert['קישור']}" target="_blank">🔗 למעבר למקור הדיון לחץ כאן</a>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("🔍 ניתוח מדיניות והמלצות - Gemini AI"):
                    analysis = analyze_with_gemini(alert['מקור'], alert['קטגוריה'], alert['כותרת'])
                    st.write(analysis)
                st.markdown("<br>", unsafe_allow_html=True)

    # טאב 2: סורק PDF
    with tab2:
        st.write("### 📂 סורק החלטות ממשלה וועדות שרים (PDF)")
        st.write("מזכירות הממשלה מפרסמת קובצי PDF. העלה אותם כאן לסריקה וניתוח מיידי:")
        uploaded_file = st.file_uploader("גרור או בחר קובץ PDF של הממשלה", type=["pdf"])
        
        if uploaded_file is not None:
            with st.spinner("ה-AI קורא ומנתח את המסמך..."):
                file_bytes = uploaded_file.read()
                prompt = "אתה מנהל מדיניות ציבורית בוולט ישראל. סרוק את ה-PDF המצורף וחפש סעיפים שקשורים למילות המפתח של החברה. תן תקציר בעברית של סיכונים או הזדמנויות לוולט."
                try:
                    response = model.generate_content([{"mime_type": "application/pdf", "data": file_bytes}, prompt])
                    st.success(response.text)
                except Exception as e:
                    st.error(f"שגיאה בניתוח: {e}")

    # טאב 3: רדאר חדשות
    with tab3:
        st.write("### 📰 רדאר מדיניות בתקשורת הישראלית")
        with st.spinner("סורק את אתרי החדשות..."):
            news_alerts = fetch_news_data()
            
        if not news_alerts:
            st.info("אין כתבות אקטואליות חדשות בנושאי הליבה של וולט בשעות האחרונות.")
        else:
            for alert in news_alerts:
                st.markdown(f"""
                    <div class="wolt-card">
                        <h4>📰 {alert['מקור']}</h4>
                        <p><b>כותרת הכתבה:</b> {alert['כותרת']}</p>
                        <p style="font-size: 13px; color: #606060; margin-bottom: 10px;">📅 פורסם בתאריך: {alert['תאריך']}</p>
                        <a href="{alert['קישור']}" target="_blank">🔗 לקריאת הכתבה המלאה לחץ כאן</a>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("🔍 ניתוח ספין והשפעה תקשורתית - Gemini AI"):
                    analysis = analyze_with_gemini(alert['מקור'], "חדשות ומדיה", alert['כותרת'])
                    st.write(analysis)
                st.markdown("<br>", unsafe_allow_html=True)
