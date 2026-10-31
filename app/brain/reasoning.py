"""PrahaarShield Brain v3: reasoning from the actual chat (all local, no cloud).

1. TACTICS  - manipulation tactics found in a message (persuasion research, adapted to Indian financial scams):
              authority, urgency, threat, secrecy, familiarity, reward, verify_block, channel, new_number, pay_ask.
2. FACTS    - what happened in THIS chat: money requests and amounts (escalation), verification blocking
              (only when repeated or joined with payment pressure - one "I'm busy, call later" is normal),
              the user's own call attempts, kind of OTP asked (bank / WhatsApp / delivery), threats, secrecy, links.
3. FACT LIBRARY - checked facts about how Indian institutions really work; a claim in the chat is matched to the fact.
4. COMPOSER - chat-specific sentences in English / Hindi / Marathi built from those facts.
Context signals (contact status, account tags) only adjust levels in the Brain; they never enter the model.
"""
from __future__ import annotations

import re

R = lambda p: re.compile(p, re.I)
DEV = r"(?![\u0900-\u097F])"            # end of a Devanagari word (\b is unreliable with vowel signs)

TACTIC_RX = {
    "authority": R(r"\b(police|cbi|enforcement directorate|rbi|sebi|trai|customs|cyber ?(cell|crime)|inspector|officer|court|judge|"
                   r"customer care|bank (manager|officer|se|from)|hr (team|department)|ceo|managing director|\bmd\b|director|boss)\b|"
                   r"पुलिस|पोलीस|पोलिस|सीबीआई|अधिकारी|सायबर|कोर्ट|न्यायालय|कस्टम|बँकेतून|बैंक से"),
    "urgency": R(r"\b(urgent|urgently|immediately|right now|asap|jaldi|turant|fast|quick(ly)?|hurry|today only|aaj hi|ajach|lagech|patkan|"
                 r"within \d+ ?(min|minutes|hours?|hrs?)|\d+ ?(min|minute|minutes|ghante|ghanton|tasat|minitat))\b|"
                 r"तुरंत|जल्दी|पटकन|लगेच|आजच|आज ही|\d+ ?(मिनिटांत|मिनिटात|मिनट|घंटे|तासांत)"),
    "threat": R(r"\b(arrest|warrant|jail|fir|freeze|frozen|suspend(ed)?|seiz\w*|confiscat\w*|zabt|jappt|blacklist\w*|cibil|defaulter|morph\w*|"
                r"legal (action|notice|case)|case (darj|file|filed|registered)|consequences?|parinam|warna|nahi ?to|nahitar|or else|otherwise|"
                r"will be blocked|block (ho|kar|karu|karun))\b|"
                r"गिरफ्तार|अटक|जेल|तुरुंग|फ्रीज़|फ्रीज|गोठव|ज़ब्त|जप्त|परिणाम|वरना|नाहीतर|नहीं तो|ब्लॉक कर|बंद होईल|बंद हो जाएगा"),
    "secrecy": R(r"\b(don'?t tell|do not (tell|inform)|keep (it|this) (secret|confidential)|confidential|nda|between us|chupchaap|gupchup|"
                 r"kisi ko (mat|na) bata\w*|sangu nak\w*|don'?t loop in)\b|मत बताना|किसी को मत|सांगू नका|सांगू नकोस|गोपनीय"),
    "familiarity": R(r"\b(remember me|yaad hai|pehchana|olakhla|we met|mile the|bhetlo|long time|kitne din baad|old friend|purana dost)\b|"
                     r"ओळखलं|पहचाना|याद है|भेटलो|आठवतं"),
    "reward": R(r"\b(guaranteed?|assured|sure ?shot|risk[- ]?free|no loss|zero loss|double (your|money)|\d+ ?% ?(daily|weekly|monthly|profit|return)|"
                r"daily profit|earn ₹?\s?\d|lottery|prize|jackpot)\b|पक्का मुनाफ़ा|गारंटी|खात्रीशीर|रोज़ ₹"),
    "verify_block": R(r"\b((don'?t|do not|mat|nako|naka|nahi|na) (call|phone|video ?call)|call (mat|nako|naka|nahi|later|baad me)|"
                      r"can'?t (talk|call|take calls?)|no calls?|call (cut|kat)|call karu nak\w*|phone mat kar\w*)\b|"
                      r"कॉल (नको|मत|नाही)|फोन (नको|मत|करू नको)|call नको"),
    "channel": R(r"\b(telegram|join (our|the|this) (group|channel)|download|install|apk|anydesk|teamviewer|quick ?support|screen ?share|"
                 r"click (here|the link|this link))\b|https?://|\b[\w-]+\.(in|com|net|org|co|top|xyz|info|site|online|app)\b|डाउनलोड|इंस्टॉल"),
    "new_number": R(r"\b(new number|naya number|navin number|number (change|badal)\w*|my personal number|this is my new)\b|नवीन नंबर|नया नंबर"),
}
PAY_IMPERATIVE = R(r"\b(pay|send|transfer|deposit|bhej|bhejo|bhej do|bhejna|bhejiye|bharo|bhar do|bhar dena|bhariye|transfer karo|"
                   r"transfer kar do|jama karo|pay karo|pay kar do|pathav|pathva|bhara)\b|"
                   r"पाठव(?!ले|ल|त|ण)|पाठवा|भेजो|भेज दो|भेजिए|भरो|भर दो|भरा" + DEV + r"|जमा करो|जमा करें|ट्रान्सफर कर|ट्रांसफर करो")
