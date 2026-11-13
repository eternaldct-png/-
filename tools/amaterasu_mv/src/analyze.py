import librosa, numpy as np, json, sys
y, sr = librosa.load('analysis/mono.wav', sr=22050)
dur = len(y)/sr
print('dur', dur)
hop=512
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, units='time')
print('tempo', tempo, 'nbeats', len(beats))
print('beat intervals median', np.median(np.diff(beats)), 'first beats', beats[:8])
# band energies at 30fps
FPS=30
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))**2
freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
def band(lo,hi):
    return S[(freqs>=lo)&(freqs<hi)].sum(0)
tS = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)
bands = {'low':band(20,150),'mid':band(150,2000),'high':band(4000,11000),'all':S.sum(0)}
tf = np.arange(int(np.ceil(dur*FPS)))/FPS
out={}
for k,v in bands.items():
    v=np.sqrt(v); v=v/np.percentile(v,99.5); 
    out[k]=np.clip(np.interp(tf,tS,v),0,1.5)
# kick onsets: low band flux
def flux_onsets(v, delta):
    env = np.maximum(0,np.diff(np.log1p(v*50),prepend=0))
    pk = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=10, post_avg=10, delta=delta, wait=4)
    return tS[pk], env[pk]
kt,ks = flux_onsets(np.sqrt(bands['low']/np.percentile(bands['low'],99.5)), 0.25)
st,ss = flux_onsets(np.sqrt(band(1500,6000)/np.percentile(band(1500,6000),99.5)), 0.3)
print('kicks',len(kt),'snares',len(st))
# section energy per 2 sec
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
for t0 in np.arange(0,dur,4):
    m=(tS>=t0)&(tS<t0+4)
    lo=np.sqrt(bands['low'][m]).mean(); 
    print(f'{t0:6.1f} rms {rms[m].mean():.3f} low {lo:8.1f} high {np.sqrt(bands["high"][m]).mean():7.1f} onset {oenv[m].mean():.2f}')
json.dump({'dur':dur,'tempo':float(np.atleast_1d(tempo)[0]),'beats':[round(float(b),4) for b in beats],
 'kicks':[[round(float(a),3),round(float(b),3)] for a,b in zip(kt,ks)],
 'snares':[[round(float(a),3),round(float(b),3)] for a,b in zip(st,ss)],
 'fps':FPS, **{k:[round(float(x),3) for x in v] for k,v in out.items()}}, open('analysis/audio.json','w'))
