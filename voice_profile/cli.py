import argparse, json, sys
from pathlib import Path
from .analyze import analyze
from .recommend import recommend

def main(argv=None):
    p = argparse.ArgumentParser(prog="voice-profile", description="Podcast voice sound-profile analysis + EQ recommendations")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="measure a WAV (then auto-run recommend)")
    a.add_argument("wav", type=Path); a.add_argument("--speakers", type=Path, help="Riverside aligned_transcript.json; omit for whole-file")
    a.add_argument("--out", type=Path); a.add_argument("--title"); a.add_argument("--no-recommend", action="store_true")
    r = sub.add_parser("recommend", help="metrics.json -> recommendations.md/json")
    r.add_argument("metrics", type=Path); r.add_argument("--out", type=Path)
    x = p.parse_args(argv)
    if x.cmd == "analyze":
        out = x.out or Path("out")/x.wav.stem
        res = analyze(x.wav, out, x.speakers, x.title)
        print(json.dumps(res, indent=1))
        if not x.no_recommend: recommend(out/"metrics.json", out); print((out/"recommendations.md").read_text())
        print(f"Output: {out}", file=sys.stderr)
    else:
        out = x.out or x.metrics.parent; recommend(x.metrics, out); print((out/"recommendations.md").read_text())

if __name__ == "__main__": main()
