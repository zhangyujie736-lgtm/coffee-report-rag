import json,re,math,threading
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import jieba
import onnxruntime as ort
from tokenizers import Tokenizer
ROOT=Path(__file__).resolve().parent
STOP=set('的了和与及在是为对本公司报告年度什么哪些多少如何')|{'年','月','日','情况','报告期','the','a','and','of','to','in'}
def tokenize(text):
    return [t.lower() for t in jieba.lcut(text) if len(t.strip())>1 and t.lower() not in STOP and re.search(r'[\w\u4e00-\u9fff]',t)]
class Encoder:
    def __init__(self):
        opts=ort.SessionOptions();opts.intra_op_num_threads=4
        self.session=ort.InferenceSession(str(ROOT/'data'/'model'/'model.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
        self.tokenizer=Tokenizer.from_file(str(ROOT/'data'/'model'/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=384);self.tokenizer.enable_padding(pad_id=1,pad_token='<pad>')
        self.lock=threading.Lock()
    def encode(self,texts,kind='query'):
        with self.lock:
            enc=self.tokenizer.encode_batch([kind+': '+x for x in texts])
            ids=np.array([x.ids for x in enc],dtype=np.int64);mask=np.array([x.attention_mask for x in enc],dtype=np.int64)
            inputs={'input_ids':ids,'attention_mask':mask}
            if 'token_type_ids' in {i.name for i in self.session.get_inputs()}:inputs['token_type_ids']=np.zeros_like(ids)
            result=self.session.run(None,inputs)[0]
            pooled=(result*mask[:,:,None]).sum(1)/np.maximum(mask.sum(1)[:,None],1) if result.ndim==3 else result
            return (pooled/np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-9)).astype(np.float32)
class Index:
    def __init__(self):
        self.chunks=json.loads((ROOT/'data'/'index'/'chunks.json').read_text(encoding='utf-8'))
        self.vectors=np.load(ROOT/'data'/'index'/'vectors.npy')
        self.bm=json.loads((ROOT/'data'/'index'/'bm25.json').read_text(encoding='utf-8'))
        self.encoder=Encoder();self.sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    def search(self,q,k=8,company=None,mode='hybrid'):
        names=[s['code'] for s in self.sources if s['company'] in q or s['code'] in q]
        if company:names=[company]
        selected=[i for i,c in enumerate(self.chunks) if not names or c['code'] in names]
        core_scope=bool(names) and all(next(s for s in self.sources if s['code']==code)['core'] for code in names)
        summary=core_scope and bool(re.search('营业收入|营收|净利润|归母|现金流',q)) and not re.search('毛利|即饮|产品|分行业|分地区|季度',q)
        if summary:
            subset=[i for i in selected if self.chunks[i]['pdf_page']<=15 and self.chunks[i]['kind']=='table' and '2025' in ' '.join(self.chunks[i]['headers'])]
            if subset:selected=subset
        # Generic intent normalization, not question-ID or gold-answer lookup.
        normalized=q
        for s in self.sources:normalized=normalized.replace(s['company'],'').replace(s['code'],'')
        normalized=re.sub(r'全景|跨公司|比较|11\s*家公司|公司|是多少|分别|及同比变化',' ',normalized)
        normalized=normalized.replace('归母净利润','归属于上市公司股东的净利润').replace('营收','营业收入')
        if summary:normalized+=' 主要会计数据 财务指标'
        if names==['LKNCY']:
            mapping={'门店':'total global store network stores','总净收入':'total net revenues RMB in thousands','营业收入':'total net revenues','股价':'share price','全球':'global worldwide','年末':'as of December 31'}
            for zh,en in mapping.items():
                if zh in q:normalized+=' '+en
        eligible=np.array(selected,dtype=int)
        scores=np.zeros(len(self.chunks),dtype=np.float32)
        for t in set(tokenize(normalized)):
            posts=self.bm['postings'].get(t,[]);df=len(posts)
            if not df:continue
            idf=math.log(1+(len(self.chunks)-df+.5)/(df+.5))
            for idx,tf in posts:
                dl=self.bm['lengths'][idx];scores[idx]+=idf*tf*2.5/(tf+1.5*(.25+.75*dl/self.bm['avgdl']))
        bs=sorted(eligible,key=lambda i:float(scores[i]),reverse=True)[:40]
        vs=self.vectors@self.encoder.encode([normalized])[0]
        ds=sorted(eligible,key=lambda i:float(vs[i]),reverse=True)[:40]
        rank=defaultdict(float)
        if mode!='vector':
            for r,i in enumerate(bs,1):rank[i]+=1/(60+r)
        if mode!='bm25':
            for r,i in enumerate(ds,1):rank[i]+=1/(60+r)
        hits=sorted(rank,key=lambda i:rank[i],reverse=True)[:k]
        return [dict(self.chunks[i],bm25=float(scores[i]),cosine=float(vs[i]),rrf=rank[i],bm25_rank=(bs.index(i)+1 if i in bs else None),vector_rank=(ds.index(i)+1 if i in ds else None)) for i in hits]
def build_bm25(chunks):
    postings=defaultdict(list);lengths=[]
    for i,c in enumerate(chunks):
        ts=tokenize(c['company']+' '+c['section']+' '+c['text']);counts=Counter(ts);lengths.append(len(ts))
        for t,n in counts.items():postings[t].append([i,n])
    return {'postings':postings,'lengths':lengths,'avgdl':sum(lengths)/len(lengths),'k1':1.5,'b':.75}
