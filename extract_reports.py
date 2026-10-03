"""Preserve PDF pages and table cell matrices before chunking."""
import json,re,hashlib,time
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parent
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
def slices(text,size=650,overlap=80):
    start=0
    while start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            cut=text.rfind('\n',start+size//2,end)
            if cut>start:end=cut
        yield text[start:end]
        if end==len(text):break
        start=max(start+1,end-overlap)
def main():
    target=ROOT/'data'/'pages';target.mkdir(parents=True,exist_ok=True)
    sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'));chunks=[];stats=[]
    for s in sources:
        out=target/(s['code']+'.json')
        if out.exists():pages=json.loads(out.read_text(encoding='utf-8'))
        else:
            doc=fitz.open(ROOT/'data'/'pdfs'/s['file']);pages=[];section='封面与前言'
            toc=doc.get_toc();section_by_page={item[2]:item[1] for item in toc if item[0]==1}
            for pno,page in enumerate(doc,1):
                text=page.get_text('text',sort=True)
                if pno in section_by_page:section=section_by_page[pno]
                headings=re.findall(r'(?m)^\s*(第[一二三四五六七八九十]+节\s+[^\n.。]{2,35}|Item\s+\d+[A-Z]?\.\s+[^\n]{4,70})\s*$',text)
                if headings and '目录' not in text[:600]:section=re.sub(r'\s+',' ',headings[-1]).strip()
                tables=[]
                try:
                    found=page.find_tables()
                    for tno,t in enumerate(found.tables,1):
                        cells=t.extract()
                        if len(cells)>=2 and max(map(len,cells),default=0)>=2:
                            tables.append({'id':f'{s["code"]}-p{pno}-t{tno}','bbox':list(t.bbox),'rows':[[re.sub(r'\s+',' ',v).strip() if v else '' for v in row] for row in cells],'external_header':t.header.names if t.header.external else []})
                except Exception as e:tables=[{'error':type(e).__name__}]
                footer=page.get_text('blocks',clip=fitz.Rect(0,page.rect.height-60,page.rect.width,page.rect.height))
                printed=[re.sub(r'\s+',' ',b[4]).strip() for b in footer if re.fullmatch(r'\s*(?:\d+\s*/\s*\d+|\d+|F-\d+)\s*',b[4])]
                pages.append({'pdf_page':pno,'printed_page':printed[-1] if printed else None,'section':section,'text':text,'tables':tables})
                if pno%50==0:print(s['company'],pno,'pages extracted',flush=True)
            save(out,pages)
        for page in pages:
            base={k:s[k] for k in ['code','company','year','report','url','source','category','core']}
            base.update({k:page[k] for k in ['pdf_page','printed_page','section']})
            for n,text in enumerate(slices(page['text'])):
                if len(text.strip())<35:continue
                chunks.append(dict(base,id=f'{s["code"]}-p{page["pdf_page"]}-x{n+1}',kind='text',text=text))
            for table in page['tables']:
                if 'rows' not in table:continue
                rows=table['rows'];header=table['external_header'] or rows[0]
                # Original blanks are retained: no guessed merged-cell values.
                for n in range(0,len(rows),8):
                    selected=rows[n:n+8]
                    text='表头：'+' | '.join(header)+'\n'+'\n'.join(' | '.join(row) for row in selected)
                    chunks.append(dict(base,id=table['id']+f'-r{n+1}',kind='table',text=text,table_id=table['id'],headers=header,rows=selected,row_start=n+1,row_end=n+len(selected),bbox=table['bbox']))
        stats.append({'company':s['company'],'code':s['code'],'pages':len(pages),'tables':sum(len([t for t in p['tables'] if 'rows' in t]) for p in pages),'chunks':sum(c['code']==s['code'] for c in chunks),'empty_pages':[p['pdf_page'] for p in pages if len(p['text'].strip())<20]})
        print(s['company'],stats[-1],flush=True)
    index=ROOT/'data'/'index';index.mkdir(parents=True,exist_ok=True)
    save(index/'chunks.json',chunks);save(ROOT/'extraction_stats.json',stats)
    print('TOTAL CHUNKS',len(chunks),flush=True)
if __name__=='__main__':main()
