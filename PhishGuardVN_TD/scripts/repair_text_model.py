from __future__ import annotations
import argparse, json, re, shutil, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix, average_precision_score
from sklearn.utils.validation import check_is_fitted
from sklearn.exceptions import NotFittedError

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "text_model.joblib"
MANIFEST_PATH = ROOT / "models" / "manifest.json"
RAW_PATH = ROOT / "data" / "raw" / "full_dataset.csv"
SPLIT_PATH = ROOT / "data" / "sms_split_manifest.csv"

def text_input(s):
    return re.sub(r"\s+", " ", re.sub(r"\d{4,}", " [NUMBER] ", str(s))).strip()

def is_pipeline_fitted(model):
    try:
        check_is_fitted(model)
        if not hasattr(model, "predict_proba"):
            return False, "Pipeline không có predict_proba"
        # Smoke test catches partially fitted transformers.
        model.predict_proba(["kiem tra mo hinh da fit"])
        return True, "Pipeline và các bước bên trong đã fit; predict_proba hoạt động"
    except (NotFittedError, AttributeError, ValueError) as exc:
        return False, f"Pipeline chưa fit/không dự đoán được: {type(exc).__name__}: {exc}"

def metric(y, p, threshold):
    pred = (np.asarray(p) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0,1]).ravel()
    return {
        "precision": float(precision_score(y,pred,zero_division=0)),
        "recall": float(recall_score(y,pred,zero_division=0)),
        "f1": float(f1_score(y,pred,zero_division=0)),
        "fpr": float(fp/max(1,fp+tn)),
        "pr_auc": float(average_precision_score(y,p)),
        "confusion_matrix_TN_FP_FN_TP": [[int(tn),int(fp)],[int(fn),int(tp)]],
        "threshold": float(threshold),
    }

def main():
    ap=argparse.ArgumentParser(description="Kiểm tra hoặc fit lại TF-IDF + Logistic Regression chỉ trên Train.")
    ap.add_argument("--repair", action="store_true", help="Fit lại nếu artifact hiện tại chưa fitted; backup artifact cũ trước khi thay.")
    args=ap.parse_args()
    if not RAW_PATH.exists() or not SPLIT_PATH.exists():
        raise FileNotFoundError("Thiếu data/raw/full_dataset.csv hoặc data/sms_split_manifest.csv")
    raw=pd.read_csv(RAW_PATH)
    split=pd.read_csv(SPLIT_PATH)
    required_raw={"message_id","message","label"}; required_split={"message_id","group","split"}
    if not required_raw.issubset(raw.columns) or not required_split.issubset(split.columns):
        raise ValueError("Schema SMS không đúng; cần message_id/message/label và message_id/group/split")
    if raw.message_id.duplicated().any() or split.message_id.duplicated().any():
        raise ValueError("message_id bị trùng; dừng để tránh ghép sai")
    df=raw.merge(split,on="message_id",how="inner",validate="one_to_one")
    if len(df)!=len(split): raise ValueError(f"Có {len(split)-len(df)} ID trong split manifest không tìm thấy ở full_dataset.csv")
    if set(df.split)!={"train","validation","test"}: raise ValueError("Split phải gồm train, validation, test")
    group_sets=[set(df.loc[df.split.eq(s),"group"]) for s in ["train","validation","test"]]
    if any(group_sets[i]&group_sets[j] for i in range(3) for j in range(i+1,3)):
        raise ValueError("Phát hiện group giao nhau giữa các split")
    print("SMS rows/splits:",len(df),df.split.value_counts().to_dict())
    model=None; fitted=False; reason="Chưa có artifact"
    if MODEL_PATH.exists():
        try:
            model=joblib.load(MODEL_PATH)
            fitted,reason=is_pipeline_fitted(model)
        except Exception as exc:
            reason=f"Không load được artifact: {type(exc).__name__}: {exc}"
    print("Artifact:",MODEL_PATH)
    print("Fitted:",fitted,"|",reason)
    if fitted:
        print("Không cần fit lại. Dùng tiếp artifact hiện tại.")
        return
    if not args.repair:
        print("BLOCKED: chưa thay đổi file. Nếu xác nhận đúng thư mục dự án, chạy lại với --repair.")
        return
    train=df[df.split.eq("train")]; val=df[df.split.eq("validation")]
    if train.label.nunique()!=2 or val.label.nunique()!=2:
        raise ValueError("Train và Validation phải có đủ hai lớp 0/1")
    model=make_pipeline(
        TfidfVectorizer(analyzer="char",ngram_range=(3,5),min_df=2,max_features=40000,sublinear_tf=True),
        LogisticRegression(C=2,max_iter=1200,random_state=42)
    )
    model.fit(train.message.map(text_input),train.label.astype(int))
    check_is_fitted(model)
    classes=[int(x) for x in model.classes_]
    if 1 not in classes: raise ValueError(f"Không tìm thấy lớp dương 1; classes={classes}")
    pval=model.predict_proba(val.message.map(text_input))[:,classes.index(1)]
    candidates=[metric(val.label.astype(int),pval,t) for t in np.linspace(.05,.95,91)]
    best=max(candidates,key=lambda m:(m["f1"],m["recall"],-m["fpr"]))
    MODEL_PATH.parent.mkdir(parents=True,exist_ok=True)
    if MODEL_PATH.exists():
        backup=MODEL_PATH.with_name(f"text_model_unfitted_backup_{time.strftime('%Y%m%d_%H%M%S')}.joblib")
        shutil.copy2(MODEL_PATH,backup); print("Backup:",backup)
    joblib.dump(model,MODEL_PATH,compress=3)
    manifest=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["text_threshold"]=best["threshold"]
    manifest["text_model"]="TFIDF_LR_source_binary_repaired"
    manifest["text_model_repair"]={"fit_rows":int(len(train)),"validation_rows":int(len(val)),"classes":classes,"validation_metrics":best,"fit_split":"train_only","threshold_selected_on":"validation","test_used_for_fit_or_tuning":False}
    MANIFEST_PATH.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    ok,msg=is_pipeline_fitted(joblib.load(MODEL_PATH))
    if not ok: raise RuntimeError("Artifact sau khi lưu vẫn chưa fitted: "+msg)
    print("REPAIRED:",msg)
    print("Validation threshold/metrics:",json.dumps(best,ensure_ascii=False,indent=2))
    print("Test chưa được dùng để fit hoặc chọn threshold.")

if __name__=="__main__": main()
