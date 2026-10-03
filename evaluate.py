"""Run questions and retain complete recall plus answer traces.
Human source-page review is required before assigning final verdicts.
"""
import json
from retrieval import ROOT,Index
from qa import answer
def main():
    index=Index();questions=json.loads((ROOT/'questions.json').read_text(encoding='utf-8'));rows=[]
    for case in questions:
        result=answer(index,case['question']);trace=[]
        for mode in ['bm25','vector','hybrid']:
            if mode=='hybrid':r=result
            else:r=answer(index,case['question'],mode)
            recovered={h['code']:set() for h in r['hits']}
            for h in r['hits']:recovered[h['code']].add(h['pdf_page'])
            targets=case['gold_pages'];found=sum(bool(set(pages)&recovered.get(code,set())) for code,pages in targets.items())
            trace.append({'mode':mode,'gold_company_page_coverage':found,'gold_company_count':len(targets),'recall':[{k:h[k] for k in ['id','company','pdf_page','kind','bm25_rank','vector_rank','rrf','cosine']} for h in r['hits']]})
        row={**case,'verdict':'待原页复核','actual':'\n'.join(b['text'] for b in result['answer']),'error':'尚未判分','recalled':[{k:h[k] for k in ['id','company','code','pdf_page','section','kind','bm25_rank','vector_rank','rrf','cosine']} for h in result['hits']],'result':result,'comparison':trace}
        rows.append(row);print(case['id'],result['status'],len(result['facts']),flush=True)
    (ROOT/'evaluation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Raw evaluation traces written; verdicts await source-page review.',flush=True)
if __name__=='__main__':main()