MONEY_CTX = R(r"₹|\brs\.?\s?\d|\b\d{3,}\b|\b\d+\s?(k|lakh|lac)\b|paise|paisa|money|payment|amount|fee|fees|charges?|पैसे|पैसा|रक्कम|रकम|शुल्क|फी")
SEND_NOW = R(r"\b(send|bhej|pathav)\w*\s+(it\s+)?(fast|now|quick|jaldi|lagech|patkan)\b|\b(jaldi|patkan|lagech)\s+(bhej|pathav)\w*|पटकन पाठव|लगेच पाठव|जल्दी भेज")
CALL_TRY = R(r"\b(call (karte|karti|karto|karu|kar raha|kar rahi|karungi|karunga|me|you|kar)|let me call|i'?ll call|calling you|pick up|phone (uchal|utha|kar))\b|"
             r"कॉल करते|कॉल करतो|कॉल करू|फोन कर|फोन उचल|call कट")
OTP_KIND = [("whatsapp", R(r"whatsapp|verification code|6.?digit code|(sent|bheja|aaya)\w* (by )?(mistake|galti)|चुकून|गलती से")),
            ("bank", R(r"\b(bank|upi|net ?banking|card|cvv|account|a/c|khata|paytm|phonepe|gpay|wallet|kyc|loan)\b|बँक|बैंक|खाते|खाता")),
            ("delivery", R(r"\b(delivery|order|parcel|swiggy|zomato|amazon|flipkart|meesho|blinkit|zepto|gas|cylinder|courier)\b|डिलिव्हरी|डिलीवरी|ऑर्डर"))]
AMOUNT = R(r"(?:₹|rs\.?|inr)\s?([\d,]+)|\b([\d,]{4,})\b|\b(\d+(?:\.\d+)?)\s?(k|lakh|lac)\b")
PRESSURE = {"urgency", "threat", "secrecy", "verify_block"}


def tactics(text: str) -> set[str]:
    t = text or ""
    out = {k for k, rx in TACTIC_RX.items() if rx.search(t)}
    if (PAY_IMPERATIVE.search(t) and MONEY_CTX.search(t)) or SEND_NOW.search(t):
        out.add("pay_ask")
    return out


def otp_kind(text: str) -> str:
    for kind, rx in OTP_KIND:
        if rx.search(text or ""):
            return kind
    return "unknown"


def amounts(text: str) -> list[int]:
    out = []
    for a, b, c, unit in AMOUNT.findall(text or ""):
        try:
            if a or b:
                v = int((a or b).replace(",", ""))
            else:
                v = int(float(c) * (1000 if unit.lower() == "k" else 100000))
        except ValueError:
            continue
        if 100 <= v <= 50_00_00_000 and not (1900 <= v <= 2100 and not a):   # skip years written without ₹
            out.append(v)
    return out


def trusted(ctx: dict | None) -> bool:
    return bool(ctx and ctx.get("contacts_permission") and ctx.get("contact_status") == "safe")


