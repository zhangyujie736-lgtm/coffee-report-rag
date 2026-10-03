import json,mimetypes,urllib.parse
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from retrieval import ROOT,Index
from qa import answer
INDEX=None
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,value,status=200):
        raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/info':
            return self.reply({'sources':INDEX.sources,'index':json.loads((ROOT/'index_stats.json').read_text(encoding='utf-8')),'extraction':json.loads((ROOT/'extraction_stats.json').read_text(encoding='utf-8'))})
        if path=='/api/evaluation':
            p=ROOT/'evaluation.json';return self.reply(json.loads(p.read_text(encoding='utf-8')) if p.exists() else [])
        if path.startswith('/pdf/'):
            filename=path.split('/')[-1]
            if filename not in {s['file'] for s in INDEX.sources}:return self.reply({'error':'not found'},404)
            file=ROOT/'data'/'pdfs'/filename
        elif path in ['/','/index.html','/app.js','/style.css']:file=ROOT/('index.html' if path=='/' else path[1:])
        else:return self.reply({'error':'not found'},404)
        raw=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream');self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path!='/api/ask':return self.reply({'error':'not found'},404)
        origin=urllib.parse.urlparse(self.headers.get('Origin',''))
        if origin.hostname not in ('127.0.0.1','localhost') or origin.port!=4175:return self.reply({'error':'请从本机页面发起请求'},403)
        length=int(self.headers.get('Content-Length',0))
        if length>4096:return self.reply({'error':'问题过长'},400)
        try:
            data=json.loads(self.rfile.read(length));mode=data.get('mode','hybrid')
            if mode not in ['hybrid','vector','bm25']:raise ValueError('检索方式无效')
            self.reply(answer(INDEX,data.get('question',''),mode))
        except Exception as e:self.reply({'error':str(e)},400)
if __name__=='__main__':
    print('Loading local vector model and index...',flush=True);INDEX=Index()
    print('Ready: http://127.0.0.1:4175/',flush=True);ThreadingHTTPServer(('127.0.0.1',4175),Handler).serve_forever()
