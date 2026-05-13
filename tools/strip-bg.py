#!/usr/bin/env python3
"""
strip-bg.py — Convert white-background JPGs to transparent-background PNGs.

For each input .jpg, builds a per-pixel alpha channel from luminance:
  L >= UPPER  -> alpha 0   (fully transparent)
  L <= LOWER  -> alpha 255 (fully opaque)
  in between  -> linear ramp

Luminance is PIL's 'L' mode conversion: L = 0.299*R + 0.587*G + 0.114*B
(Rec. 601 weights).

Output is written alongside each input as <stem>.png. Source .jpg is
preserved — caller is responsible for retiring it once the .png is
visually verified.

Usage:
  python tools/strip-bg.py [--upper 240] [--lower 230] [--max-width WIDTH] [--dry-run] INPUT.jpg [INPUT.jpg ...]
"""
import argparse
import os
import sys
from PIL import Image


def strip_bg(input_path, upper, lower, dry_run=False, max_width=None):
    img = Image.open(input_path).convert('RGB')
    src_size = img.size

    if max_width and img.width > max_width:
        new_height = int(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    out_dims = img.size
    lum = img.convert('L')
    span = upper - lower
    if span <= 0:
        raise ValueError(f"--upper ({upper}) must be greater than --lower ({lower})")

    def alpha_for_lum(L):
        if L >= upper:
            return 0
        if L <= lower:
            return 255
        # L between lower and upper: closer to upper = more transparent.
        # At L = upper, alpha = 0; at L = lower, alpha = 255.
        return int((upper - L) / span * 255)

    alpha = lum.point(alpha_for_lum)
    out = img.copy()
    out.putalpha(alpha)

    output_path = os.path.splitext(input_path)[0] + '.png'
    in_size = os.path.getsize(input_path)

    if dry_run:
        out_size = None
    else:
        out.save(output_path, 'PNG', optimize=True)
        out_size = os.path.getsize(output_path)

    return output_path, src_size, out_dims, in_size, out_size


def main():
    p = argparse.ArgumentParser(description='Strip white background from JPGs to PNG with alpha.')
    p.add_argument('inputs', nargs='+', help='Input .jpg paths')
    p.add_argument('--upper', type=int, default=240, help='L >= this -> fully transparent (default: 240)')
    p.add_argument('--lower', type=int, default=230, help='L <= this -> fully opaque (default: 230)')
    p.add_argument('--dry-run', action='store_true', help='Print what would happen, write nothing')
    p.add_argument('--max-width', type=int, default=None,
                   help='Resize source to this width (preserving aspect) before alpha pass. Default: no resize.')
    args = p.parse_args()

    mode = ' (dry-run)' if args.dry_run else ''
    print(f"Threshold: L >= {args.upper} -> transparent, L <= {args.lower} -> opaque, linear ramp between.{mode}\n")
    print(f"  {'file':<32} {'src dims':<12} {'out dims':<12}  {'in':>10}   {'out':>10}   {'delta':>7}")
    print(f"  {'-'*32} {'-'*12} {'-'*12}  {'-'*10}   {'-'*10}   {'-'*7}")

    for input_path in args.inputs:
        if not os.path.isfile(input_path):
            print(f"  skip: {input_path} not found")
            continue
        output_path, (sw, sh), (ow, oh), in_size, out_size = strip_bg(
            input_path, args.upper, args.lower, dry_run=args.dry_run, max_width=args.max_width
        )
        src_dims = f"{sw}x{sh}"
        out_dims = f"{ow}x{oh}"
        if out_size is None:
            print(f"  {os.path.basename(output_path):<32} {src_dims:<12} {out_dims:<12}  "
                  f"{in_size/1024:>7.1f} KB   {'(dry-run)':>10}   {'':>7}")
        else:
            delta_pct = ((out_size - in_size) / in_size * 100) if in_size else 0
            print(f"  {os.path.basename(output_path):<32} {src_dims:<12} {out_dims:<12}  "
                  f"{in_size/1024:>7.1f} KB   {out_size/1024:>7.1f} KB   {delta_pct:+6.1f}%")


if __name__ == '__main__':
    main()
