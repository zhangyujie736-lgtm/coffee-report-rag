"""Download full official annual reports, never news summaries."""
import json, hashlib, re, time, urllib.parse, urllib.request, argparse, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parent
COMPANIES=[('605300','佳禾食品','咖啡及植物基原料'),('300915','海融科技','奶油及茶饮原料'),('605339','南侨食品','烘焙油脂及配餐'),('600298','安琪酵母','烘焙及食品原料'),('002946','新乳业','乳品'),('600597','光明乳业','乳品'),('600887','伊利股份','乳品'),('002732','燕塘乳业','乳品'),('301296','新巨丰','饮料包装'),('002846','英联股份','金属包装'),('603711','香飘飘','茶饮及冲泡饮品')]
HEADERS={'User-Agent':'Mozilla/5.0','Referer':'https://www.cninfo.com.cn/'}
def get(url,data=None):
    for n in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data,HEADERS),timeout=90) as r:return r.read()
        except Exception:
            if n==2:raise
            time.sleep(2+n)
def one(c,year=2025):
    code,name,category=c
    params={'pageNum':1,'pageSize':30,'column':'szse','tabName':'fulltext','searchkey':name,'secid':'','stock':'','category':'category_ndbg_szsh;','trade':'','seDate':f'{year+1}-01-01~{year+1}-10-03','sortName':'','sortType':'','isHLtitle':'true'}
    result=json.loads(get('https://www.cninfo.com.cn/new/hisAnnouncement/query',urllib.parse.urlencode(params).encode()))
    candidates=[a for a in result.get('announcements',[]) if a['secCode']==code and re.search(fr'{year}年年度报告(全文)?$',re.sub('<.*?>','',a['announcementTitle']))]
    if not candidates:raise RuntimeError(f'{name}: no full annual report found')
    a=candidates[0];url='https://static.cninfo.com.cn/'+a['adjunctUrl']
    filename=f'{code}-{year}.pdf';target=ROOT/'data'/'pdfs'/filename
    if not target.exists():target.write_bytes(get(url))
    raw=target.read_bytes()
    if not raw.startswith(b'%PDF'):raise RuntimeError(f'{name}: response is not PDF')
    return {'code':code,'company':name,'category':category,'year':year,'report':f'{year}年年度报告','source':'巨潮资讯','url':url,'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'core':True}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-manifest',action='store_true');parser.add_argument('--luckin-pdf',type=Path);args=parser.parse_args()
    (ROOT/'data'/'pdfs').mkdir(parents=True,exist_ok=True)
    if args.luckin_pdf:shutil.copyfile(args.luckin_pdf,ROOT/'data'/'pdfs'/'LKNCY-2025.pdf')
    if args.from_manifest:
        rows=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
        for row in rows:
            p=ROOT/'data'/'pdfs'/row['file']
            if not p.exists():p.write_bytes(get(row['url']))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError(row['company']+': source hash mismatch; investigate revised report before indexing')
            print(row['company'],'SHA-256 verified',flush=True)
        return
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(one,c):c for c in COMPANIES}
        for job in as_completed(jobs):
            row=job.result();rows.append(row);print(row['company'],row['url'],flush=True)
    rows.sort(key=lambda x:x['code'])
    (ROOT/'sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    url='https://investor.lkcoffee.com/static-files/b3e2a29b-7e43-4a34-b5e0-cfe24553efb5'
    target=ROOT/'data'/'pdfs'/'LKNCY-2025.pdf'
    if not target.exists():target.write_bytes(get(url))
    raw=target.read_bytes()
    if not raw.startswith(b'%PDF'):raise RuntimeError('Luckin report is not PDF')
    rows.append({'code':'LKNCY','company':'瑞幸咖啡','category':'现制咖啡','year':2025,'report':'2025 Annual Report (20-F)','source':'瑞幸官方投资者关系（补充材料）','url':url,'file':target.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'core':False})
    rows.sort(key=lambda x:x['code'])
    (ROOT/'sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Downloaded',len(rows),'full reports',flush=True)
if __name__=='__main__':main()
