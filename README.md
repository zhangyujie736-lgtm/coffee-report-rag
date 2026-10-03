# 咖啡产业链财报问答库 - 第三周作业 A

以瑞幸咖啡为主题，收集 **11 家 A 股相关行业公司的巨潮年报全文**，另加入瑞幸官方 20-F 年报作为境外补充。公司范围是咖啡、茶饮、乳品、食品原料和包装的研究样本，**不等于这些公司均已被证实向瑞幸供货**。

统一报告年度：2025。12 家公司、2,606 个 PDF 物理页、16,300 个检索块。所有财报来自官方全文，不是新闻、业绩快报或摘要。完整 URL、文件大小和 SHA-256 在 `sources.json`。

## 交付与真实结果

- `index.html`、`style.css`、`app.js` 与 `server.py`：本地问答页面，输入任意问题，显示答案、公司、报告、章节、页码、块编号与原始 PDF 链接；可切换 BM25、向量与混合检索。
- `download_reports.py`、`download_model.py`、`extract_reports.py`、`extract_borderless.py`、`build_index.py`：下载、全文/表格处理及建库脚本。
- `questions.json`、`evaluate.py`、`evaluation.json`：10 道题（含两道跨公司全景题）的问题、参考页、完整召回编号与排名、实际结果和逐题判定。
- `evaluation_summary.json`、`review_evaluation.py`：由 agent 对原始 PDF 逐题核对后记录的判定过程，**未经过用户独立盲审**。评价脚本与判分记录不参与运行时问答，也不向问答提供标准答案。
- [一页结论](conclusion.pdf)、[问答截图](qa-screenshot.jpg)、[全景比较截图](panorama-screenshot.jpg)、[10 题记录截图](evaluation-screenshot.jpg) 均已随仓库交付。

本开发集：9 题通过、1 题部分通过；其中 1 题是边界拒答题，因此事实题为 8/9 通过，两道全景题为 2/2 通过。Q10 取得了相关收入文字，但未完整给出精确的人民币元金额。BM25 的参考公司-页覆盖为 22/22，向量及混合为 21/22，不能声称混合总是更优。

查询口径识别和中英术语映射是在同一批题上调试的；这是**开发集结果，不是独立测试集准确率**。首轮的全景召回失败与改进说明保存在 `baseline_comparison.json`。

## 复现

Python 3.12；建议创建虚拟环境。无付费 API、无 API key。

```bash
python -m pip install -r requirements.txt
python download_reports.py --from-manifest
python download_model.py
python extract_reports.py
python extract_borderless.py
python build_index.py
python evaluate.py
python server.py
```

打开 **http://127.0.0.1:4175/**。页面需要本地 Python 后端提供真实查询向量，不能只双击 HTML 或作为纯静态页面部署。

瑞幸官网连接可能较慢。本次由其官方年度报告页面下载成功；若脚本在该源超时，可从 https://investor.lkcoffee.com/financial-information/annual-reports 下载 2025 Annual Report，随后执行：

```bash
python download_reports.py --from-manifest --luckin-pdf "/path/to/Luckin Coffee Inc. 2025 Annual Report.pdf"
```

脚本会核对 SHA-256。内容修订或哈希不同应先核验，不能悄悄替换材料后沿用旧结论。`evaluate.py` 重新运行后结果为“待原页复核”；`review_evaluation.py` 记录的是本次已核验版本，不可无核对地用于将来的材料。

## 提取、表格与切块

全文按 PDF 页提取，正文按 650 字符切分、重叠 80 字符；公司、年度、章节、物理页及可靠识别出的印刷页随块保存。章节主要来自一级目录或节标题，不承诺每个小标题均识别正确。

有框线表格用 PyMuPDF 的表格单元格矩阵提取，按每 8 行分块、保留表头、空值、行范围与原始坐标。中文行名可能被拆开，答案解析仅连接行名碎片，不填补数值。跨页表头不会凭空补齐。

瑞幸无框线财表使用数值右边界的坐标聚类恢复行列，取得 51 个补充表格；无法可靠匹配的年份/币种使用“数值列（核对表头）”，保留原页链接。**这类表格的语义还原仍不完整**，是 Q10 的主要限制。金额和同比核对以原文为准，不声称全部表格已无误恢复。

## 向量、BM25 与问答

- 向量模型：`Xenova/multilingual-e5-small` 的 int8 ONNX，模型修订号 `761b726dd34fb83930e26aab4e9ac3899aa1fa78`，384 维。`query:`/`passage:` 前缀、掩码平均池化、L2 归一化，最多 384 token。长度超过上限的片段向量会截断；BM25 与页面仍保留全文。
- BM25：jieba 分词，k1=1.5、b=0.75；两路各 Top-40，通过 RRF（k=60）融合。
- 公司识别与查询口径：公司名过滤；全景题按公司分别取 Top-5；一般题 Top-8。公司总收入/归母净利润/经营现金流查询优先检索前 15 页中含年度列的财务表；产品/毛利率/季度题不做该过滤。此规则是可见、可复现的启发式，不能保证其他年报布局适用。
- 使用通用中英财报术语映射，改善中文检索瑞幸英文年报；不按题号检索，也不把标准答案存入问答逻辑。
- **问答是摘录与表格计算，不调用生成式大模型。** 财务主表能解析时展示具体数值；否则显示原文与引用，明确提示核对。同比按 `(本年-上年)/abs(上年)` 计算；上年为零时不计算。未来股价等无证据问题保留拒答。

## 仓库边界

财报 PDF、模型权重、全文索引和原始评估大段文本留在本机，通过脚本复建。`.env`、凭据、个人资料和本机路径均不上传。`sources.json` 与评估记录只包含公开财报来源、数据及实验记录。此作业研究事实检索的适用性，没有实施 LoRA，也没有据此得出微调效果更差的实验结论。
