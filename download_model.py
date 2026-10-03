"""Public ONNX model; no account, token or API key required."""
import urllib.request, shutil, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO='Xenova/multilingual-e5-small'
def main():
    target=ROOT/'data'/'model';target.mkdir(parents=True,exist_ok=True)
    api=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}',timeout=30))
    revision=api['sha']
    for remote,local in [('tokenizer.json','tokenizer.json'),('onnx/model_quantized.onnx','model.onnx')]:
        path=target/local
        if path.exists():continue
        print('Downloading',remote,'revision',revision,flush=True)
        with urllib.request.urlopen(f'https://huggingface.co/{REPO}/resolve/{revision}/{remote}',timeout=180) as r,path.with_suffix('.partial').open('wb') as f:shutil.copyfileobj(r,f)
        path.with_suffix('.partial').replace(path)
    (target/'revision.json').write_text(json.dumps({'repo':REPO,'revision':revision}),encoding='utf-8')
    print('Model ready',flush=True)
if __name__=='__main__':main()
