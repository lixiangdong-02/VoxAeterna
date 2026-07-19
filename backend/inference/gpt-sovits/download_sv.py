import os
import requests

url = 'https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/sv/pretrained_eres2netv2w24s4ep4.ckpt'
save_dir = 'GPT_SoVITS/pretrained_models/sv'
os.makedirs(save_dir, exist_ok=True)
save_path = os.path.join(save_dir, 'pretrained_eres2netv2w24s4ep4.ckpt')

print(f'Downloading from {url}...')
r = requests.get(url, stream=True, timeout=60)
r.raise_for_status()
total = int(r.headers.get('content-length', 0))
downloaded = 0
with open(save_path, 'wb') as f:
    for chunk in r.iter_content(8192):
        f.write(chunk)
        downloaded += len(chunk)
        if total:
            pct = downloaded / total * 100
            print(f'\r  {downloaded}/{total} ({pct:.0f}%)', end='')
print('\nOK:', save_path)
