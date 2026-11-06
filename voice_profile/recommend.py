"""Rules: metrics.json -> EQ / dynamics / loudness recommendations (rules tuned on a real two-person interview)."""
import json
TARGET_I, TARGET_TP = -16.0, -1.0

def magic_audio(m):
    sig = []
    if m.get("noise", 0) <= -170 or m.get("digital_silence_frac", 0) > 0.02: sig.append("true digital silence in gaps")
    if -2.3 <= m.get("TP", 0) <= -1.9: sig.append(f"hard ~-2 dBTP ceiling (TP {m['TP']})")
    if m["dev"].get("rumble<80", 0) <= -5: sig.append(f"rumble already cut ({m['dev']['rumble<80']} dB vs ref)")
    return len(sig) >= 2, sig

def for_speaker(m):
    d = m["dev"]; eq, notes = [], []
    eq.append({"type":"highpass","freq_hz":"80-90","slope":"12-18 dB/oct","why":"standard voice HPF"})
    if d["boom80-200"] > 1.5:
        eq.append({"type":"bell","freq_hz":m.get("peak_boom_hz", m.get("peak_200_500")),"gain_db":-2.0,"q":1.0,"why":f"boom +{d['boom80-200']} dB over ref"})
    if d["boxy500-1k"] > 1.0:
        eq.append({"type":"bell","freq_hz":700,"gain_db":-1.5,"q":1.2,"why":f"boxy +{d['boxy500-1k']} dB over ref"})
    if d["presence2-5k"] > 4.0:
        g = -2.0 if d["presence2-5k"] > 5.0 else -1.5
        eq.append({"type":"bell","freq_hz":m["peak_2_5k"],"gain_db":g,"q":1.5,"why":f"presence +{d['presence2-5k']} dB over ref"})
    des = [{"type":"de-esser","freq_hz":"6500-7000","threshold_dbfs":m.get("sib_p95"),"why":"threshold at p95 sibilance level"}]
    if d["sib5-9k"] > 6.0:
        des.append({"type":"de-esser (narrow)","freq_hz":m["sib_peak_hz"],"threshold_dbfs":m.get("sib_p95"),"q":4,
                    "why":f"sibilance +{d['sib5-9k']} dB over ref; loudest at {m['sib_peak_hz']} Hz"})
    ma, sig = magic_audio(m)
    if ma: notes.append("Magic Audio looks already applied (" + "; ".join(sig) + "). Turn Magic Audio OFF before manual EQ, or the chain double-processes.")
    if m["clip"]: notes.append(f"{m['clip']} clipped samples: fix at source/declip before EQ.")
    loud = {"target_lufs":TARGET_I,"target_dbtp":TARGET_TP,"measured_lufs":m["I"],"measured_dbtp":m["TP"],
            "gain_db":round(TARGET_I-m["I"],1),"limiter_ceiling_dbtp":TARGET_TP}
    return {"magic_audio_detected":ma,"magic_audio_signals":sig,"eq":eq,"de_ess":des,"loudness":loud,"notes":notes}

def recommend(metrics_path, out):
    mt = json.load(open(metrics_path)); recs = {k: for_speaker(v) for k,v in mt.items() if not k.startswith("_")}
    json.dump(recs, open(out/"recommendations.json","w"), indent=1)
    L = ["# Voice profile recommendations", "", f"Source: `{mt.get('_meta',{}).get('source','?')}`", ""]
    for spk, r in recs.items():
        m = mt[spk]
        L += [f"## {spk}", "", f"Measured: {m['I']} LUFS, {m['TP']} dBTP, LRA {m['LRA']}, noise floor {m['noise']} dBFS, clips {m['clip']}", ""]
        if r["magic_audio_detected"]: L += [f"**Magic Audio detected:** {'; '.join(r['magic_audio_signals'])}. Turn it off before manual EQ.", ""]
        L += ["EQ:"] + [f"- {e['type']} {e['freq_hz']} Hz" + (f" {e['gain_db']} dB Q{e['q']}" if 'gain_db' in e else f" {e.get('slope','')}") + f" ({e['why']})" for e in r["eq"]]
        L += ["", "De-ess:"] + [f"- {e['type']} {e['freq_hz']} Hz, threshold {e['threshold_dbfs']} dBFS ({e['why']})" for e in r["de_ess"]]
        lo = r["loudness"]; L += ["", f"Loudness: {lo['gain_db']:+} dB gain to {lo['target_lufs']} LUFS, true-peak limiter at {lo['target_dbtp']} dBTP", ""]
        L += [f"- {n}" for n in r["notes"]] + [""]
    (out/"recommendations.md").write_text("\n".join(L)); return recs
