"""Paired GOLD validation tuner, ready for reviewed Week-4 text predictions.
Required CSV: sample_id, split, y_phishing, p_text, p_url, has_url, label_status.
Do not feed source spam/scam labels as y_phishing.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .training import threshold

def tune_reviewed_validation(csv_path,output_path):
    d=pd.read_csv(csv_path)
    required={'sample_id','split','y_phishing','p_text','p_url','has_url','label_status'}
    if not required.issubset(d):raise ValueError('Thiếu cột: '+str(sorted(required-set(d))))
    if not d['split'].eq('validation').all():raise ValueError('Chỉ nhận Validation; không được dùng Test để tối ưu.')
    if not d.label_status.eq('human_reviewed').all():raise ValueError('Cần nhãn phishing được người gán nhãn rà soát.')
    if d.sample_id.duplicated().any():raise ValueError('sample_id trùng.')
    if set(d.y_phishing.unique())!={0,1}:raise ValueError('Cần đủ hai lớp Legitimate/Phishing.')
    if not d.has_url.isin([0,1]).all():raise ValueError('has_url phải là 0 hoặc 1.')
    if not d.p_text.between(0,1).all() or not d.loc[d.has_url.eq(1),'p_url'].between(0,1).all():raise ValueError('Xác suất không hợp lệ.')
    if not d.has_url.any():raise ValueError('Cần mẫu có URL để lựa chọn alpha.')
    scores=[]
    for a in np.linspace(0,1,21):
        p=np.where(d.has_url.astype(bool),a*d.p_text+(1-a)*d.p_url.fillna(0),d.p_text)
        scores.append({**threshold(d.y_phishing,p),'alpha':float(a)})
    best=max(scores,key=lambda m:(m['f1'],m['recall'],-m['fpr']))
    result={'selected':best,'grid':scores,'rows':len(d),'label_status':'human_reviewed','test_used':False,'warning':'Operator must verify model training provenance and group disjointness for supplied predictions.'}
    Path(output_path).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('output');a=p.parse_args();tune_reviewed_validation(a.csv,a.output)
