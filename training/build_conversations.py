"""Build the conversation dataset for M7 from the v3 message splits (laptop, seconds).

Run AFTER prepare_v3.py:   python build_conversations.py
Out: conversations/conv_train.jsonl conv_val.jsonl conv_test.jsonl
  - assembled scam chats (approach -> pressure -> demand, with user replies), slow-burn chats (friendly first),
    benign chats (casual + hard negatives: bank alerts, OTP SMS, family money, office urgency, awareness forwards)
  - messages are drawn ONLY from the same split (train chats from train messages, ...) -> no leakage into M7 tests
  - the 20 hand-written chats (conversations_written.jsonl) go to TEST only
Each message: speaker (them/me), text, stage (none/approach/pressure/demand for 'them'), is_scam_msg.
"""
import json, os, random, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.join(HERE, "prepared_v3"), os.path.join(HERE, "conversations")
TYPES = ["digital_arrest", "kyc_bank", "boss_impersonation", "investment_group", "job_task", "loan_app"]
SIZES = {"train": (90, 90, 700), "val": (12, 12, 90), "test": (12, 12, 90)}   # per type scam, slow-burn total, benign total
R_SCAM = {"en": ["Who is this?", "What happened?", "Ok", "I don't understand", "Is this real?", "How much?", "Ok sir", "I'm scared", "Wait, let me check", "Please explain"],
          "hinglish": ["Kaun bol raha hai?", "Kya hua?", "Ok", "Samjha nahi", "Sach me?", "Kitna dena hoga?", "Theek hai sir", "Mujhe dar lag raha hai", "Ruko check karta hu", "Haan bolo"],
          "hi_deva": ["कौन बोल रहा है?", "क्या हुआ?", "ठीक है", "समझ नहीं आया", "सच में?", "कितने पैसे?", "जी सर", "मुझे डर लग रहा है"],
          "mr": ["कोण बोलतंय?", "काय झालं?", "ठीक आहे", "समजलं नाही", "खरंच?", "किती पैसे?", "हो सर", "मला भीती वाटतेय"]}
R_BEN = {"en": ["Ok 👍", "Thanks!", "Sure", "Done", "😂", "Got it", "See you", "Yes"], "hinglish": ["Ok 👍", "Haan", "Theek hai", "Done", "😂😂", "Achha", "Thanks yaar", "Pakka"],
         "hi_deva": ["ठीक है", "हाँ", "धन्यवाद", "अच्छा", "जी"], "mr": ["ठीक आहे", "हो", "धन्यवाद", "बरं", "चालेल"]}
R_SCAM["other"] = R_SCAM["en"]; R_BEN["other"] = R_BEN["en"]