# ------------------------------------------------------------------ fact library (local, checked; source in brackets)
FACTS = [
    ("bank_otp", R(r"(bank|customer care|kyc|account|khata|बँक|बैंक).{0,60}\b(otp|pin|cvv)\b|\b(otp|pin|cvv)\b.{0,60}(bank|kyc|account|verif)"),
     {"en": "Banks never ask for your OTP, PIN or CVV on a call or chat.",
      "hi": "बैंक कभी कॉल या चैट पर आपका OTP, PIN या CVV नहीं माँगते।",
      "mr": "बँका कधीही कॉल किंवा चॅटवर तुमचा OTP, PIN किंवा CVV मागत नाहीत."}, "RBI / bank advisories"),
    ("kyc_link", R(r"kyc.{0,80}(link|http|\.in\b|\.com\b|\.net\b|click|update now|लिंक)"),
     {"en": "KYC is updated only in your bank branch or the bank's official app, never through a link from an unknown number.",
      "hi": "केवाईसी सिर्फ़ बैंक शाखा या बैंक के आधिकारिक ऐप से होती है, किसी अनजान नंबर के लिंक से नहीं।",
      "mr": "KYC फक्त बँकेच्या शाखेत किंवा अधिकृत ॲपमध्ये होते, अनोळखी नंबरवरच्या लिंकवरून नाही."}, "RBI / bank advisories"),
    ("safe_account", R(r"(safe|secure|verification|escrow|audit|security|जाँच|तपासणी|सेफ)\s?(account|khata|खाते|खाता)"),
     {"en": "RBI does not keep any 'safe', 'verification' or 'escrow' account for citizens' money.",
      "hi": "आरबीआई नागरिकों के पैसे के लिए कोई 'सेफ', 'जाँच' या 'एस्क्रो' खाता नहीं रखता।",
      "mr": "RBI नागरिकांच्या पैशांसाठी कोणतेही 'सेफ', 'तपासणी' किंवा 'एस्क्रो' खाते ठेवत नाही."}, "RBI / I4C advisories"),
    ("digital_arrest", R(r"digital arrest|video call.{0,50}(arrest|case|police|investigation|camera)|(arrest|warrant).{0,50}(video call|whatsapp)|"
                         r"stay on (the )?video|डिजिटल अरेस्ट|video call pe raho|camera on"),
     {"en": "There is no 'digital arrest' in Indian law. Police never question or arrest anyone on a video call, and never share warrants or FIRs on WhatsApp.",
      "hi": "भारतीय कानून में 'डिजिटल अरेस्ट' नाम की कोई चीज़ नहीं है। पुलिस वीडियो कॉल पर पूछताछ या गिरफ्तारी नहीं करती और वारंट/एफआईआर व्हाट्सऐप पर नहीं भेजती।",
      "mr": "भारतीय कायद्यात 'डिजिटल अरेस्ट' असे काहीही नाही. पोलीस व्हिडिओ कॉलवर चौकशी किंवा अटक करत नाहीत आणि वॉरंट/FIR व्हॉट्सॲपवर पाठवत नाहीत."}, "Mumbai Police / MHA"),
    ("official_money", R(r"(police|cbi|\bed\b|court|customs|officer|inspector|पुलिस|पोलीस|अधिकारी).{0,90}(pay|transfer|deposit|bail|fine|security|fee|₹|rs\b|bhej|bhar|पाठव|भर|जमा)"),
     {"en": "Police, courts and customs never ask you to pay money on a call or chat to close a case.",
      "hi": "पुलिस, अदालत या कस्टम कभी केस बंद करने के लिए कॉल या चैट पर पैसे नहीं माँगते।",
      "mr": "पोलीस, न्यायालय किंवा कस्टम केस बंद करण्यासाठी कधीही कॉल किंवा चॅटवर पैसे मागत नाहीत."}, "I4C / MHA advisories"),
    ("loan_charges_personal", R(r"(emi|loan|installment|instalment|hapta|हप्ता|किस्त|लोन|कर्ज).{0,90}(charges?|processing|clearance|penalty|fee|extra|hold|शुल्क|चार्ज)"),
     {"en": "Banks add late fees and charges to your own loan account. They never ask you, or a relative, to send money personally to 'clear' an EMI.",
      "hi": "बैंक लेट फीस और चार्ज आपके अपने लोन खाते में जोड़ते हैं। ईएमआई 'क्लियर' करने के लिए वे कभी आपसे या रिश्तेदार से निजी तौर पर पैसे भेजने को नहीं कहते।",
      "mr": "बँका उशिराचे शुल्क तुमच्याच कर्ज खात्यात जोडतात. EMI 'क्लिअर' करण्यासाठी त्या कधीही तुम्हाला किंवा नातेवाइकाला वैयक्तिकरित्या पैसे पाठवायला सांगत नाहीत."}, "RBI / bank practice"),
    ("loan_advance_fee", R(r"(loan|disburs\w*|approved|sanction\w*|लोन|कर्ज).{0,90}(processing fee|gst|insurance|charges?|deposit|fee).{0,60}(pay|first|before|pehle|adhi|आधी|पहले|bhar|भर)"),
     {"en": "Regulated lenders list every fee in the loan's Key Fact Statement and usually deduct it from the loan amount. A demand to pay first through UPI is a common scam.",
      "hi": "नियमित ऋणदाता हर फीस लोन के 'की फैक्ट स्टेटमेंट' में बताते हैं और आमतौर पर लोन की रकम से ही काटते हैं। पहले यूपीआई से फीस माँगना आम स्कैम है।",
      "mr": "नियमित कर्जदाते प्रत्येक शुल्क कर्जाच्या 'की फॅक्ट स्टेटमेंट'मध्ये दाखवतात आणि सहसा कर्जाच्या रकमेतूनच कापतात. आधी UPI ने फी मागणे हा सामान्य स्कॅम आहे."}, "RBI digital lending rules"),
    ("recovery_harassment", R(r"(contacts?|relatives|family|office|groups?|कॉन्टॅक्ट|कॉन्टैक्ट).{0,70}(send|message|bhej|tell|bata|post|daal|पाठव|भेज|मेसेज).{0,50}(photo|fraud|defaulter|chor|चोर|फ्रॉड|फसवे)|morph"),
     {"en": "Lenders and recovery agents are not allowed to shame or threaten you through your contacts. Keep the messages and report on 1930 or cybercrime.gov.in.",
      "hi": "लोन देने वाले या रिकवरी एजेंट आपके कॉन्टैक्ट्स के ज़रिए आपको बदनाम या धमका नहीं सकते। मैसेज सँभाल कर रखें और 1930 या cybercrime.gov.in पर शिकायत करें।",
      "mr": "कर्जदाते किंवा वसुली एजंट तुमच्या कॉन्टॅक्ट्समार्फत तुमची बदनामी किंवा धमकी देऊ शकत नाहीत. मेसेज जपून ठेवा आणि 1930 किंवा cybercrime.gov.in वर तक्रार करा."}, "RBI fair-practice rules"),
    ("invest_guarantee", R(r"(guarantee\w*|assured|sure ?shot|risk[- ]?free|no loss|zero loss|गारंटी|खात्रीशीर|पक्का).{0,60}(profit|return|%|kamai|नफा|मुनाफ़ा|कमाई)|\d+ ?% ?(daily|weekly|per day|roz)"),
     {"en": "No genuine investment can guarantee fixed daily or weekly profits; SEBI-registered advisers are not allowed to promise assured returns.",
      "hi": "कोई असली निवेश रोज़ या हर हफ़्ते पक्के मुनाफ़े की गारंटी नहीं दे सकता; सेबी-पंजीकृत सलाहकार पक्के रिटर्न का वादा नहीं कर सकते।",
      "mr": "कोणतीही खरी गुंतवणूक रोज किंवा दर आठवड्याला खात्रीशीर नफ्याची हमी देऊ शकत नाही; SEBI-नोंदणीकृत सल्लागार खात्रीशीर परताव्याचे आश्वासन देऊ शकत नाहीत."}, "SEBI"),
    ("withdraw_tax", R(r"(withdraw\w*|nikal\w*|निकाल|काढ).{0,90}(tax|fee|charge|margin|deposit|शुल्क|कर" + DEV + r"|टॅक्स|टैक्स|bhar|pay|भर)"),
     {"en": "A real platform deducts tax from your earnings. You never pay a 'tax' or 'fee' first to withdraw your own money.",
      "hi": "असली प्लेटफ़ॉर्म टैक्स आपकी कमाई से ही काटता है। अपना पैसा निकालने के लिए पहले 'टैक्स' या 'फीस' कभी नहीं भरनी होती।",
      "mr": "खरा प्लॅटफॉर्म कर तुमच्या कमाईतूनच कापतो. स्वतःचे पैसे काढण्यासाठी आधी 'कर' किंवा 'फी' कधीच भरावी लागत नाही."}, "Income-tax practice"),
    ("job_fee", R(r"(job|task|offer|joining|registration|naukri|नोकरी|नौकरी|टास्क|जॉब|जॉइनिंग).{0,90}(fee|deposit|pay|charge|शुल्क|फी|फीस|bhar|jama|जमा|भर)|prepaid (task|round)|combination task|प्रीपेड"),
     {"en": "Genuine employers never charge a joining, registration or task fee, and never ask you to deposit money to earn.",
      "hi": "असली कंपनियाँ कभी जॉइनिंग, रजिस्ट्रेशन या टास्क फीस नहीं लेतीं, और कमाने के लिए पैसे जमा करने को नहीं कहतीं।",
      "mr": "खऱ्या कंपन्या कधीही जॉइनिंग, नोंदणी किंवा टास्क फी घेत नाहीत आणि कमाईसाठी पैसे भरायला सांगत नाहीत."}, "I4C advisories"),
    ("electricity", R(r"(electricity|bijli|light bill|वीज|बिजली|meter|mseb|msedcl|mahavitaran|महावितरण).{0,90}(cut|disconnect|kaat|kapl|कापली|काट|tonight|aaj raat|आज रात|officer|call|link|apk|download)"),
     {"en": "MSEDCL bills are paid only on the official app, website or office. Officials don't ask you to pay through a personal number, link or APK.",
      "hi": "बिजली बिल सिर्फ़ आधिकारिक ऐप, वेबसाइट या दफ़्तर में भरा जाता है। अधिकारी निजी नंबर, लिंक या APK से भुगतान नहीं माँगते।",
      "mr": "महावितरणचे बिल फक्त अधिकृत ॲप, वेबसाइट किंवा कार्यालयात भरले जाते. अधिकारी वैयक्तिक नंबर, लिंक किंवा APK ने पैसे मागत नाहीत."}, "MSEDCL"),
    ("gift_cards", R(r"gift ?cards?|vouchers?.{0,40}codes?|scratch codes?|गिफ्ट कार्ड"),
     {"en": "No company pays clients or vendors with gift-card codes requested on WhatsApp.",
      "hi": "कोई कंपनी व्हाट्सऐप पर माँगे गए गिफ्ट-कार्ड कोड से क्लाइंट या वेंडर को भुगतान नहीं करती।",
      "mr": "कोणतीही कंपनी व्हॉट्सॲपवर मागितलेल्या गिफ्ट-कार्ड कोडने क्लायंट किंवा वेंडरला पैसे देत नाही."}, "I4C advisories"),
    ("boss_process", R(r"(don'?t (tell|inform|loop in)|keep it confidential|\bnda\b|finance ko mat|फायनान्सला सांगू|फाइनेंस को मत).{0,90}|new (account|bank) details|naye account|नए खाते|नवीन खात"),
     {"en": "Company payments go through an approval process. Verify any urgent payment request on the person's old number or in person.",
      "hi": "कंपनी के भुगतान अनुमोदन प्रक्रिया से होते हैं। किसी भी जल्दी वाले भुगतान को उस व्यक्ति के पुराने नंबर पर या आमने-सामने पक्का करें।",
      "mr": "कंपनीची पेमेंट्स मंजुरी प्रक्रियेतून होतात. कोणतीही तातडीची पेमेंट मागणी त्या व्यक्तीच्या जुन्या नंबरवर किंवा प्रत्यक्ष खात्री करा."}, "Company finance practice"),
    ("whatsapp_code", R(r"(code|otp).{0,40}(sent|bheja|aaya).{0,25}(mistake|galti|चुकून|गलती)|(forward|share|send|bhej).{0,30}(6.?digit|verification) code"),
     {"en": "A WhatsApp code 'sent by mistake' is used to take over your WhatsApp account. Never forward it, even to a friend.",
      "hi": "'गलती से भेजा गया' व्हाट्सऐप कोड आपका व्हाट्सऐप अकाउंट हथियाने के लिए माँगा जाता है। इसे किसी दोस्त को भी न भेजें।",
      "mr": "'चुकून पाठवलेला' व्हॉट्सॲप कोड तुमचे व्हॉट्सॲप अकाउंट ताब्यात घेण्यासाठी मागितला जातो. तो मित्रालाही पाठवू नका."}, "WhatsApp / I4C"),
    ("upi_receive", R(r"(receive|get|milenge|credit|refund).{0,60}(upi pin|\bpin\b)|(upi pin|\bpin\b).{0,60}(receive|refund|credit|milenge)"),
     {"en": "You never enter your UPI PIN to receive money; a PIN is only needed to send money.",
      "hi": "पैसे पाने के लिए कभी यूपीआई पिन नहीं डालना पड़ता; पिन सिर्फ़ पैसे भेजने के लिए होता है।",
      "mr": "पैसे मिळवण्यासाठी कधीही UPI PIN टाकावा लागत नाही; PIN फक्त पैसे पाठवण्यासाठी असतो."}, "NPCI"),
    ("reply_no", R(r"reply\s+no\b|\bNO\b\s*(likh|लिख|पाठव|type)|'no' (likh|reply)"),
     {"en": "Banks don't ask you to reply 'NO' and share an OTP to stop a debit. Call the number printed on your card.",
      "hi": "बैंक कभी डेबिट रोकने के लिए 'NO' लिखकर ओटीपी बताने को नहीं कहते। अपने कार्ड पर छपे नंबर पर कॉल करें।",
      "mr": "डेबिट थांबवण्यासाठी बँका 'NO' लिहून OTP सांगायला कधीच सांगत नाहीत. तुमच्या कार्डवर छापलेल्या नंबरवर कॉल करा."}, "RBI / bank advisories"),
    ("remote_app", R(r"anydesk|teamviewer|quick ?support|screen ?share|rustdesk"),
     {"en": "Banks and support teams never ask you to install screen-sharing apps like AnyDesk.",
      "hi": "बैंक या सपोर्ट टीम कभी AnyDesk जैसे स्क्रीन-शेयरिंग ऐप डालने को नहीं कहते।",
      "mr": "बँका किंवा सपोर्ट टीम कधीही AnyDesk सारखे स्क्रीन-शेअरिंग ॲप टाकायला सांगत नाहीत."}, "RBI / bank advisories"),
    ("customs", R(r"(customs|parcel|courier|fedex|dhl|पार्सल|कस्टम).{0,90}(duty|fine|penalty|clearance|drugs|passport|ड्रग्स)"),
     {"en": "Customs duty is paid on official portals with a receipt, never to a person on a call or chat.",
      "hi": "कस्टम ड्यूटी आधिकारिक पोर्टल पर रसीद के साथ भरी जाती है, कॉल या चैट पर किसी व्यक्ति को नहीं।",
      "mr": "कस्टम ड्युटी अधिकृत पोर्टलवर पावतीसह भरली जाते, कॉल किंवा चॅटवर कोणत्या व्यक्तीला नाही."}, "CBIC"),
]


