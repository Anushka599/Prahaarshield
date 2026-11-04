"""PrahaarShield SELF-TEST: one command, no manual testing.   python selftest.py

Runs ~60 hand-written messages and 20 hand-written conversations through the REAL model + Brain, then prints a
summary you can paste back (also saved to eval/selftest_report.md).  These cases were written for testing and are
NOT part of the training data. They are small and written by the developers, so treat the numbers as a smoke test,
not as a final accuracy claim.
"""
import json, statistics, sys, time
from pathlib import Path

from brain.brain import LEVELS, assess_chat, message_level
from engine.conversation import load_conv
from engine.text_engine import find_model_dir, load_engine

HERE = Path(__file__).resolve().parent
# (text, expected: 1 scam / 0 benign, language tag, note)
CASES = [
 # ---- scams
 ("Main CBI officer bol raha hu. Aapke Aadhaar se money laundering case hai, video call pe raho aur kisi ko mat batana warna arrest hoga", 1, "hinglish", "digital arrest"),
 ("This is Mumbai Cyber Crime. A parcel with drugs was booked in your name. You are under digital arrest, stay on video call.", 1, "en", "digital arrest"),
 ("मैं सीबीआई से बोल रहा हूँ, आपके आधार से मनी लॉन्ड्रिंग हुई है, वीडियो कॉल पर बने रहिए और किसी को मत बताइए", 1, "hi", "digital arrest"),
 ("मी मुंबई पोलिसांकडून बोलतोय, तुमच्या नावावर ड्रग्सचे पार्सल सापडले आहे, कॉल कट करू नका", 1, "mr", "digital arrest"),
 ("Pay ₹1,85,000 to the RBI safe account now to stop the arrest warrant. Do not tell your family.", 1, "en", "digital arrest demand"),
 ("Dear customer, your SBI YONO KYC has expired. Update now at sbi-yono-kyc-update.in or your account will be blocked today.", 1, "en", "kyc link"),
 ("Sir KYC ke liye OTP aaya hoga, wo abhi bata do warna account band ho jayega", 1, "hinglish", "kyc otp"),
 ("बैंक केवाईसी विभाग: आपका खाता आज बंद हो जाएगा। आया हुआ ओटीपी तुरंत बताइए", 1, "hi", "kyc otp"),
 ("बँकेकडून: तुमची केवायसी अपूर्ण आहे, आलेला ओटीपी लगेच सांगा नाहीतर खाते बंद होईल", 1, "mr", "kyc otp"),
 ("Please share the OTP you just received to complete verification", 1, "en", "otp ask"),
 ("Hi, this is Anil sir, new number. In a meeting, can't call. Buy 5 Amazon gift cards of ₹10,000 and send me the codes, keep it confidential", 1, "en", "boss gift cards"),
 ("Priya, main Mehta sir. Vendor ko abhi ₹3,40,000 transfer karo, accounts team ko mat batana. Account details neeche", 1, "hinglish", "boss payment"),
 ("मी मीटिंगमध्ये आहे, कॉल करू नकोस. वेंडरला ₹2,80,000 आत्ताच पाठव, डिटेल्स पाठवतो", 1, "mr", "boss payment"),
 ("🚀 Join our VIP trading group 💰 Guaranteed 10% weekly profit, only 20 seats left, deposit ₹30,000 in our app today", 1, "en", "investment"),
 ("Bhai ye stock kal 30% upar jayega, operator wala call hai, kisi ko mat batana, group join karo", 1, "hinglish", "investment tip"),
 ("तुमचा नफा काढण्यासाठी आधी ₹25,000 टॅक्स भरा, मग सगळे पैसे खात्यात येतील", 1, "mr", "withdraw fee"),
 ("Your profit of ₹3,48,000 is ready. Pay 15% tax first to withdraw it, otherwise the account will be frozen", 1, "en", "withdraw fee"),
 ("Part time job: like YouTube videos and earn ₹3,000 daily. First 3 tasks paid. Join our Telegram group", 1, "en", "job task"),
 ("Next task is prepaid: deposit ₹2,000 and get ₹2,700 back in 30 minutes. Limited slots, do it fast", 1, "en", "job prepaid"),
 ("घर बैठे पार्ट टाइम जॉब, रोज़ ₹2,500 कमाएँ। रजिस्ट्रेशन फीस ₹999 आज ही भरें", 1, "hi", "job fee"),
 ("Instant loan ₹2,00,000 in 10 minutes, no CIBIL check. Download QuickCash app", 1, "en", "loan"),
 ("Aapka loan approve ho gaya hai, bas ₹1,999 processing fee aaj bharni hogi warna approval cancel", 1, "hinglish", "loan fee"),
 ("Your loan is overdue. Pay ₹11,800 today or we will message all your contacts that you are a fraud", 1, "en", "loan threat"),
 ("कर्ज मिळण्यासाठी पहिला हप्ता आधी भरावा लागेल, आजच भरा", 1, "mr", "loan advance"),
 ("Download AnyDesk and give me the code, I will fix your KYC remotely", 1, "en", "remote app"),
 ("A p p r o v e   t h e   c o l l e c t   r e q u e s t   a n d   e n t e r   y o u r   U P I   P I N   t o   r e c e i v e   ₹5,000", 1, "en", "trick spaced"),
 ("Your KYC is exрired, update nоw at sbi-kyc-verify.top and share the 0TP", 1, "en", "trick homoglyph"),
 ("🔥🔥 URGENT 🔥🔥 Your account will be blocked 🚨 click link and verify KYC 💳💳 bit.ly/3kYcUpd ⏰", 1, "en", "emoji scam"),
 ("Sir aapke naam pe parcel mein drugs mile hai 🚔 case darj ho gaya hai, call cut mat karna 😠", 1, "hinglish", "emoji short"),
 # ---- benign (including look-alikes)
 ("Beta kal ki fees ₹18,500 bhej di hai, receipt bhej dena 🙏", 0, "hinglish", "family money"),
 ("Guys DBMS assignment kal 11:59 PM tak submit karna hai portal pe", 0, "hinglish", "college"),
 ("Rent for October is ₹18,500, transferring tonight. Can you send the electricity bill too?", 0, "en", "rent"),
 ("Your OTP for login is 482913. Do not share it with anyone. SBI never asks for OTP.", 0, "en", "genuine otp"),
 ("Dear customer, ₹2,500 debited from A/c XX1234 on 21-Oct via UPI. Not you? Call 1800-1234 (toll free).", 0, "en", "bank alert"),
 ("सर्व सभासदांना सूचना: तिसऱ्या तिमाहीचे देखभाल शुल्क ₹4,200 10 तारखेपर्यंत भरावे", 0, "mr", "society notice"),
 ("बेटा, नया पेंशन फॉर्म बैंक में जमा कर दिया है। मैनेजर ने कहा अगले महीने से पेंशन खाते में आएगी", 0, "hi", "family hindi"),
 ("Bhai ek forward aaya hai 'digital arrest' wala, ye scam hai, kabhi paise mat bhejna, 1930 pe report karo", 0, "hinglish", "awareness"),
 ("*Public advisory* Fake loan apps ask for processing fees before disbursal. Never pay any fee first. Report on 1930.", 0, "en", "awareness"),
 ("Team, please release the vendor payment for Zenith after approval in ERP. Approval note AP/2026/1187.", 0, "en", "office payment"),
 ("Salary got credited today 🎉 finally I can clear my credit card bill of ₹22,000", 0, "en", "salary"),
 ("Your education loan of ₹12,00,000 has been sanctioned. Disbursement will be made directly to the university.", 0, "en", "genuine loan"),
 ("Dear Parent, the second-term fee of ₹24,500 is due by 15 October. Pay through the school portal.", 0, "en", "school fee"),
 ("Your electricity bill of ₹2,346 is generated. Due date 18 October. Pay on the official app.", 0, "en", "utility"),
 ("Flat 40% off on all courses this Diwali! Enrol now on our app 🎓📚 Offer valid till Sunday", 0, "en", "genuine offer"),
 ("Oyeee 😂😂 kal ka plan pakka na? pizza ka ₹350 GPay kar dena baad me", 0, "hinglish", "friends"),
 ("Aate waqt doodh aur bread le aana. Aur mummy ki medicines bhi", 0, "hinglish", "family"),
 ("Happy Birthday Aditi 🎂🎉 Party kab de rahi hai? 😄", 0, "hinglish", "wishes"),
 ("Good morning! Small steps every day become big achievements 🌅 Have a great day", 0, "en", "quote"),
 ("Meeting moved to Friday 3 PM, conference room B. Please confirm attendance.", 0, "en", "office"),
 ("Your Amazon order has been shipped and will arrive tomorrow. Track it in the Amazon app.", 0, "en", "delivery"),
 ("तुमचा SIP हप्ता ₹5,000 या महिन्यात कापला गेला आहे. तपशील अधिकृत ॲपमध्ये पहा", 0, "mr", "sip"),
 ("Mom, can you send ₹2,000 for my project materials? I'll show you the bill.", 0, "en", "family money"),
 ("🙏🙏🙏", 0, "other", "emoji only"),
 # ---- v3.2: financial threats (scam) and money threats in normal life (benign)
 ("Your UPI will stop in 1 hour. Share the 6 digit code you just got or your account gets frozen and ₹3,000 fine", 1, "en", "threat kyc"),
 ("Bhai tumhara loan ka ₹2,800 baaki hai, aaj nahi diya toh tumhare saare relatives ko msg jayega ki tum chor ho", 1, "hinglish", "threat loan"),
 ("निवेश खाते से पैसे निकालने हैं तो पहले ₹40,000 शुल्क भरें, वरना पूरा पैसा ज़ब्त", 1, "hi", "threat investment"),
 ("तुमच्या नावावर गुन्हा दाखल आहे, ₹55,000 भरले नाहीत तर उद्या अटक होईल", 1, "mr", "threat digital arrest"),
 ("Main boss hu, ye ₹70,000 abhi transfer nahi kiye toh kal se office mat aana", 1, "hinglish", "threat boss"),
 ("Reminder: your car loan EMI of ₹16,200 is due on the 7th. A late fee applies after the due date. Ignore if paid.", 0, "en", "genuine emi"),
 ("Arre ₹600 wapas kar warna agli baar chai tera bill 😂", 0, "hinglish", "friend banter"),
 ("बिजली विभाग: बकाया बिल 15 तारीख तक नहीं भरा तो नियमानुसार कनेक्शन काटा जा सकता है। आधिकारिक ऐप से भुगतान करें।", 0, "hi", "genuine bill"),
 ("आई: या महिन्यात परत फोनचे बिल वाढले तर रिचार्ज बंद 😠", 0, "mr", "family threat"),
 ("Landlord: the rent is 2 weeks late, please pay by Saturday or I'll have to add a late fee.", 0, "en", "genuine rent"),
]