# user replies by intent: after approach -> confused/curious, after pressure -> scared/doubtful, after demand -> comply/leak/resist
U = {
 "approach": {"en": ["Who is this?", "Which company?", "I didn't apply for anything", "How did you get my number?", "Is this real?", "What is this about?", "Sorry, which department?", "Hmm ok, tell me more"],
              "hinglish": ["Kaun bol raha hai?", "Kaunsi company?", "Maine toh apply nahi kiya", "Mera number kahan se mila?", "Ye sach hai kya?", "Kis baare me?", "Kaunsa department?", "Achha, aur batao"],
              "hi_deva": ["आप कौन?", "कौन सी कंपनी?", "मैंने तो अप्लाई नहीं किया", "मेरा नंबर कहाँ से मिला?", "क्या यह सच है?", "किस बारे में?"],
              "mr": ["कोण बोलतंय?", "कोणती कंपनी?", "मी तर अर्ज केला नाही", "माझा नंबर कुठून मिळाला?", "हे खरं आहे का?", "Kon bolatay?", "Konti company?", "Mi apply nahi kela"]},
 "pressure": {"en": ["Please don't block my account", "I haven't done anything wrong!", "This sounds fake to me", "Why didn't I get any email?", "I'm scared, what should I do?", "Can I visit the branch instead?", "Let me ask my son first", "Please give me some time"],
              "hinglish": ["Please account block mat karo", "Maine kuch galat nahi kiya!", "Ye fake lag raha hai", "Mujhe koi email kyu nahi aaya?", "Mujhe darr lag raha hai, kya karu?", "Main branch jaa ke kar lu?", "Pehle bete se puchh lu", "Thoda time do please"],
              "hi_deva": ["कृपया खाता बंद मत कीजिए", "मैंने कुछ गलत नहीं किया!", "यह फ़र्ज़ी लग रहा है", "मुझे डर लग रहा है, क्या करूँ?", "मैं शाखा जाकर कर लूँ?", "पहले बेटे से पूछ लूँ"],
              "mr": ["प्लीज खाते बंद करू नका", "मी काहीच चुकीचं केलं नाही!", "हे खोटं वाटतंय", "मला भीती वाटतेय, काय करू?", "मी शाखेत जाऊन करू का?", "Plz account band karu naka", "Mala bhiti vatatey", "Adhi mulala vicharto"]},
 "demand": {"en": ["Ok sending now", "Done, paid ₹1,999. Check screenshot", "The OTP is 849201", "Why do you need my OTP on chat?", "I won't pay before getting the money", "Can you deduct it from the loan amount?", "Installed the app, what next?", "No, I'll call the bank myself", "I'll report this to 1930"],
            "hinglish": ["Ok bhej raha hu", "Ho gaya, ₹1,999 bhar diya. Screenshot dekho", "OTP 849201 hai", "OTP chat pe kyu chahiye?", "Pehle paisa do phir pay karunga", "Loan amount se kaat lo na", "App install kar liya, ab kya?", "Nahi, main khud bank ko call karunga", "Main 1930 pe report karunga"],
            "hi_deva": ["ठीक है, भेज रहा हूँ", "हो गया, ₹1,999 भर दिए, स्क्रीनशॉट देखो", "ओटीपी 849201 है", "ओटीपी चैट पर क्यों चाहिए?", "नहीं, मैं खुद बैंक को फोन करूँगा", "मैं 1930 पर शिकायत करूँगा"],
            "mr": ["ठीक आहे, पाठवतो", "झालं, ₹1,999 भरले, स्क्रीनशॉट बघा", "OTP 849201 आहे", "OTP चॅटवर का हवा?", "नाही, मी स्वतः बँकेला फोन करतो", "Zala, paise bharle", "OTP 849201 aahe", "Mi 1930 la takrar karen"]},
}
U_BEN = {"en": ["Ok 👍", "Thanks!", "Sure, will do", "Done, paid it", "😂😂", "Got it", "See you there", "Yes, sending now", "Oh no, I forgot, paying today", "Sorry yaar, tomorrow pakka", "Haha fine", "Can you remind me later?"],
         "hinglish": ["Ok 👍", "Haan", "Theek hai", "Ho gaya, bhar diya", "😂😂", "Achha", "Thanks yaar", "Pakka", "Arre bhool gaya, aaj bhar deta hu", "Sorry, kal pakka", "Haha chal theek hai", "Baad me yaad dila dena"],
         "hi_deva": ["ठीक है 👍", "हाँ", "धन्यवाद", "भर दिया", "😂😂", "अच्छा", "पक्का", "अरे भूल गया, आज भर देता हूँ", "माफ़ करना, कल पक्का"],
         "mr": ["ठीक आहे 👍", "हो", "धन्यवाद", "भरलं", "😂😂", "बरं", "नक्की", "अरे विसरलो, आज भरतो", "Ho, bharla", "Sorry, udya nakki", "Bara"]}
THREAT_RX = __import__("re").compile(r"arrest|warrant|jail|fir\b|block|freez|frozen|forfeit|zabt|jappt|seiz|confiscat|blacklist|cibil|defaulter|morph|legal|cancel|warna|nahitar|nahi toh|वरना|नाहीतर|गिरफ्तार|अटक|जेल|फ्रीज़|गोठव|ज़ब्त|जप्त|रद्द|cut|kaat|disconnect", __import__("re").I)


def _guess_lang(t):
    if re.search(r"[\u0900-\u097F]", t):
        return "mr" if re.search(r"आहे|नाही|का |तुला|मला|पाठव|झाल", t) else "hi_deva"
    if re.search(r"\b(aahe|aahes|nahi ka|tula|mala|pathav|kar na|zala|ahe)\b", t, re.I): return "mr"
    if re.search(r"\b(hai|kya|bhai|mera|tera|kar|nahi|yaar|bhej)\b", t, re.I): return "hinglish"
    return "en"


def stage_of(r):
    p = set(r.get("pillar_labels") or [])
    if p & {"P_CRED", "P_RESOURCE"}: return "demand"
    if p & {"P_STAKES", "P_CONTROL"}: return "pressure"
    return "approach"