def fact_checks(text: str, lang: str) -> list[str]:
    out = []
    for fid, rx, txt, src in FACTS:
        if rx.search(text or ""):
            out.append(f"{S['fact'][lang]}{txt.get(lang, txt['en'])} ({src})")
    return out


# ------------------------------------------------------------------ chat facts
def chat_facts(messages: list[dict], ctx: dict | None, levels: dict | None = None) -> dict:
    """messages: [{id, direction, text, analysis}] oldest -> newest."""
    F = {"money_requests": 0, "amounts": [], "escalation": False, "verify_blocks": 0, "blocking": False, "user_calls": 0,
         "otp": [], "threat_quote": None, "authority_quote": None, "secrecy": False, "reward": False, "familiarity": False,
         "channel": False, "new_number": False, "urgency": False, "threats": 0, "victim_action": False, "fact_ids": [], "money_mentions": []}
    known = trusted(ctx)
    seq = []                                                     # (direction, text, tactics, rules)
    for m in messages:
        a = m.get("analysis") or {}
        text = a.get("clean_text") or m.get("text") or ""
        seq.append((m.get("direction"), text, tactics(text) if m.get("direction") == "in" else set(), set(a.get("rules", []))))
    threats = []
    for i, (d, text, tac, rules) in enumerate(seq):
        if d == "out":
            if CALL_TRY.search(text):
                F["user_calls"] += 1
            continue
        amts = amounts(text)
        F["money_mentions"] += amts
        # a money request = "send/pay" command, or money + pressure ("35000 ... if not sent in 5 minutes, account freeze")
        if "pay_ask" in tac or (MONEY_CTX.search(text) and tac & {"threat", "urgency"} and amts):
            F["money_requests"] += 1
            F["amounts"] += amts
        if "verify_block" in tac:
            F["verify_blocks"] += 1
            window = [seq[j] for j in range(max(0, i - 3), min(len(seq), i + 4)) if j != i]
            money_push = "pay_ask" in tac or any(w[0] == "in" and "pay_ask" in w[2] for w in window) or F["money_requests"] > 0
            pressure = bool(tac & {"threat", "urgency"}) or any(w[0] == "in" and w[2] & {"threat", "urgency"} for w in window)
            tried = any(w[0] == "out" and CALL_TRY.search(w[1]) for w in window)
            if money_push and (tried or pressure):
                F["blocking"] = True     # refuses checks while pushing for money AND (you tried to call, or there is pressure); one "busy, call later" is normal
        if "threat" in tac:
            F["threats"] += 1
            threats.append(text)
        if "authority" in tac and not known and not F["authority_quote"]:
            F["authority_quote"] = text[:100]                    # only for unknown senders: a saved contact's identity is known
        for k in ("secrecy", "reward", "familiarity", "channel", "new_number", "urgency"):
            F[k] = F[k] or (k in tac)
        if "cred_ask" in rules:
            F["otp"].append(otp_kind(text))
        for fid, rx, txt, src in FACTS:
            if rx.search(text) and fid not in F["fact_ids"]:
                F["fact_ids"].append(fid)
    if threats:
        q = min(threats, key=len)                                # the clearest (shortest) threat
        F["threat_quote"] = q if len(q) <= 110 else q[:107].rsplit(" ", 1)[0] + "…"
    if F["verify_blocks"] >= 2 and F["money_requests"]:
        F["blocking"] = True
    a = F["amounts"]
    F["escalation"] = len(a) >= 2 and max(a) > a[0] * 1.3
    F["pressure"] = sum(bool(x) for x in (F["urgency"], F["threats"], F["blocking"], F["secrecy"], F["escalation"]))
    return F


