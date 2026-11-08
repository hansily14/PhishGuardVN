from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch.utils.data import Dataset
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, average_precision_score
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments, DataCollatorWithPadding

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data"/"raw"/"full_dataset.csv"
SPLIT=ROOT/"data"/"sms_split_manifest.csv"
OUT=ROOT/"models"/"xlmr_binary"
REPORT=ROOT/"reports"/"xlmr_binary_metrics.json"
MODEL_NAME="FacebookAI/xlm-roberta-base"

def text_input(s):
    return re.sub(r"\s+"," ",re.sub(r"\d{4,}"," [NUMBER] ",str(s))).strip()

class SmsDataset(Dataset):
    def __init__(self, frame, tokenizer, max_length):
        self.texts=frame.message.map(text_input).tolist()
        self.labels=frame.label.astype(int).tolist()
        self.tokenizer=tokenizer; self.max_length=max_length
    def __len__(self): return len(self.labels)
    def __getitem__(self,idx):
        item=self.tokenizer(self.texts[idx],truncation=True,max_length=self.max_length)
        item["labels"]=self.labels[idx]
        return item

def metrics(y,p,t):
    pred=(np.asarray(p)>=t).astype(int); tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0)),"fpr":float(fp/max(1,fp+tn)),"pr_auc":float(average_precision_score(y,p)),"confusion_matrix_TN_FP_FN_TP":[[int(tn),int(fp)],[int(fn),int(tp)]],"threshold":float(t)}

def main():
    ap=argparse.ArgumentParser(description="Fine-tune XLM-RoBERTa binary SMS baseline; labels remain source Legitimate vs Spam/Scam.")
    ap.add_argument("--epochs",type=float,default=2.0)
    ap.add_argument("--max-length",type=int,default=160)
    ap.add_argument("--batch-size",type=int,default=1)
    ap.add_argument("--grad-accum",type=int,default=8)
    ap.add_argument("--model-name",default=MODEL_NAME)
    args=ap.parse_args()
    if not RAW.exists() or not SPLIT.exists(): raise FileNotFoundError("Thiếu SMS raw hoặc split manifest")
    raw=pd.read_csv(RAW); split=pd.read_csv(SPLIT)
    df=raw.merge(split,on="message_id",validate="one_to_one")
    if len(df)!=len(split): raise ValueError("Không ghép đủ message_id")
    if set(df.label.unique())!={0,1}: raise ValueError("Dữ liệu hiện tại chỉ hỗ trợ nhãn nhị phân 0/1")
    groups=[set(df.loc[df.split.eq(s),"group"]) for s in ["train","validation","test"]]
    if any(groups[i]&groups[j] for i in range(3) for j in range(i+1,3)): raise ValueError("Group leakage across splits")
    train=df[df.split.eq("train")].copy(); val=df[df.split.eq("validation")].copy(); test=df[df.split.eq("test")].copy()
    print("Device:","CUDA" if torch.cuda.is_available() else "CPU", "| counts:",len(train),len(val),len(test))
    tokenizer=AutoTokenizer.from_pretrained(args.model_name)
    model=AutoModelForSequenceClassification.from_pretrained(args.model_name,num_labels=2,id2label={0:"LEGITIMATE",1:"SPAM_SCAM"},label2id={"LEGITIMATE":0,"SPAM_SCAM":1})
    model.config.use_cache=False
    model.gradient_checkpointing_enable()
    train_ds=SmsDataset(train,tokenizer,args.max_length); val_ds=SmsDataset(val,tokenizer,args.max_length)
    collator=DataCollatorWithPadding(tokenizer=tokenizer,pad_to_multiple_of=8 if torch.cuda.is_available() else None)
    OUT.mkdir(parents=True,exist_ok=True)
    # Pin transformers==4.46.3 in requirements_xlmr.txt; API below uses evaluation_strategy.
    training_args=TrainingArguments(
        output_dir=str(OUT/"trainer_runs"),num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,per_device_eval_batch_size=2,
        gradient_accumulation_steps=args.grad_accum,learning_rate=2e-5,
        weight_decay=0.01,warmup_ratio=0.1,lr_scheduler_type="linear",
        evaluation_strategy="epoch",save_strategy="epoch",load_best_model_at_end=True,
        metric_for_best_model="eval_loss",greater_is_better=False,save_total_limit=1,
        logging_steps=25,report_to="none",fp16=bool(torch.cuda.is_available()),
        gradient_checkpointing=True,dataloader_num_workers=0,seed=42,
    )
    trainer=Trainer(model=model,args=training_args,train_dataset=train_ds,eval_dataset=val_ds,
                    tokenizer=tokenizer,data_collator=collator)
    trainer.train()
    # Select threshold only on Validation.
    val_logits=trainer.predict(val_ds).predictions
    val_prob=torch.softmax(torch.tensor(val_logits),dim=1).numpy()[:,1]
    yv=val.label.astype(int).to_numpy()
    candidates=[metrics(yv,val_prob,t) for t in np.linspace(.05,.95,91)]
    best=max(candidates,key=lambda m:(m["f1"],m["recall"],-m["fpr"]))
    # Test is evaluated exactly once after threshold selection.
    test_ds=SmsDataset(test,tokenizer,args.max_length)
    test_logits=trainer.predict(test_ds).predictions
    test_prob=torch.softmax(torch.tensor(test_logits),dim=1).numpy()[:,1]
    test_metrics=metrics(test.label.astype(int).to_numpy(),test_prob,best["threshold"])
    trainer.save_model(str(OUT)); tokenizer.save_pretrained(str(OUT))
    result={"model":args.model_name,"task":"binary_source_sms_classification","label_mapping":{"0":"LEGITIMATE","1":"SPAM_SCAM"},"not_a_3_class_phishing_classifier":True,"split_counts":{"train":len(train),"validation":len(val),"test":len(test)},"training":{"epochs":args.epochs,"max_length":args.max_length,"batch_size":args.batch_size,"gradient_accumulation_steps":args.grad_accum,"device":"cuda" if torch.cuda.is_available() else "cpu"},"validation_threshold_selection":best,"test_metrics":test_metrics,"test_used_for_fit_or_tuning":False,"created_at_epoch":time.time()}
    REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
