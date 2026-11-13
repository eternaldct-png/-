import librosa, numpy as np, json, re
y, sr = librosa.load('analysis/mono.wav', sr=22050)
hop=128; fr=sr/hop
S=np.abs(librosa.stft(y,n_fft=1024,hop_length=hop))
fq=librosa.fft_frequencies(sr=sr,n_fft=1024)
def bandflux(lo,hi):
    v=np.log1p(S[(fq>=lo)&(fq<hi)].sum(0)); return np.maximum(0,np.diff(v,prepend=v[0]))
def bandamp(lo,hi): return S[(fq>=lo)&(fq<hi)].sum(0)
t=np.arange(S.shape[1])/fr
P=0.3375
kf=bandflux(20,120); sf=bandflux(1800,5000); hf=bandflux(6000,11000); af=bandflux(20,11000)
# beat phase from kick+snare flux
def phase(v,per):
    c=np.sum((v-v.mean())*np.exp(-2j*np.pi*t/per)); return (-np.angle(c)/(2*np.pi)*per)%per
for nm,v in (('kick',kf),('snare',sf),('all',af)):
    print(nm,'phase',phase(v,P), 'half',phase(v,P/2))
ph=phase(af,P/2)%(P/2)
# choose beat offset = ph or ph+P/2 : test kick strength
def fold(v,off,per,n):
    idx=np.floor((t-off+per*0.25)/per).astype(int)
    out=np.zeros(n);cnt=np.zeros(n)
    w=np.abs(((t-off)/per+0.5)%1-0.5)<0.12
    for i in range(n):
        m=w&(idx%n==i)&(idx>=0); out[i]=v[m].mean()
    return out
for off in (ph,ph+P/2):
    print('off',round(off,4),'kick8',fold(kf,off,P,8).round(3),'snare8',fold(sf,off,P,8).round(3))
json.dump({'ph':float(ph)},open('analysis/phase.json','w'))
