"""Evidence-first extractive QA. No hidden model-generated facts."""
import re,time
from collections import OrderedDict
METRICS={'营业收入':['营业收入'],'归母净利润':['归属于上市公司股东的净利润','归属于母公司股东的净利润'],'经营现金流':['经营活动产生的现金流量净额']}
def compact(s):return re.sub(r'\s+','',s)
def facts(hits,q):
    year=int(re.search(r'202[345]',q).group()) if re.search(r'202[345]',q) else 2025
    wanted=[k for k in METRICS if (k=='营业收入' and re.search('收入|营收',q)) or (k=='归母净利润' and re.search('归母|净利润|盈利|亏损',q)) or (k=='经营现金流' and '现金' in q)]
    records=OrderedDict()
    for h in hits:
        if h['kind']!='table':continue
        header=[compact(v) for v in h['headers']]
        current=next((n for n,v in enumerate(header) if re.fullmatch(fr'{year}年?',v)),None)
        if current is None:continue
        previous=next((n for n,v in enumerate(header) if re.fullmatch(fr'{year-1}年?',v)),None)
        for rowno,row in enumerate(h['rows']):
            label=compact(''.join(row[:current])) if row else ''
            # Join line fragments in the label columns only. Never fill numeric blanks.
            for tail in h['rows'][rowno+1:rowno+3]:
                if current>=len(tail) or tail[current].strip():break
                fragment=compact(''.join(tail[:current]))
                if fragment:label+=fragment
            for name in wanted:
                if not any(label.startswith(m) and '扣除' not in label for m in METRICS[name]):continue
                if current>=len(row):continue
                value=row[current];old=row[previous] if previous is not None and previous<len(row) else ''
                try:
                    a=float(value.replace(',',''));b=float(old.replace(',','')) if old else None
                except ValueError:continue
                # Only mainland summary tables: their accounting data is RMB yuan.
                if not h['core']:continue
                if not ('元' in label or '主要会计' in h['section'] or h['pdf_page']<=15):continue
                key=(h['code'],name)
                if key not in records:records[key]={'company':h['company'],'metric':name,'year':year,'value':a,'previous':b,'change_percent':(a-b)/abs(b)*100 if b else None,'unit':'人民币元','citation':h['id'],'reconstructed_label':label}
    return list(records.values())
def answer(index,q,mode='hybrid'):
    start=time.time();q=q.strip()[:500]
    if not q:raise ValueError('请输入问题')
    scope=[s for s in index.sources if s['company'] in q or s['code'] in q]
    overview=bool(re.search(r'全景|11\s*家|所有公司|全部公司|跨公司',q))
    if overview and not scope:scope=[s for s in index.sources if s['core']]
    if overview or len(scope)>1:
        hits=[]
        for s in scope:
            hits+=index.search(q,k=5,company=s['code'],mode=mode)
        strategy='按公司分别召回，保证全景问题的覆盖'
    else:
        hits=index.search(q,k=8,mode=mode);strategy='公司过滤 + 混合 Top-8' if scope else '全库混合 Top-8'
    items=facts(hits,q);blocks=[]
    if re.search('明年|202[6-9]|股价|必然|一定|预测|导致.*多少',q):
        blocks.append({'text':'本库只覆盖 2025 年历史财报，不能据此验证未来股价、预测金额或必然的因果关系。以下是检索到的历史证据，不能当作该问题的确定答案。','citations':[]})
        status='证据不足，保留拒答'
    elif items:
        for f in items:
            change=f'；按两年金额计算同比 {f["change_percent"]:.2f}%' if f['change_percent'] is not None else ''
            blocks.append({'text':f'{f["company"]}：{f["year"]} 年{f["metric"]} {f["value"]:,.2f} 人民币元（{f["value"]/1e8:.4f} 亿元）{change}。','citations':[f['citation']]})
        requested=len(scope) if scope else 1
        status='表格事实已提取' if len({f['company'] for f in items})>=requested else '部分公司未取得可解析表格，需核对'
        if overview:blocks.append({'text':f'本次取得 {len({f["company"] for f in items})}/{len(scope)} 家公司的相应指标。未取得的公司不能解释为零或没有该业务。','citations':[]})
    else:status='原文摘录，需核对问题是否被完整回答'
    if not items or status.startswith('证据不足'):
        for h in hits[:3]:blocks.append({'text':h['text'][:450],'citations':[h['id']],'extract':True})
    return {'question':q,'mode':mode,'strategy':strategy,'status':status,'answer':blocks,'facts':items,'hits':hits,'elapsed_seconds':round(time.time()-start,3),'warning':'摘录式问答；只使用财报证据，不调用生成式大模型。页码为 PDF 物理页。'}
