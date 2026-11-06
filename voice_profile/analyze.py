"""Measure a podcast voice 'sound profile' (per speaker or whole file)."""
import json, re, subprocess
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import welch, resample_poly
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

BANDS = [("rumble<80",20,80),("boom80-200",80,200),("mud200-500",200,500),("boxy500-1k",500,1000),
         ("1-2k",1000,2000),("presence2-5k",2000,5000),("sib5-9k",5000,9000),("air10k+",10000,20000)]
# typical voice long-term average spectrum, dB relative to total energy
REF = {"rumble<80":-30,"boom80-200":-6,"mud200-500":-4,"boxy500-1k":-8,"1-2k":-13,
       "presence2-5k":-17,"sib5-9k":-25,"air10k+":-35}

def _slug(s): return re.sub(r"\W+", "_", s).strip("_") or "speaker"

def load_speakers(path):
    s = open(path).read(); t = json.loads(s[s.index("{"):s.rindex("}")+1])
    segs = {}
    for r in t["sentences"]:
        if r.get("playableEndMs") is None or r.get("playableStartMs") is None: continue
        segs.setdefault(r["speaker"], []).append((r["playableStartMs"], r["playableEndMs"]))
    return segs

def true_peak(a): return float(20*np.log10(np.abs(resample_poly(a,4,1,axis=0)).max()+1e-12))

def lra(path):
    err = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-af","ebur128","-f","null","-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"LRA:\s+([\d.]+)", err); return float(m[-1]) if m else None

def measure(a, sr, wavpath):
    m = a.mean(1)
    I = pyln.Meter(sr).integrated_loudness(a)
    fr = int(0.05*sr); rms = np.sqrt(np.convolve(m**2, np.ones(fr)/fr, "valid")[::fr]); rdb = 20*np.log10(rms+1e-9)
    f, P = welch(m, sr, nperseg=8192); band = (f>20)&(f<20000); tot = 10*np.log10(P[band].sum()+1e-20)
    b = {n: round(float(10*np.log10(P[(f>=lo)&(f<hi)].sum()+1e-20)-tot),1) for n,lo,hi in BANDS}
    def pk(lo,hi): s=(f>=lo)&(f<hi); return int(f[s][np.argmax(P[s])])
    # sibilance: short-term (50 ms) 5-9k level, dBFS, over voiced frames
    hop = int(0.05*sr); sibl = []
    from scipy.signal import butter, sosfilt
    sib = sosfilt(butter(4,[5000,min(9000,sr/2-100)],btype="band",fs=sr,output="sos"), m)
    sr_rms = np.sqrt(np.convolve(sib**2, np.ones(hop)/hop, "valid")[::hop]); sdb = 20*np.log10(sr_rms+1e-9)
    voiced = rdb[:len(sdb)] > (np.percentile(rdb,90)-30); sv = sdb[voiced] if voiced.any() else sdb
    gaps = rdb < -60
    return dict(
        I=round(float(I),1), TP=round(true_peak(a),1), LRA=lra(wavpath),
        noise=round(float(np.percentile(rdb,5)),1), speech_rms=round(float(np.percentile(rdb,90)),1),
        clip=int((np.abs(a)>=0.999).sum()), digital_silence_frac=round(float((rdb<=-170).mean()),3),
        gap_frac=round(float(gaps.mean()),3),
        sib_peak_hz=pk(5000,9000), sib_peak_4_10k_hz=pk(4000,10000),
        sib_p50=round(float(np.percentile(sv,50)),1), sib_p90=round(float(np.percentile(sv,90)),1),
        sib_p95=round(float(np.percentile(sv,95)),1), sib_p99=round(float(np.percentile(sv,99)),1),
        bands=b, ref=REF, dev={k: round(b[k]-REF[k],1) for k in b},
        peak_boom_hz=pk(80,200), peak_200_500=pk(150,600), peak_2_5k=pk(2000,5000),
        duration_s=round(len(m)/sr,1)), (f, 10*np.log10(P+1e-20)-tot)

def analyze(wav, out, speakers=None, title=None):
    out.mkdir(parents=True, exist_ok=True)
    x, sr = sf.read(str(wav), always_2d=True); n = len(x)
    if speakers:
        groups = {}
        for spk, segs in load_speakers(speakers).items():
            parts = [x[int(s0*sr/1000):min(n,int(s1*sr/1000))] for s0,s1 in segs if int(s0*sr/1000) < n]
            parts = [p for p in parts if len(p)]
            if parts: groups[spk] = np.concatenate(parts)
    else:
        groups = {"whole_file": x}
    res = {}; plt.figure(figsize=(10,5))
    for spk, a in sorted(groups.items()):
        p = out/f"{_slug(spk)}.wav"
        if speakers: sf.write(str(p), a, sr)
        mtr, (f, Pdb) = measure(a, sr, p if speakers else wav)
        mtr["wav"] = p.name if speakers else str(wav); res[spk] = mtr
        plt.semilogx(f, Pdb, label=spk)
    plt.xlim(30,20000); plt.grid(True,which="both",alpha=.3); plt.legend(); plt.xlabel("Hz"); plt.ylabel("dB rel total")
    plt.title(f"LTAS - {title or wav.name}"); plt.savefig(str(out/"spectrum.png"), dpi=120); plt.close()
    meta = {"source": str(wav), "speakers_json": str(speakers) if speakers else None, "sample_rate": sr}
    json.dump({"_meta": meta, **res}, open(out/"metrics.json","w"), indent=1)
    return res
