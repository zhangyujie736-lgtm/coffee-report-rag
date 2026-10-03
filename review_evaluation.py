"""Recorded source-page review. This file is never imported by runtime QA.
It summarizes observed traces; it does not supply answers to retrieval.
"""
import json,math
from retrieval import ROOT
REVIEWS={
'Q01':('通过','收入 2,256,020,464.09 元、归母净利润 30,796,286.38 元，均引用 PDF p.8 的表格行。','金额及人民币元口径一致；参考页和回答引用一致。'),
'Q02':('通过','收入 11,233,457,712.85 元；金额重算同比 5.33%。','原始表存在空列和多行行名；保留原表，并只连接行名片段，不填补数值。'),
'Q03':('通过','经营现金流量净额 3,812,310.48 元，引用 PDF p.8。','避免把现金流入小计当作净额；金额与参考表一致。'),
'Q04':('通过','原文摘录提供即饮类收入 1,005,071,661.49 元、毛利率 25.03%，引用 p.18、p.30。','首条摘录末尾被长度截断，后续摘录和完整表格补足答案。可读性欠佳，但未错用公司总收入。'),
'Q05':('通过','首条英文原文明确给出全球门店 31,048 家，引用 p.19；p.72 提供另一处验证。','中英术语映射后检索到原文；输出仍为英文摘录，未自动翻译。'),
'Q06':('通过','咖啡豆、咖啡粉、热萃/冷萃咖啡液、冻干/速溶咖啡及固体饮料，均在首条 p.12 摘录。','后续摘录含 C 端产品与子公司表；不能把后者的万元数据与公司元数据直接比较。'),
'Q07':('通过','11/11 家取得公司总营业收入，逐公司金额及同比均与年报摘要会计表复核一致。','需要按公司分别召回，并明确过滤到主要财务指标表；是开发集结果，不能外推到任意复杂问题。'),
'Q08':('通过','四家公司均覆盖：新乳 731,146,914.29 元、光明 -149,213,522 元、伊利 11,565,166,497.81 元、燕塘 57,625,055.83 元。','保留负号，未把净利润与扣非净利润或少数股东损益混淆。'),
'Q09':('通过','明确拒绝从历史财报推断未来股价一定上涨，随后仅展示历史证据。','这是边界题，单列；拒答不代表已回答了预测问题。'),
'Q10':('部分通过','召回 p.113 的收入讨论，给出 RMB49,288.1 million 等相关文字，但没有明确换算成精确的人民币元金额。','无框线多层表头、千元/百万元/美元列并存；BM25 命中标准参考页 p.108，向量和混合未命中该页。混合检索并非总优于单路。')}
def main():
    path=ROOT/'evaluation.json';rows=json.loads(path.read_text(encoding='utf-8'))
    (ROOT/'data'/'evaluation_raw.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in rows:
        r['verdict'],r['actual'],r['error']=REVIEWS[r['id']]
        if r['id']=='Q08':r['expected']='新乳 731,146,914.29 元（p.9）、光明 -149,213,522 元（p.6）、伊利 11,565,166,497.81 元（p.7）、燕塘 57,625,055.83 元（p.7）。'
        for value in r['gold_values']:
            if not any(math.isclose(f['value'],value,rel_tol=0,abs_tol=.01) for f in r['result']['facts']):raise RuntimeError(r['id']+' fact mismatch')
        r['review_method']='逐题将实际回答和引用页与原始 PDF 文字/表格复核；由 agent 复核，未经用户独立盲审。'
        r.pop('result',None)
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'questions':10,'passed':9,'partial':1,'wrong':0,'boundary_questions':1,'factual_passed':8,'factual_total':9,'panoramic_questions':2,'panoramic_passed':2,'development_set':True,'reviewer':'agent','review':'gold references fixed before evaluation; query normalization improved on this same development set; no held-out generalization claim','reference_company_pages':sum(len(r['gold_pages']) for r in rows),'coverage_by_mode':{m:sum(next(t['gold_company_page_coverage'] for t in r['comparison'] if t['mode']==m) for r in rows) for m in ['bm25','vector','hybrid']}}
    (ROOT/'evaluation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
