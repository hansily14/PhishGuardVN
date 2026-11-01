"""Deterministic validation-only selection. Test is reserved for Week 9."""
import argparse, hashlib, json, platform, re, zipfile
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from xgboost import XGBClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, confusion_matrix, brier_score_loss
from sklearn.metrics.pairwise import cosine_similarity
from .features import feature_frame, extract_urls, normalize_url, domain_group, LEXICAL
from .signals import rule_evidence, LABELS
SEED=42

def text_input(s):
    return re.sub(r'\s+',' ',re.sub(r'\d{4,}',' [NUMBER] ',str(s))).strip()

def metric(y,p,t):
    pred=np.asarray(p)>=t;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),'fpr':float(fp/max(1,fp+tn)),'pr_auc':float(average_precision_score(y,p)) if np.sum(y)>0 else None,'brier':float(brier_score_loss(y,p)),'threshold':float(t),'confusion_matrix':[[int(tn),int(fp)],[int(fn),int(tp)]]}

def threshold(y,p):
    return max([metric(y,p,t) for t in np.linspace(.05,.95,91)],key=lambda m:(m['f1'],m['recall'],-m['fpr']))

def grouped_split(df,group):
    ti,vi=next(GroupShuffleSplit(n_splits=1,test_size=.15,random_state=SEED).split(df,groups=df[group]))
    tv=df.iloc[ti];a,b=next(GroupShuffleSplit(n_splits=1,test_size=3/17,random_state=SEED).split(tv,groups=tv[group]))
    result=df.copy();result['split']='test';result.loc[tv.iloc[a].index,'split']='train';result.loc[tv.iloc[b].index,'split']='validation'
    groups=[set(result.loc[result.split==s,group]) for s in ['train','validation','test']]
    assert not (groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
    return result

def prepare_sms(raw):
    raw=raw.copy();raw['input']=raw.message.map(text_input);raw['key']=raw.input.str.casefold()
    bad=set(raw.groupby('key').label.nunique().loc[lambda x:x>1].index)
    raw=raw[~raw.key.isin(bad)&raw.input.str.len().gt(4)].drop_duplicates('key').reset_index(drop=True)
    vector=TfidfVectorizer(analyzer='char',ngram_range=(3,5),binary=True,dtype=np.float32)
    sim=cosine_similarity(vector.fit_transform(raw.key));parent=list(range(len(raw)))
    def root(i):
        while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,j in zip(*np.where(np.triu(sim>=.88,k=1))):parent[root(int(j))]=root(int(i))
    raw['group']=[root(i) for i in range(len(raw))];df=grouped_split(raw,'group');max_cross={}
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        maximum=float(sim[np.ix_(df.index[df.split==a],df.index[df.split==b])].max());assert maximum<.88;max_cross[a+'_'+b]=maximum
    return df,{'conflicting_keys_removed':len(bad),'max_cross_similarity':max_cross,'rows':len(df),'splits':df.split.value_counts().to_dict()}

def train_all(input_dir,output_dir):
    input_dir=Path(input_dir);output_dir=Path(output_dir);models=output_dir/'models';reports=output_dir/'reports';data=output_dir/'data'
    for p in [models,reports,data]:p.mkdir(parents=True,exist_ok=True)
    zpath=input_dir/'vietnamese_sms_dataset.zip';upath=input_dir/'phiusiil+phishing+url+dataset.zip'
    manifest={'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [zpath,upath]},'seed':SEED,'versions':{'python':platform.python_version(),'sklearn':sklearn.__version__,'xgboost':xgboost.__version__},'test_evaluated':False}
    with zipfile.ZipFile(zpath) as z:raw=pd.read_csv(z.open('vietnamese_sms_dataset/full_dataset.csv'))
    sms,sms_audit=prepare_sms(raw);print('SMS',sms_audit,flush=True)
    sms[['message_id','group','split']].to_csv(data/'sms_split_manifest.csv',index=False)
    sms_domains={domain_group(u) for msg in sms.message for u in extract_urls(msg)}
    with zipfile.ZipFile(upath) as z:urls=pd.read_csv(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),usecols=['URL','label'])
    canonical=[];groups=[]
    for u in urls.URL:
        try:c=normalize_url(u);g=domain_group(c)
        except (ValueError,UnicodeError):c=None;g=None
        canonical.append(c);groups.append(g)
    urls['canonical']=canonical;urls['domain_group']=groups;urls=urls.dropna(subset=['canonical'])
    conflict=set(urls.groupby('canonical').label.nunique().loc[lambda s:s>1].index)
    urls=urls[~urls.canonical.isin(conflict)].drop_duplicates('canonical')
    assert set(urls.label.unique())=={0,1}
    urls['y_phishing']=1-urls.label.astype(int) # ORIGINAL PhiUSIIL: 1 Legitimate, 0 Phishing.
    excluded=urls.domain_group.isin(sms_domains);removed=int(excluded.sum());urls=urls[~excluded].reset_index(drop=True)
    urls=grouped_split(urls,'domain_group');urls[['canonical','domain_group','label','y_phishing','split']].to_csv(data/'url_split_manifest.csv.gz',index=False)
    print('URL',urls.split.value_counts().to_dict(),'SMS-domain excluded',removed,flush=True)
    train=urls[urls.split=='train'];val=urls[urls.split=='validation'];X=feature_frame(train.URL);Xv=feature_frame(val.URL);y=train.y_phishing.values;yv=val.y_phishing.values
    comparisons=[];candidates=[]
    for c in [.1,1.]:candidates.append((f'LogisticRegression_C{c}',make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=1500,random_state=SEED))))
    for depth in [4,6]:candidates.append((f'XGBoost_depth{depth}',XGBClassifier(n_estimators=240,max_depth=depth,learning_rate=.08,subsample=.9,colsample_bytree=.9,tree_method='hist',n_jobs=4,eval_metric='logloss',random_state=SEED)))
    selected=None;best_key=None
    for name,model in candidates:
        model.fit(X,y);m=threshold(yv,model.predict_proba(Xv)[:,1]);m['model']=name;comparisons.append(m);key=(m['f1'],m['recall'],-m['fpr'])
        if best_key is None or key>best_key:selected=(name,model,m);best_key=key
        print(name,m,flush=True)
    name,url_model,url_metrics=selected;joblib.dump(url_model,models/'url_model.joblib',compress=3)
    if isinstance(url_model,XGBClassifier):url_model.save_model(models/'url_model.json')
    joblib.dump(X.sample(min(100,len(X)),random_state=SEED).values,models/'url_background.joblib',compress=3)
    pd.DataFrame(comparisons).to_csv(reports/'url_validation_comparison.csv',index=False)
    st=sms[sms.split=='train'];sv=sms[sms.split=='validation']
    text_model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=2,max_features=40000,sublinear_tf=True),LogisticRegression(C=2,max_iter=1200,random_state=SEED))
    text_model.fit(st.input,st.label);ptext=text_model.predict_proba(sv.input)[:,1];text_metrics=threshold(sv.label,ptext);joblib.dump(text_model,models/'text_model.joblib',compress=3)
    sample=sms.sample(700,random_state=SEED).copy();targets=np.array([[int(x['present']) for x in rule_evidence(s)] for s in sample.message])
    for j,key in enumerate(LABELS):sample[key]=targets[:,j]
    sample['annotation_status']='weak_rules_v2_unreviewed'
    reviewed_path=data/'social_engineering_reviewed.csv'
    if reviewed_path.exists():
        reviewed=pd.read_csv(reviewed_path)
        required={'message_id','annotation_status',*LABELS}
        if not required.issubset(reviewed) or not reviewed.annotation_status.eq('human_reviewed').all() or reviewed.message_id.duplicated().any():raise ValueError('SE reviewed: cần ID duy nhất, đủ sáu nhãn và annotation_status=human_reviewed.')
        if not 500<=len(reviewed)<=800 or not set(reviewed.message_id).issubset(set(sms.message_id)):raise ValueError('SE reviewed: cần 500–800 ID thuộc corpus SMS đã làm sạch.')
        if not reviewed[LABELS].isin([0,1]).all().all():raise ValueError('SE reviewed: các nhãn phải là 0/1.')
        sample=sms[sms.message_id.isin(reviewed.message_id)].merge(reviewed[['message_id',*LABELS]],on='message_id',validate='one_to_one')
        sample['annotation_status']='human_reviewed'
    se_label_status=str(sample.annotation_status.iloc[0])
    sample.to_csv(data/'social_engineering_700_v2.csv',index=False,encoding='utf-8-sig')
    se_train=sample[sample.split=='train'];se_val=sample[sample.split=='validation'];se_models={};se_metrics={};se_thresholds={}
    for key in LABELS:
        yf=se_train[key];classifier=LogisticRegression(C=2,max_iter=1000,class_weight='balanced',random_state=SEED) if yf.nunique()>1 else DummyClassifier(strategy='most_frequent')
        model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=1,max_features=15000),classifier);model.fit(se_train.input,yf);probs=model.predict_proba(se_val.input)
        p=probs[:,list(model.classes_).index(1)] if 1 in model.classes_ else np.zeros(len(se_val))
        m=threshold(se_val[key],p) if se_val[key].nunique()>1 else {**metric(se_val[key],p,.5),'threshold_status':'default_insufficient_validation_classes'}
        m.update({'train_positives':int(yf.sum()),'validation_positives':int(se_val[key].sum()),'label_status':se_label_status,'train_negatives':int(len(yf)-yf.sum()),'validation_negatives':int(len(se_val)-se_val[key].sum())});se_models[key]=model;se_metrics[key]=m;se_thresholds[key]=m['threshold']
    joblib.dump(se_models,models/'se_models.joblib',compress=3)
    purl=[];has_url=[]
    for msg in sv.message:
        extracted=extract_urls(msg);has_url.append(bool(extracted));purl.append(float(url_model.predict_proba(feature_frame(extracted))[:,1].max()) if extracted else 0.)
    purl=np.array(purl);has_url=np.array(has_url);fusion_rows=[]
    for alpha in np.linspace(0,1,21):
        m=threshold(sv.label,np.where(has_url,alpha*ptext+(1-alpha)*purl,ptext));m['alpha']=float(alpha);fusion_rows.append(m)
    fusion=max(fusion_rows,key=lambda m:(m['f1'],m['recall'],-m['fpr']))
    fusion.update({'status':'proxy_only_not_validated_phishing_probability','target':'source_spam_or_scam','paired_validation_rows':int(has_url.sum()),'validation_rows':len(sv),'test_used':False})
    pd.DataFrame(fusion_rows).to_csv(reports/'fusion_validation_grid.csv',index=False)
    pd.DataFrame({'message_id':sv.message_id,'split':'validation','y_source_spam_scam':sv.label,'p_text':ptext,'p_url_max':purl,'has_url':has_url}).to_csv(reports/'paired_validation_predictions.csv',index=False)
    manifest.update({'url_selected':name,'url_threshold':url_metrics['threshold'],'feature_columns':LEXICAL,'infrastructure_model_used':False,'source_label_mapping':{'PhiUSIIL_0':'Phishing','PhiUSIIL_1':'Legitimate'},'url_rows':len(urls),'url_splits':urls.split.value_counts().to_dict(),'sms_audit':sms_audit,'sms_domain_rows_excluded_from_URL_corpus':removed,'url_conflicting_keys_removed':len(conflict),'text_model':'TFIDF_LR_source_binary','text_threshold':text_metrics['threshold'],'se_thresholds':se_thresholds,'se_label_status':se_label_status,'se_support':{key:{'train_positives':v['train_positives'],'validation_positives':v['validation_positives'],'adequate_counts':bool(v['train_positives']>=10 and v['train_negatives']>=10 and v['validation_positives']>=5 and v['validation_negatives']>=5)} for key,v in se_metrics.items()},'fusion':fusion})
    (models/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'url_validation':comparisons,'selected_url':name,'text_validation':text_metrics,'social_engineering_validation_weak_labels':se_metrics,'fusion_validation_proxy':fusion,'test_evaluated':False}
    (reports/'validation_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SELECTED',name,'FUSION proxy',fusion,flush=True);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input-dir',required=True);parser.add_argument('--output-dir',default='.')
    args=parser.parse_args();train_all(args.input_dir,args.output_dir)
