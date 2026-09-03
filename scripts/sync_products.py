"""persona/goods_config.yaml → site/data/products.json を再生成する。

商品を追加・変更したら:  python3 scripts/sync_products.py
（site/ は Cloudflare Pages が配信する静的ファイルなので、YAML を直接読めない）
"""
import json, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = yaml.safe_load((ROOT / 'persona' / 'goods_config.yaml').read_text(encoding='utf-8'))
out = []
for p in cfg['products']:
    item = {'id': p['id'], 'name': p['name'], 'description': p.get('description', '')}
    if 'price' in p:
        item['price'] = p['price']
    if 'variants' in p:
        item['variants'] = p['variants']
    imgs = []
    if p.get('image'):
        imgs.append({'path': 'assets/img/' + p['image'].split('/')[-1]})
    for im in p.get('images', []):
        imgs.append({'path': 'assets/img/' + im['path'].split('/')[-1], 'color': im.get('color'), 'design': im.get('design')})
    item['images'] = imgs
    item['model'] = f"assets/models/{p['id']}.glb"
    item['kind'] = 'mug' if 'mug' in p['id'] else 'tshirt'
    out.append(item)
dst = ROOT / 'site' / 'data' / 'products.json'
dst.write_text(json.dumps({'_note': 'persona/goods_config.yaml から生成した写し。商品を変えたら scripts/sync_products.py を実行する',
                           'products': out}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote {dst} ({len(out)} products)')
