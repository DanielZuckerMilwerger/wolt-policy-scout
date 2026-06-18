def fetch_knesset_data():
    events = []
    try:
        # שינוי הטווח: סריקה החל מ-3 ימים אחורה כדי לתפוס גם דיונים עתידיים בשבוע הקרוב
        start_dt = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')
        url = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Agenda"
        
        params = {
            '$filter': f"StartDate ge datetime'{start_dt}'",
            '$orderby': "StartDate asc", # מסדר מהקרוב לרחוק
            '$top': '800', # הגדלנו ל-800 כדי לא לפספס אף דיון עתידי
            '$format': "json"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            for item in response.json().get('value', []):
                session_name = item.get('CommitteeSessionName', '') or ''
                subject = item.get('Subject', '') or ''
                committee = item.get('CommitteeName', '') or 'ועדה כללית'
                
                txt = f"{session_name} {subject} {committee}"
                match_kw = any(w in txt for w in KEYWORDS)
                match_comm = any(c in committee for c in PRIORITY_COMMITTEES)
                
                if match_kw or match_comm:
                    title_to_show = session_name if session_name else subject
                    if not title_to_show:
                        title_to_show = f"ישיבה של {committee}"
                    
                    date_parsed = datetime.strptime(item['StartDate'], '%Y-%m-%dT%H:%M:%S')
                    date_str = date_parsed.strftime('%d/%m/%Y %H:%M')
                    link_kn = "https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgendas.aspx"
                    
                    events.append({
                        "מקור": "🏛️ כנסת ישראל",
                        "קטגוריה": committee,
                        "כותרת": title_to_show,
                        "תאריך": date_str,
                        "עדיפות": "🔥 גבוהה" if match_comm else "🔵 רגילה",
                        "קישור": link_kn
                    })
    except:
        pass
    return events
