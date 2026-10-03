"""Conservative coordinate reconstruction of borderless financial tables.
Retains generic value-column labels when headers cannot be matched confidently.
"""
import json,re,statistics
from collections import defaultdict
import pymupdf as fitz
from extract_reports import ROOT,save
NUMBER=re.compile(r'^\(?-?\d[\d,]*(?:\.\d+)?\)?%?$')
def tables(page,pno):
    lines=[]
    for word in sorted(page.get_text('words'),key=lambda w:(round(w[1]/3),w[0])):
        mid=(word[1]+word[3])/2
        if not lines or abs(lines[-1]['y']-mid)>3:lines.append({'y':mid,'words':[]})
        lines[-1]['words'].append(word)
    candidates=[]
    for line in lines:
        nums=[w for w in line['words'] if w[0]>page.rect.width*.33 and NUMBER.fullmatch(w[4])]
        if len(nums)>=2:candidates.append((line,nums))
    groups=[]
    for row in candidates:
        if not groups or row[0]['y']-groups[-1][-1][0]['y']>45:groups.append([])
        groups[-1].append(row)
    result=[]
    for group in groups:
        if len(group)<4:continue
        bins=[]
        for _,ns in group:
            for w in ns:
                slot=next((b for b in bins if abs(statistics.mean(b)-w[2])<8),None)
                if slot is None:bins.append([w[2]])
                else:slot.append(w[2])
        anchors=sorted(statistics.mean(b) for b in bins if len(b)>=3)
        if len(anchors)<2 or len(anchors)>10:continue
        rows=[]
        for line,ns in group:
            values=['']*len(anchors);used=[]
            for w in ns:
                col=min(range(len(anchors)),key=lambda i:abs(w[2]-anchors[i]))
                if abs(w[2]-anchors[col])<10:values[col]=w[4];used.append(w)
            if sum(bool(v) for v in values)<2:continue
            left=min(w[0] for w in used);label=' '.join(w[4] for w in sorted(line['words'],key=lambda w:w[0]) if w[2]<left-3)
            if label:rows.append([label]+values)
        if len(rows)<4:continue
        ymin=group[0][0]['y'];ymax=group[-1][0]['y']
        context='\n'.join(' '.join(w[4] for w in line['words']) for line in lines if ymin-90<=line['y']<ymin)
        result.append({'id':f'LKNCY-p{pno}-b{len(result)+1}','bbox':[0,ymin-10,page.rect.width,ymax+10],'rows':rows,'external_header':['项目']+[f'数值列 {n+1}（核对表头）' for n in range(len(anchors))],'header_context':context,'method':'numeric right-edge coordinate clusters; headers require original-page check'})
    return result
def main():
    source=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))[-1]
    pages=json.loads((ROOT/'data/pages/LKNCY.json').read_text(encoding='utf-8'))
    chunks=json.loads((ROOT/'data/index/chunks.json').read_text(encoding='utf-8'));oldlen=len(chunks)
    doc=fitz.open(ROOT/'data/pdfs/LKNCY-2025.pdf');count=0
    for p,page in zip(pages,doc):
        if p.get('borderless_added'):continue
        extra=tables(page,p['pdf_page']);p['tables']+=extra;p['borderless_added']=True;count+=len(extra)
        for t in extra:
            for n in range(0,len(t['rows']),8):
                selected=t['rows'][n:n+8];header=t['external_header']
                c={k:source[k] for k in ['code','company','year','report','url','source','category','core']};c.update({k:p[k] for k in ['pdf_page','printed_page','section']})
                c.update(id=t['id']+f'-r{n+1}',kind='table',text=t['header_context']+'\n'+' | '.join(header)+'\n'+'\n'.join(' | '.join(r) for r in selected),table_id=t['id'],headers=header,rows=selected,row_start=n+1,row_end=n+len(selected),bbox=t['bbox'],header_context=t['header_context'],extraction_warning='无框线表格的数值按坐标还原；年份/货币列未自动猜测，请核对原文表头。')
                chunks.append(c)
    save(ROOT/'data/pages/LKNCY.json',pages);save(ROOT/'data/index/chunks.json',chunks)
    stats=json.loads((ROOT/'extraction_stats.json').read_text(encoding='utf-8'))
    for s in stats:
        if s['code']=='LKNCY':s.update(tables=sum(len(p['tables']) for p in pages),chunks=sum(c['code']=='LKNCY' for c in chunks),borderless_tables=count)
    save(ROOT/'extraction_stats.json',stats)
    print('Additional borderless tables',count,'chunks',len(chunks)-oldlen,'total',len(chunks),flush=True)
if __name__=='__main__':main()
