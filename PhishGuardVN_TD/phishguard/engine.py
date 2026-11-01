import json
from pathlib import Path
import joblib
import numpy as np
import xgboost as xgb
from .features import feature_frame, extract_urls, normalize_url, LEXICAL, URL_PATTERN
from .signals import rule_evidence
from .training import text_input

class Engine:
    def __init__(self, directory):
        directory=Path(directory)
        self.manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        self.url = xgb.XGBClassifier()
        self.url.load_model(str(directory / 'url_model.json'))
        self.text=joblib.load(directory/'text_model.joblib')
        self.se=joblib.load(directory/'se_models.joblib')
        self.background=joblib.load(directory/'url_background.joblib')
        self._explainer=None

    def explain(self, frame):
        if hasattr(self.url,'get_booster'):
            # Exact Tree SHAP supplied by XGBoost. Contributions are in log-odds.
            booster=self.url.get_booster();d=xgb.DMatrix(frame)
            contribution=booster.predict(d,pred_contribs=True)[0];base=float(contribution[-1]);values=contribution[:-1]
            margin=float(booster.predict(d,output_margin=True)[0])
            method='XGBoost Tree SHAP (exact)'
        else:
            import shap
            scaler=self.url.steps[0][1];classifier=self.url.steps[-1][1]
            if self._explainer is None:self._explainer=shap.LinearExplainer(classifier,scaler.transform(self.background))
            transformed=scaler.transform(frame)
            values=np.asarray(self._explainer.shap_values(transformed))[0];base=float(self._explainer.expected_value);margin=float(classifier.decision_function(transformed)[0]);method='SHAP LinearExplainer'
        residual=abs(base+float(np.sum(values))-margin)
        order=np.argsort(np.abs(values))[::-1][:8]
        return {'method':method,'unit':'log_odds_phishing','base_value':base,'model_margin':margin,'additivity_residual':residual,'all_contributions':{k:float(v) for k,v in zip(LEXICAL,values)},'top_features':[{'feature':LEXICAL[i],'value':float(frame.iloc[0,i]),'contribution':float(values[i]),'direction':'increase' if values[i]>0 else 'decrease'} for i in order]}

    def analyze(self,text='',urls=None):
        text=text.strip();found=extract_urls(text)
        for value in urls or []:
            normalized=normalize_url(value)
            if normalized not in found:found.append(normalized)
        if len(found)>20:raise ValueError('Tối đa 20 URL mỗi lần kiểm tra.')
        if not text and not found:raise ValueError('Nhập nội dung hoặc URL để kiểm tra.')
        remaining=URL_PATTERN.sub('',text.replace('[.]','.')).strip(' \n\t.,;:!?()')
        has_text=bool(remaining)
        details=[]
        for u in found:
            frame=feature_frame([u]);p=float(self.url.predict_proba(frame)[0,1])
            details.append({'url':u,'p_phishing':p,'prediction':'Phishing' if p>=self.manifest['url_threshold'] else 'Legitimate','shap':self.explain(frame)})
        purl=max((r['p_phishing'] for r in details),default=None)
        ptext=float(self.text.predict_proba([text_input(text)])[0,1]) if has_text else None
        if ptext is None and purl is None:raise ValueError('Không nhận diện được nội dung hợp lệ.')
        fusion=self.manifest['fusion']
        if ptext is None:score=purl;cut=self.manifest['url_threshold'];mode='url_only';alpha=None
        elif purl is None:score=ptext;cut=self.manifest['text_threshold'];mode='text_only_proxy';alpha=None
        else:alpha=fusion['alpha'];score=alpha*ptext+(1-alpha)*purl;cut=fusion['threshold'];mode='fusion_proxy'
        signals=[]
        if has_text:
            for evidence in rule_evidence(text):
                model=self.se[evidence['key']];prob=float(model.predict_proba([text_input(text)])[0,list(model.classes_).index(1)]) if 1 in model.classes_ else 0.
                support=self.manifest.get('se_support',{}).get(evidence['key'],{})
                adequate=support.get('adequate_counts',False)
                evidence.update({'probability':prob,'predicted':bool(prob>=self.manifest['se_thresholds'][evidence['key']]) if adequate else None,'threshold':self.manifest['se_thresholds'][evidence['key']],'support':support,'validation_status':'weak_labels_only' if adequate else 'insufficient_positive_samples'})
                signals.append(evidence)
        return {'risk_score':score,'risk_percent':round(score*100,1),'alert':bool(score>=cut),'risk_level':'CẢNH BÁO' if score>=cut else 'CHƯA PHÁT HIỆN NGUY CƠ CAO','threshold':cut,'mode':mode,'alpha':alpha,'p_text_spam_scam':ptext,'p_url_phishing':purl,'urls':details,'signals':signals,'model_version':'0.5.0','limitations':['Điểm văn bản/kết hợp là kết quả thử nghiệm trên nhãn spam/scam gộp chung, chưa phải xác suất phishing đã kiểm chứng.','Dấu hiệu Social Engineering được học từ nhãn tự động; nhận diện danh tính không chứng minh giả mạo.','Không truy cập URL và chưa sử dụng DNS/WHOIS trong mô hình hiện tại.','Kết quả thấp không đảm bảo an toàn; số báo cáo cộng đồng được hiển thị riêng.']}