def main():
    eng = load_engine()
    try:
        conv = load_conv(find_model_dir())
    except FileNotFoundError:
        conv = None
    th = float(getattr(eng, "threshold", 0.5))
    print(f"\nEngine: {type(eng).__name__} | threshold {th} | conversation model: {type(conv).__name__ if conv else 'rules (not trained)'}\n")
    rows, times = [], []
    for text, exp, lang, note in CASES:
        t0 = time.time(); a = eng.analyze(text); times.append((time.time() - t0) * 1000)
        lvl = message_level(a, th); pred = int(lvl >= 2)
        rows.append((text, exp, lang, note, a, lvl, pred))
    tp = sum(1 for r in rows if r[1] and r[6]); fn = sum(1 for r in rows if r[1] and not r[6])
    fp = sum(1 for r in rows if not r[1] and r[6]); tn = sum(1 for r in rows if not r[1] and not r[6])
    print("=== 1. SINGLE MESSAGES ===")
    print(f"scams caught {tp}/{tp+fn}   |   benign wrongly flagged {fp}/{fp+tn}   |   median {statistics.median(times):.0f} ms per message")
    bylang = {}
    for r in rows:
        d = bylang.setdefault(r[2], [0, 0]); d[0] += int(r[6] == r[1]); d[1] += 1
    print("correct by language:", {k: f"{v[0]}/{v[1]}" for k, v in bylang.items()})
    wrong = [r for r in rows if r[6] != r[1]]
    for r in wrong:
        print(f"  MISS  expected {'SCAM' if r[1] else 'SAFE'} got L{r[5]} p={r[4]['p_scam']:.2f} type={r[4]['scam_type']} [{r[3]}] :: {r[0][:90]}")
    # ---- conversations
    chats = [json.loads(l) for l in open(HERE / "eval" / "written_chats.jsonl", encoding="utf-8")]
    res = []
    for ch in chats:
        msgs, items, maxlvl, first_l3, first_l4 = [], [], 0, None, None
        for i, m in enumerate(ch["messages"]):
            d = "in" if m["speaker"] == "them" else "out"
            if d == "in":
                a, fe = eng.analyze_full(m["text"])
            else:
                a, fe = None, eng.features(m["text"])
            msgs.append({"id": str(i), "direction": d, "text": m["text"], "analysis": a})
            items.append({"vec": fe["vec"], "raw": fe["raw"], "speaker": "them" if d == "in" else "me"})
            if d == "in":
                cv = conv.predict(items) if conv else None
                lvl = assess_chat(msgs, th, None, cv)["level"]
                maxlvl = max(maxlvl, lvl)
                if lvl >= 3 and first_l3 is None: first_l3 = i
                if lvl >= 4 and first_l4 is None: first_l4 = i
        res.append((ch, maxlvl, first_l3, first_l4))
    scam_ch = [r for r in res if r[0]["kind"] != "benign"]; ben_ch = [r for r in res if r[0]["kind"] == "benign"]
    caught = sum(1 for r in scam_ch if r[1] >= 3); crit = sum(1 for r in scam_ch if r[1] >= 4); fa = sum(1 for r in ben_ch if r[1] >= 3)
    print("\n=== 2. CONVERSATIONS (20 hand-written, streamed message by message) ===")
    print(f"scam chats reaching Dangerous (L3+): {caught}/{len(scam_ch)}   reaching Critical (L4): {crit}/{len(scam_ch)}   |   normal chats falsely alerted (L3+): {fa}/{len(ben_ch)}")
    for ch, mx, f3, f4 in res:
        ok = (mx >= 3) == (ch["kind"] != "benign")
        if not ok:
            print(f"  MISS  chat {ch['id']} ({ch['kind']}/{ch['scam_type']}) max level L{mx}")
    print("\nper chat (id kind -> max level, first L3 message index, first L4 message index):")
    print("  " + " | ".join(f"{ch['id']} {ch['kind'][:4]}->L{mx}" + (f" @{f3}/{f4}" if f3 is not None else "") for ch, mx, f3, f4 in res))
    # ---- identifiers
    from engine.identifiers import check_link, check_phone, check_upi
    F = {"link": check_link, "upi": check_upi, "phone": check_phone}
    cases = json.load(open(HERE / "eval" / "identifier_tests.json", encoding="utf-8"))
    tpi = fpi = fni = tni = 0
    for c in cases:
        r = F[c["kind"]](c["value"], c.get("text", "")); fl = r["risk"] in ("registry_hit", "suspicious")
        if c["expected"] == "bad": tpi += fl; fni += not fl
        elif c["expected"] == "good": fpi += fl; tni += not fl
    print(f"\n=== 3. LINK / UPI / PHONE CHECKS (125 cases written by the developers) ===\nfake flagged {tpi}/{tpi+fni}   genuine wrongly flagged {fpi}/{fpi+tni}")
    print("\nDONE. Copy everything above and send it back. (Saved to eval/selftest_report.md)")


if __name__ == "__main__":
    import io, contextlib
    buf = io.StringIO()
    class Tee(io.TextIOBase):
        def write(self, s): sys.__stdout__.write(s.encode(sys.__stdout__.encoding, errors="replace").decode(sys.__stdout__.encoding)); buf.write(s); return len(s)
    with contextlib.redirect_stdout(Tee()):
        main()
    (HERE / "eval" / "selftest_report.md").write_text("```\n" + buf.getvalue() + "\n```", encoding="utf-8")
