import argparse
from pathlib import Path
from corda_synth import CordaSynthesizer, CordaParser

def main():
    parser = argparse.ArgumentParser(description="corda-synth CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # render
    render_p = subparsers.add_parser("render", help="Render a .crd file")
    render_p.add_argument("input", help="Input .crd file")
    render_p.add_argument("-o", "--output", required=True, help="Output .wav file")
    render_p.add_argument("--sample-rate", type=int, default=44100, help="Sample rate")
    
    # render-peo
    render_peo_p = subparsers.add_parser("render-peo", help="Render a single PEO")
    render_peo_p.add_argument("input", help="Input .crd file")
    render_peo_p.add_argument("--peo-id", required=True, help="PEO ID to render")
    render_peo_p.add_argument("-o", "--output", required=True, help="Output .wav file")
    
    # info
    info_p = subparsers.add_parser("info", help="Print file summary")
    info_p.add_argument("input", help="Input .crd file")
    
    args = parser.parse_args()
    
    if args.command == "render":
        synth = CordaSynthesizer(sample_rate=args.sample_rate)
        audio = synth.render(args.input)
        synth.save_wav(audio, args.output)
        
    elif args.command == "render-peo":
        c_parser = CordaParser()
        corda = c_parser.parse(args.input)
        synth = CordaSynthesizer(sample_rate=44100)
        audio = synth.render_peo(args.peo_id, corda)
        synth.save_wav(audio, args.output)
        
    elif args.command == "info":
        c_parser = CordaParser()
        corda = c_parser.parse(args.input)
        print(f"File UUID: {corda.file_uuid}")
        print(f"Duration ticks: {corda.duration_ticks}")
        print(f"Mode: {corda.mode}")
        print(f"Number of PEOs: {len(corda.peos)}")

if __name__ == "__main__":
    main()
