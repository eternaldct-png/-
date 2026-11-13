"""out/stills の静止画を1枚のコンタクトシートにまとめる: python3 sheet.py 出力名 [列数]"""
import sys, glob
from PIL import Image, ImageDraw
fs=sorted(glob.glob('out/stills/t_*.jpg')); cols=int(sys.argv[2]) if len(sys.argv)>2 else 3
w=1920//cols if cols<=2 else 640; h=w*9//16; rows=(len(fs)+cols-1)//cols
s=Image.new('RGB',(w*cols,h*rows))
for i,f in enumerate(fs):
    im=Image.open(f).resize((w,h),Image.LANCZOS); d=ImageDraw.Draw(im); d.rectangle((0,0,70,16),fill=(0,0,0)); d.text((4,2),f.split('t_')[1][:-4],fill=(255,255,0))
    s.paste(im,((i%cols)*w,(i//cols)*h))
s.save(f'out/{sys.argv[1]}.jpg',quality=88); print(s.size,len(fs))
