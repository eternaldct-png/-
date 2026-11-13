"""白背景のキャラ画像を切り抜く（外周から白を塗りつぶし → 髪のすき間の白も抜く → ふちの白かぶりを除去）"""
import numpy as np, sys
from PIL import Image
from scipy import ndimage as ndi
def cut(name, hair_bottom):
    im=np.asarray(Image.open(f'assets/{name}.jpg').convert('RGB')).astype(np.float32)
    mn=im.min(2)
    white=mn>=(254 if name=='2' else 249)
    lab,n=ndi.label(white)
    border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
    bg=np.isin(lab,list(border))
    # 髪の中に閉じ込められた白（すき間）
    hair=np.zeros_like(bg); hair[:hair_bottom]=True
    pockets=(mn>=244)&~bg&hair
    # 体の中の大きな白い面は残す: 小さい成分だけ抜く
    l2,n2=ndi.label(pockets); sizes=ndi.sum(pockets,l2,range(1,n2+1))
    small=np.isin(l2,1+np.where(sizes<6000)[0])
    bg|=small
    # 本体につながっていない小さな島（JPEGのノイズ）を消す
    l3,n3=ndi.label(~bg); sz=ndi.sum(~bg,l3,range(1,n3+1)); main=1+int(np.argmax(sz)); bg=(l3!=main)
    alpha=(~bg).astype(np.float32)
    # ふち: 背景から3px以内は「暗さ」でアルファを決める（髪の細い毛）
    dist=ndi.distance_transform_edt(~bg)
    band=(dist>0)&(dist<=3)
    soft=np.clip((250-mn)/70,0,1)
    a_h=np.where(band&hair,np.minimum(alpha,soft*1.15),alpha)
    # 体側は1pxだけ削ってぼかす
    body_er=ndi.binary_erosion(~bg,iterations=1).astype(np.float32)
    a_b=ndi.gaussian_filter(body_er,0.8)
    a=np.where(hair,a_h,a_b); a=np.clip(a,0,1)
    a=np.where(hair,ndi.gaussian_filter(a,0.5),a)
    # 白かぶり除去
    aa=np.clip(a,0.08,1)[...,None]
    fg=np.clip((im-(1-aa)*255)/aa,0,255)
    fg=np.where((a[...,None]<0.98)&hair[...,None],fg,im)
    out=np.dstack([fg,a*255]).astype(np.uint8)
    ys,xs=np.where(a>0.02); box=(xs.min()-4,ys.min()-4,xs.max()+5,ys.max()+5)
    box=(max(0,box[0]),max(0,box[1]),min(im.shape[1],box[2]),min(im.shape[0],box[3]))
    o=Image.fromarray(out,'RGBA').crop(box); o.save(f'assets/char_{name}.png'); print(name,o.size,box)
    for col,tag in (((8,10,30),'dark'),((240,120,30),'org')):
        bgim=Image.new('RGBA',o.size,col+(255,)); bgim.alpha_composite(o); bgim.convert('RGB').resize((o.size[0]//2,o.size[1]//2)).save(f'analysis/chk_{name}_{tag}.jpg',quality=88)
cut('2',760); cut('3',470); cut('4',420)
# ロゴ: 白→透明（乗算用の原本はそのまま使う）。暗い背景用に白文字版も作る
lg=np.asarray(Image.open('assets/5.webp').convert('RGB')).astype(np.float32)
mn=lg.min(2); mx=lg.max(2); a=np.clip((250-mn)/60,0,1)
aa=np.clip(a,0.05,1)[...,None]; fg=np.clip((lg-(1-aa)*255)/aa,0,255)
ys,xs=np.where(a>0.05); box=(xs.min()-8,ys.min()-8,xs.max()+9,ys.max()+9)
Image.fromarray(np.dstack([fg,a*255]).astype(np.uint8),'RGBA').crop(box).save('assets/logo_alpha.png'); print('logo',box)
