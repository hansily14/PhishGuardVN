"""Shared offline URL extractor: same feature code in training and serving. No URL fetches."""
import re
import math
import ipaddress
import unicodedata
from collections import Counter
from urllib.parse import urlsplit, urlunsplit
import numpy as np
import pandas as pd
import tldextract

PSL = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)
URL_PATTERN = re.compile(r"(?i)(?:https?://|hxxps?://|www\.)[^\s<>\"\[\]]+|(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,24})(?::\d{1,5})?(?:/[^\s<>\"]*)?")
LEXICAL = ['URLLength','DomainLength','IsDomainIP','TLDLength','NoOfSubDomain','NoOfLettersInURL','LetterRatioInURL','NoOfDegitsInURL','DegitRatioInURL','NoOfEqualsInURL','NoOfQMarkInURL','NoOfAmpersandInURL','NoOfOtherSpecialCharsInURL','SpacialCharRatioInURL','IsHTTPS','NoOfObfuscatedChar','ObfuscationRatio','HasObfuscation','path_length','query_length','host_entropy','url_entropy','dots','hyphens','at_signs','slashes','has_punycode','has_non_ascii','has_explicit_port','credential_words','financial_words']
INFRASTRUCTURE = ['dns_resolves','dns_answer_count','domain_age_days','registration_remaining_days','tls_valid']

def normalize_url(raw):
    raw = unicodedata.normalize('NFC', str(raw)).strip().replace('[.]','.').replace('(.)','.')
    raw = re.sub(r'^hxxp', 'http', raw, flags=re.I)
    if len(raw) > 4096 or any(ord(c)<32 for c in raw):
        raise ValueError('URL không hợp lệ hoặc dài quá 4096 ký tự.')
    if not re.match(r'^[a-z][a-z0-9+.-]*://',raw,re.I): raw='https://'+raw
    p=urlsplit(raw)
    if p.scheme.lower() not in ('http','https') or not p.hostname:
        raise ValueError('Chỉ hỗ trợ URL HTTP/HTTPS.')
    host=p.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    try: ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or not re.fullmatch(r'[a-z0-9.-]+',host): raise ValueError('Tên miền không hợp lệ.')
    port=p.port  # validates port
    host_fmt=f'[{host}]' if ':' in host else host
    netloc=host_fmt+(f':{port}' if port and not ((port==443 and p.scheme=='https') or (port==80 and p.scheme=='http')) else '')
    # Preserve userinfo and case-sensitive path/query; fragment omitted for canonical lookup.
    if p.username is not None: netloc=p.netloc.rsplit('@',1)[0]+'@'+netloc
    return urlunsplit((p.scheme.lower(),netloc,p.path or '/',p.query,''))

def domain_group(url):
    host=urlsplit(normalize_url(url)).hostname
    try: ipaddress.ip_address(host); return host
    except ValueError: return PSL(host).top_domain_under_public_suffix or host

def extract_urls(text, maximum=20):
    restored=re.sub(r'\[\.\]|\(\.\)', '.', text)
    found=[]
    for m in URL_PATTERN.finditer(restored):
        raw=m.group().rstrip('.,;:!?)}\u201d\u2019')
        try: normalized=normalize_url(raw)
        except (ValueError,UnicodeError): continue
        if normalized not in found: found.append(normalized)
        if len(found)>maximum: raise ValueError(f'Tối đa {maximum} URL mỗi lần kiểm tra.')
    return found

def entropy(s):
    return -sum((v/len(s))*math.log2(v/len(s)) for v in Counter(s).values()) if s else 0.

def lexical_features(raw):
    u=normalize_url(raw); p=urlsplit(u); host=p.hostname; ext=PSL(host); n=len(u)
    try: ipaddress.ip_address(host); is_ip=1
    except ValueError: is_ip=0
    letters=sum(c.isalpha() for c in u); digits=sum(c.isdigit() for c in u)
    special=sum(not c.isalnum() for c in u); obf=len(re.findall(r'%[0-9a-fA-F]{2}',u))
    values=[n,len(host),is_ip,len(ext.suffix),len(ext.subdomain.split('.')) if ext.subdomain else 0,letters,letters/n,digits,digits/n,u.count('='),u.count('?'),u.count('&'),special,special/n,int(p.scheme=='https'),obf,obf*3/n,int(obf>0),len(p.path),len(p.query),entropy(host),entropy(u),u.count('.'),u.count('-'),u.count('@'),u.count('/'),int('xn--' in host),int(any(ord(c)>127 for c in u)),int(p.port is not None),len(re.findall(r'login|verify|account|secure|password|signin|update',u,re.I)),len(re.findall(r'bank|wallet|payment|refund|bonus|prize',u,re.I))]
    return dict(zip(LEXICAL,values))

def feature_frame(urls):
    return pd.DataFrame([lexical_features(u) for u in urls],columns=LEXICAL).astype(float)

def infrastructure_features(url, snapshots=None, as_of=None):
    """Read measured metadata only. Missing is NaN, never inferred from HTTPS.
    snapshots: map domain -> {observed_at: ISO timestamp, dns_resolves: ..., ...}.
    as_of excludes future measurements for point-in-time evaluation.
    Not used by packaged lexical model: original corpus has no comparable snapshots.
    """
    record=(snapshots or {}).get(domain_group(url),{})
    observed=record.get('observed_at')
    valid=bool(observed) and (as_of is None or pd.Timestamp(observed)<=pd.Timestamp(as_of))
    result={k:float(record[k]) if valid and record.get(k) is not None else np.nan for k in INFRASTRUCTURE}
    result.update({k+'_missing':int(pd.isna(v)) for k,v in list(result.items())})
    return result
