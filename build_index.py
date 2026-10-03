import json,time,hashlib
from pathlib import Path
import numpy as np
from retrieval import ROOT,Encoder,build_bm25
def main():
    target=ROOT/'data'/'index';chunks=json.loads((target/'chunks.json').read_text(encoding='utf-8'))
    (target/'bm25.json').write_text(json.dumps(build_bm25(chunks),ensure_ascii=False),encoding='utf-8')
    encoder=Encoder();vectors=[];start=time.time();batch=12
    for n in range(0,len(chunks),batch):
        checkpoint=target/f'batch-{n:06d}.npy'
        texts=[c['company']+' '+c['report']+' '+c['section']+' '+c['text'] for c in chunks[n:n+batch]]
        fingerprint=hashlib.sha256(json.dumps(texts,ensure_ascii=False).encode()).hexdigest()
        stamp=checkpoint.with_suffix('.sha256')
        v=np.load(checkpoint) if checkpoint.exists() and (not stamp.exists() or stamp.read_text()==fingerprint) else None
        if v is None or v.shape!=(len(texts),384):
            v=encoder.encode(texts,'passage');np.save(checkpoint,v)
        stamp.write_text(fingerprint)
        vectors.append(v)
        if n%120==0:print(f'Embedded {n+len(v)}/{len(chunks)} elapsed {time.time()-start:.0f}s',flush=True)
    array=np.vstack(vectors);np.save(target/'vectors.npy',array)
    (ROOT/'index_stats.json').write_text(json.dumps({'chunks':len(chunks),'vector_dimensions':array.shape[1],'embedding_model':'Xenova/multilingual-e5-small','prefixes':['query:','passage:'],'pooling':'masked mean + L2','onnx':'int8 quantized','max_tokens':384,'rrf_k':60,'bm25_k1':1.5,'bm25_b':.75,'seconds':round(time.time()-start,1)},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
