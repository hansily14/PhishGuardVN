"""Offline infrastructure adapter. Import measured RDAP/DNS/TLS; no live URL fetching."""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
from .features import domain_group, infrastructure_features

def timestamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('observed_at phải có múi giờ.')
    return dt.astimezone(timezone.utc)

def snapshot_from_rdap(url,rdap,dns,tls,observed_at):
    """rdap is a saved RDAP object; dns list IP answers or None; tls boolean or None.
    Caller must supply measurements captured at observed_at. None is unknown, [] is NXDOMAIN/no answer.
    """
    now=timestamp(observed_at);record={'observed_at':now.isoformat(),'dns_resolves':None if dns is None else int(bool(dns)),'dns_answer_count':None if dns is None else len(dns),'tls_valid':None if tls is None else int(tls),'domain_age_days':None,'registration_remaining_days':None}
    for event in (rdap or {}).get('events',[]):
        action=event.get('eventAction');value=timestamp(event['eventDate'])
        if action=='registration' and value<=now:record['domain_age_days']=(now-value).total_seconds()/86400
        if action=='expiration':record['registration_remaining_days']=(value-now).total_seconds()/86400
    return {domain_group(url):record}

def load_snapshots(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    for host,record in data.items():
        timestamp(record['observed_at'])
        for name,value in record.items():
            if name!='observed_at' and value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value)):raise ValueError('Giá trị hạ tầng phải là số hữu hạn hoặc null.')
    return data