# ------------------------------------------------------------------ text (EN / HI / MR)
S = {
    "fact": {"en": "Fact check: ", "hi": "तथ्य जाँच: ", "mr": "तथ्य तपासणी: "},
    "money": {"en": "Asked you for money {n} time(s){amts}.", "hi": "{n} बार पैसे माँगे{amts}।", "mr": "{n} वेळा पैसे मागितले{amts}."},
    "escalation": {"en": "The amount kept growing: ₹{first} → ₹{last}.", "hi": "रकम बढ़ती गई: ₹{first} → ₹{last}।", "mr": "रक्कम वाढत गेली: ₹{first} → ₹{last}."},
    "blocking": {"en": "Stopped you from calling to check{k} while pushing for payment.", "hi": "पैसों के लिए दबाव डालते हुए आपको कॉल करके पुष्टि करने से रोका{k}।",
                 "mr": "पैशांसाठी दबाव टाकत तुम्हाला कॉल करून खात्री करू दिली नाही{k}."},
    "user_call": {"en": "You tried to call and verify. That was the right move.", "hi": "आपने कॉल करके पुष्टि करने की कोशिश की, यह बिल्कुल सही था।",
                  "mr": "तुम्ही कॉल करून खात्री करायचा प्रयत्न केला, ते अगदी बरोबर होतं."},
    "otp_bank": {"en": "Asked for a bank / UPI code. Nobody genuine ever needs it.", "hi": "बैंक / यूपीआई का कोड माँगा। किसी असली व्यक्ति को इसकी ज़रूरत नहीं होती।",
                 "mr": "बँक / UPI चा कोड मागितला. कोणत्याही खऱ्या व्यक्तीला त्याची गरज नसते."},
    "otp_whatsapp": {"en": "Asked you to forward a WhatsApp verification code, which hands over your WhatsApp account.",
                     "hi": "व्हाट्सऐप वेरिफ़िकेशन कोड आगे भेजने को कहा, इससे आपका व्हाट्सऐप अकाउंट उनके हाथ चला जाता है।",
                     "mr": "व्हॉट्सॲप व्हेरिफिकेशन कोड पुढे पाठवायला सांगितला, त्यामुळे तुमचे व्हॉट्सॲप अकाउंट त्यांच्या हातात जाते."},
    "otp_delivery": {"en": "Asked for a delivery OTP. That is normal at home, but never share bank or WhatsApp codes.",
                     "hi": "डिलीवरी का ओटीपी माँगा। घर में यह सामान्य है, पर बैंक या व्हाट्सऐप के कोड कभी न बताएँ।",
                     "mr": "डिलिव्हरीचा OTP मागितला. घरात हे सामान्य आहे, पण बँक किंवा व्हॉट्सॲपचे कोड कधीच सांगू नका."},
    "otp_unknown": {"en": "Asked for an OTP without saying what it is for.", "hi": "बिना बताए कि किसलिए, ओटीपी माँगा।", "mr": "कशासाठी ते न सांगता OTP मागितला."},
    "threat": {"en": "Threatened you: “{q}”", "hi": "धमकी दी: “{q}”", "mr": "धमकी दिली: “{q}”"},
    "authority": {"en": "Claimed to be an official: “{q}”", "hi": "अधिकारी होने का दावा किया: “{q}”", "mr": "अधिकारी असल्याचा दावा केला: “{q}”"},
    "secrecy": {"en": "Told you to keep it secret from others.", "hi": "दूसरों से बात छुपाने को कहा।", "mr": "इतरांपासून गोष्ट लपवायला सांगितलं."},
    "reward": {"en": "Promised unusually high or guaranteed returns.", "hi": "बहुत ज़्यादा या पक्के मुनाफ़े का वादा किया।", "mr": "जास्त किंवा खात्रीशीर नफ्याचे आमिष दाखवले."},
    "familiarity": {"en": "Built familiarity first (“remember me?”) before money came up.", "hi": "पहले जान-पहचान जताई (“याद है?”), फिर पैसों की बात आई।",
                    "mr": "आधी ओळख दाखवली (“आठवतं का?”), मग पैशांचा विषय आला."},
    "channel": {"en": "Pushed you to a link, app or another platform.", "hi": "लिंक, ऐप या दूसरे प्लेटफ़ॉर्म पर ले जाने की कोशिश की।",
                "mr": "लिंक, ॲप किंवा दुसऱ्या प्लॅटफॉर्मवर नेण्याचा प्रयत्न केला."},
    "new_number": {"en": "Said they are messaging from a new number.", "hi": "नए नंबर से मैसेज करने की बात कही।", "mr": "नवीन नंबरवरून मेसेज करत असल्याचं सांगितलं."},
    "victim": {"en": "You may already have shared a code or paid. Act now.", "hi": "हो सकता है आपने कोड या पैसे दे दिए हों। तुरंत कदम उठाएँ।",
               "mr": "तुम्ही कोड किंवा पैसे दिले असू शकतात. लगेच पावले उचला."},
    "contact": {"en": "{name} is a saved contact, but accounts can be hacked. Call {name} on the number you already have before paying anything.",
                "hi": "{name} सेव किया हुआ संपर्क है, पर अकाउंट हैक हो सकता है। कुछ भी भेजने से पहले {name} को उसी पुराने नंबर पर कॉल करें।",
                "mr": "{name} सेव्ह केलेला संपर्क आहे, पण अकाउंट हॅक होऊ शकते. काहीही पाठवण्यापूर्वी {name} ला जुन्या नंबरवर कॉल करा."},
    "safe": {"en": "This looks like a normal chat.{money} Nobody asked you to pay a stranger or share a bank or WhatsApp code.",
             "hi": "यह सामान्य बातचीत लगती है।{money} किसी ने अनजान व्यक्ति को पैसे भेजने या बैंक/व्हाट्सऐप कोड बताने को नहीं कहा।",
             "mr": "हे सामान्य संभाषण दिसते.{money} कोणीही अनोळखी व्यक्तीला पैसे पाठवायला किंवा बँक/व्हॉट्सॲप कोड सांगायला सांगितले नाही."},
    "safe_money": {"en": " Money was mentioned ({amts}).", "hi": " पैसों का ज़िक्र हुआ ({amts})।", "mr": " पैशांचा उल्लेख झाला ({amts})."},
    "caution": {"en": "Mostly normal, but stay alert: {what}", "hi": "ज़्यादातर सामान्य है, पर सावधान रहें: {what}", "mr": "बहुतांश सामान्य आहे, पण सावध रहा: {what}"},
}
MSG_TACTIC = {
    "verify_block": {"en": "Discourages you from calling to check", "hi": "कॉल करके पुष्टि करने से रोकता है", "mr": "कॉल करून खात्री करण्यापासून अडवतो"},
    "familiarity": {"en": "Acts familiar to win trust", "hi": "भरोसा जीतने के लिए जान-पहचान जताता है", "mr": "विश्वास मिळवण्यासाठी ओळख दाखवतो"},
    "channel": {"en": "Pushes a link, app or another platform", "hi": "लिंक, ऐप या दूसरे प्लेटफ़ॉर्म पर ले जाता है", "mr": "लिंक, ॲप किंवा दुसऱ्या प्लॅटफॉर्मवर नेतो"},
    "new_number": {"en": "Claims a new number", "hi": "नया नंबर होने का दावा", "mr": "नवीन नंबर असल्याचा दावा"},
}


