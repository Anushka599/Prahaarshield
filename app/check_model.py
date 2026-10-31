"""Run this FIRST:  python check_model.py   -> loads M1 (+ M7 if present) and scores 6 known messages."""
import time
from brain.brain import LEVELS, message_level
from engine.conversation import load_conv
from engine.text_engine import find_model_dir, load_engine

eng = load_engine()
conv = load_conv(find_model_dir())
tests = [("Aapke Aadhaar se money laundering case hai, video call pe raho aur kisi ko mat batana warna arrest hoga", "scam"),
         ("Your SBI KYC has expired. Update now at sbi-kyc-update.in or your account will be blocked today", "scam"),
         ("Please share the OTP you just received to complete verification", "scam"),
         ("तुमचा नफा काढण्यासाठी आधी ₹25,000 टॅक्स भरा, मग सगळे पैसे खात्यात येतील", "scam"),
         ("Beta kal ki fees ₹18,500 bhej di hai, receipt bhej dena 🙏", "benign"),
         ("Guys DBMS assignment kal raat tak submit karna hai portal pe", "benign")]
for text, expect in tests:
    t0 = time.time(); a = eng.analyze(text); ms = (time.time() - t0) * 1000
    lvl = message_level(a, eng.threshold)
    print(f"[{LEVELS[lvl]:10s}] p={a['p_scam']:.2f} {a['scam_type']:18s} {a['language']:8s} {ms:5.0f} ms | expected {expect:6s} | highlights {a['highlights']} | {text[:45]}")
print("\nconversation model:", type(conv).__name__ if conv else "not trained yet (rules are used)")
print("Model OK if the 4 scam lines are Suspicious/Dangerous and the 2 normal lines are Safe.")