def main():
    rnd = random.Random(2026)
    os.makedirs(OUT, exist_ok=True)
    for split, (per_type, n_slow, n_ben) in SIZES.items():
        rows = [json.loads(l) for l in open(os.path.join(SRC, f"{split}.jsonl"), encoding="utf-8")]
        pool = defaultdict(list)                      # (type, stage) -> rows
        for r in rows:
            if r["is_scam"] and r["scam_type"] in TYPES:
                pool[(r["scam_type"], stage_of(r))].append(r)
        ben_by_cat = defaultdict(list)
        for r in rows:
            if not r["is_scam"] and r["language"] != "other":
                ben_by_cat[r["category"] or "misc"].append(r)
        cats = [c for c in ben_by_cat if ben_by_cat[c]]
        chats = []

        def reply(lang, scam=True, stage="approach"):
            if scam:
                bank = U.get(stage if stage in U else "approach", U["approach"])
                return {"speaker": "me", "text": rnd.choice(bank.get(lang, bank["en"])), "stage": None, "is_scam_msg": 0}
            return {"speaker": "me", "text": rnd.choice(U_BEN.get(lang, U_BEN["en"])), "stage": None, "is_scam_msg": 0}

        def scam_part(t, lang):
            msgs = []
            plan = (["approach"] * rnd.choice([0, 1, 1, 2])) + (["pressure"] * rnd.choice([1, 1, 2])) + (["demand"] * rnd.choice([1, 1, 2]))
            if rnd.random() < 0.3:                    # chat stops before the demand (scam still visible)
                plan = [s for s in plan if s != "demand"] or ["approach"]
            for st in plan:
                cand = pool.get((t, st)) or pool.get((t, "approach")) or [r for k, v in pool.items() if k[0] == t for r in v]
                same = [r for r in cand if r["language"] == lang]
                cand2 = same if same and rnd.random() < 0.7 else cand
                thr = [r for r in cand2 if THREAT_RX.search(r["text"])]
                if st != "approach" and thr and rnd.random() < 0.45:      # >= ~25% of scam messages carry a (financial) threat
                    cand2 = thr
                r = rnd.choice(cand2)
                msgs.append({"speaker": "them", "text": r["text"], "stage": st, "is_scam_msg": 1})
                if rnd.random() < 0.75:
                    msgs.append(reply(r["language"], True, st))
            return msgs

        def benign_part(k):
            cat = rnd.choice(cats)
            msgs = []
            for _ in range(k):
                r = rnd.choice(ben_by_cat[cat] if rnd.random() < 0.7 else ben_by_cat[rnd.choice(cats)])
                msgs.append({"speaker": "them", "text": r["text"], "stage": "none", "is_scam_msg": 0})
                if rnd.random() < 0.6:
                    msgs.append(reply(r["language"], scam=False))
            return msgs

        for t in TYPES:
            for i in range(per_type):
                langs = [r["language"] for k, v in pool.items() if k[0] == t for r in v] or ["en"]
                chats.append({"kind": "scam", "scam_type": t, "messages": scam_part(t, rnd.choice(langs))})
        for i in range(n_slow):
            t = rnd.choice(TYPES)
            langs = [r["language"] for k, v in pool.items() if k[0] == t for r in v] or ["en"]
            chats.append({"kind": "slow_burn", "scam_type": t, "messages": benign_part(rnd.randint(2, 3)) + scam_part(t, rnd.choice(langs))})
        for i in range(n_ben):
            chats.append({"kind": "benign", "scam_type": "benign", "messages": benign_part(rnd.randint(2, 6))})
        # one consistent writing style per chat (half the assembled chats), same odds for scam and normal chats
        try:
            sys.path.insert(0, HERE); from style_augment import random_profile, stylize
            for c in chats:
                if rnd.random() < 0.5:
                    prof = random_profile(rnd)
                    for m in c["messages"]:
                        m["text"] = stylize(m["text"], _guess_lang(m["text"]), prof, rnd)
                    c["style"] = prof
        except ImportError:
            print("style_augment.py not found -> chats keep their original style")
        if split == "test":
            for w in (json.loads(l) for l in open(os.path.join(OUT, "conversations_written.jsonl"), encoding="utf-8")):
                for m in w["messages"]:
                    m["is_scam_msg"] = int(m["speaker"] == "them" and w["kind"] != "benign" and m["stage"] not in (None, "none"))
                    if m["speaker"] == "them" and m["stage"] is None:
                        m["stage"] = "none"
                chats.append({"kind": w["kind"], "scam_type": w["scam_type"], "messages": w["messages"], "source": "written", "wid": w["id"]})
        rnd.shuffle(chats)
        with open(os.path.join(OUT, f"conv_{split}.jsonl"), "w", encoding="utf-8") as f:
            for k, c in enumerate(chats):
                c["id"] = f"{split}-{k:04d}"
                c.setdefault("source", "assembled")
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        from collections import Counter
        print(f"{split}: {len(chats)} chats {dict(Counter(c['kind'] for c in chats))}  avg msgs {sum(len(c['messages']) for c in chats)/len(chats):.1f}")


if __name__ == "__main__":
    main()