def _fmt_amts(xs):
    xs = list(dict.fromkeys(xs))[:4]
    return ", ".join(f"₹{x:,}" for x in xs)


def compose_chat(F: dict, ctx: dict | None, lang: str, level: int) -> dict:
    """Chat-specific sentences for the SOS report."""
    lang = lang if lang in ("en", "hi", "mr") else "en"
    g = lambda key, **kw: S[key][lang].format(**kw)
    lines, actions = [], []
    if level >= 2:
        if F.get("authority_quote"):
            lines.append(g("authority", q=F["authority_quote"]))
        if F["money_requests"]:
            amts = _fmt_amts(F["amounts"])
            lines.append(g("money", n=F["money_requests"], amts=f" ({amts})" if amts else ""))
        if F["escalation"]:
            lines.append(g("escalation", first=f"{F['amounts'][0]:,}", last=f"{max(F['amounts']):,}"))
        if F["blocking"]:
            k = {"en": f" ({F['verify_blocks']} times)", "hi": f" ({F['verify_blocks']} बार)", "mr": f" ({F['verify_blocks']} वेळा)"}[lang] if F["verify_blocks"] > 1 else ""
            lines.append(g("blocking", k=k))
        for kind in dict.fromkeys(F["otp"]):
            lines.append(g("otp_" + kind))
        if F.get("threat_quote"):
            lines.append(g("threat", q=F["threat_quote"]))
        for k in ("secrecy", "reward", "familiarity", "new_number", "channel"):
            if F.get(k):
                lines.append(g(k))
        if F.get("user_calls") and F["blocking"]:
            lines.append(g("user_call"))
        if F.get("victim_action"):
            lines.insert(0, g("victim"))
        if ctx and ctx.get("contacts_permission") and ctx.get("contact_status") == "safe":
            actions.append(g("contact", name=(ctx.get("name") or "this person")))
    facts = []
    for fid, rx, txt, src in FACTS:
        if fid in F.get("fact_ids", []):
            facts.append(f"{S['fact'][lang]}{txt.get(lang, txt['en'])} ({src})")
    safe = None
    if level < 2:
        amts = _fmt_amts(F.get("money_mentions", []))
        safe = g("safe", money=g("safe_money", amts=amts) if amts else "")
        if "delivery" in F.get("otp", []):
            safe += " " + g("otp_delivery")
    return {"lines": lines, "facts": facts[:5], "actions": actions, "safe": safe}


def message_notes(text: str, lang: str, level: int) -> tuple[list[str], list[str]]:
    """Per-message extras for the SOS explanation: tactic notes + fact checks."""
    lang = lang if lang in ("en", "hi", "mr") else "en"
    tac = tactics(text)
    flags = [MSG_TACTIC[k][lang] for k in ("verify_block", "familiarity", "channel", "new_number") if k in tac and level >= 2]
    return flags, (fact_checks(text, lang) if level >= 2 else [])
