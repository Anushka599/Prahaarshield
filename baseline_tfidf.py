"""PrahaarShield - Step 2: TF-IDF + Logistic Regression baseline (laptop, ~1 minute).
Run after merge_and_split.py:   python baseline_tfidf.py
If this already gets ~0.99 F1, the data has shortcuts (leakage) - tell Claude before training MuRIL.
"""
import json, os
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prepared")
load = lambda n: [json.loads(l) for l in open(os.path.join(P, f"{n}.jsonl"), encoding="utf-8")]
tr, va, te = load("train"), load("val"), load("test")
wv = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True)
cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=200000)
X = lambda rows, fit=False: hstack([(wv.fit_transform if fit else wv.transform)([r["text"] for r in rows]),
                                    (cv.fit_transform if fit else cv.transform)([r["text"] for r in rows])])
Xtr = X(tr, fit=True)
for target in ["is_scam", "scam_type"]:
    clf = LogisticRegression(max_iter=3000, class_weight="balanced").fit(Xtr, [r[target] for r in tr])
    for name, rows in [("VAL", va), ("TEST", te)]:
        pred = clf.predict(X(rows))
        y = [r[target] for r in rows]
        print(f"\n===== {target} | {name} | macro-F1 = {f1_score(y, pred, average='macro'):.3f}")
        if target == "is_scam":
            print(classification_report(y, pred, target_names=["benign", "scam"], digits=3))
            for lang in sorted({r["language"] for r in rows}):
                idx = [i for i, r in enumerate(rows) if r["language"] == lang]
                if len(idx) >= 10:
                    print(f"   {lang:9s} n={len(idx):4d}  F1={f1_score([y[i] for i in idx], [pred[i] for i in idx], average='macro', zero_division=0):.3f}")
