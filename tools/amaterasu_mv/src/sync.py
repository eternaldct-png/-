"""音源から同期データ(sync.json)を作る: 60Hzの帯域エンベロープ、キック/スネア/全体のオンセット、拍グリッド"""
import librosa, numpy as np, json
y, sr = librosa.load('analysis/mono.wav', sr=22050)
hop=128; fr=sr/hop
S=np.abs(librosa.stft(y,n_fft=1024,hop_length=hop)); fq=librosa.fft_frequencies(sr=sr,n_fft=1024)
t=np.arange(S.shape[1])/fr; dur=len(y)/sr
def amp(lo,hi): return S[(fq>=lo)&(fq<hi)].sum(0)
def flux(lo,hi):
    v=np.log1p(amp(lo,hi)); d=np.maximum(0,v[2:]-v[:-2]); return np.concatenate([[0],d,[0]])
def peaks(f,delta,wait):
    pk=librosa.util.peak_pick(f,pre_max=6,post_max=6,pre_avg=40,post_avg=40,delta=delta,wait=wait)
    s=f[pk]; return t[pk], s/np.percentile(s,95)
kt,ks=peaks(flux(25,110),0.25,int(0.12*fr))
st,ss=peaks(flux(1500,6000),0.22,int(0.12*fr))
at,as_=peaks(flux(25,11000),0.2,int(0.1*fr))
P=0.3375; OFF=0.142
ph=((kt-OFF)/P)%1; print('kick phase hist (8 bins of beat):',np.histogram(ph,bins=8)[0], len(kt))
ph=((st-OFF)/P)%1; print('snare phase hist:',np.histogram(ph,bins=8)[0], len(st))
ph2=((kt-OFF)/(P*4))%1; print('kick in bar (16 bins):',np.histogram(ph2,bins=16,weights=ks)[0].round(0))
ph2=((st-OFF)/(P*4))%1; print('snare in bar (16 bins):',np.histogram(ph2,bins=16,weights=ss)[0].round(0))
F=60; tf=np.arange(int(np.ceil(dur*F)))/F
def env(lo,hi):
    v=amp(lo,hi); v=v/np.percentile(v,99.5); return np.clip(np.interp(tf,t,v),0,1.6)
out={'dur':dur,'P':P,'OFF':OFF,'F':F,
 'low':env(25,110),'mid':env(200,2000),'high':env(5000,11000),'all':env(25,11000)}
for k in('low','mid','high','all'): out[k]=[round(float(x),3) for x in out[k]]
for nm,(a,b) in {'kicks':(kt,ks),'snares':(st,ss),'hits':(at,as_)}.items():
    out[nm]=[[round(float(x),3),round(float(min(s,1.5)),2)] for x,s in zip(a,b)]
json.dump(out,open('assets/sync.json','w'))
big=[(round(float(x),2),round(float(s),2)) for x,s in zip(at,as_) if s>1.0]
print('big hits',len(big)); print(big)
