# GIF test assets for the videocore GIF source

Made by `make_gifs.py` (own GIF89a writer, no Pillow encoder):

    <venv>/bin/python -I make_gifs.py ../teapot/teapot.bin .

Every file was decoded again with Pillow 13.0.0 and ffmpeg and compared to the canvas the
script composites itself: all frames match in both. `teapot_1bit.gif` composited and packed
MSB-first equals `teapot/teapot.bin` byte for byte (120 x 15000 B).

| file | size | frames | dims | palette | rect mean / max % | purpose |
|---|---|---|---|---|---|---|
| teapot_1bit.gif | 124,934 B | 120 | 400x300 | 4 entries, LZW min code 2 | 34.8 / 44.8 | e-paper 1-bit, needs MAX_WIDTH >= 400 |
| teapot_1bit_320.gif | 122,179 B | 120 | 320x240 | 4 entries, LZW min code 2 | 53.4 / 68.5 | same, centered crop, fits MAX_WIDTH 320 |
| small_rgb.gif | 2,562 B | 20 | 64x64 | 16 entries, LZW min code 4 | 11.5 / 11.8 | RGB565 path on a TFT, 25 fps |
| disposal_2.gif | 445 B | 9 | 64x64 | 4 entries | 6.2 / 6.2 | disposal 2; frame 4 uses disposal 1 |
| delay_0.gif | 590 B | 6 | 32x32 | 4 entries | 100 / 100 | delays 0, 1, 0, 1, 0, 1 cs |
| single_frame.gif | 169 B | 1 | 32x32 | 4 entries | - | one frame, no GCE, no loop extension |

Rect % is the frame's image rect as a share of the canvas, frames 1..n-1 (frame 0 is
always the full canvas).

## Details

- Teapot palette: index 0 = black, 1 = white, 2 = transparent (stored as magenta, never
  shown), 3 = black, unused. A global color table must be a power of two, so 3 entries
  are not possible. Pixel index equals the SSD1683 RAM bit (1 = white).
- Teapot frames: frame 0 is the full canvas with no transparency. Later frames are the
  bounding box of changed pixels with x rounded out to multiples of 8, unchanged pixels
  inside it transparent (index 2). Frames with no change are an 8x1 all-transparent rect.
  Disposal 1, delay 2 cs (50 fps), NETSCAPE loop count 0 (forever).
- teapot_1bit_320 is x 40..359, y 30..269 of the 400x300 frames.
- small_rgb: diagonal stripes (indices 9, 14), a ball circling, colors 2..8, index 15
  transparent. Rects are exact (no 8-pixel rounding). Delay 4 cs, loops forever.
- disposal_2: background index 0 (black). Frame 0 is the full canvas with a white square;
  frames 1..8 are 16x16 squares stepping 6 px diagonally. All use disposal 2 except
  frame 4 (disposal 1), so frame 4's square stays on frames 5..8.

## JSON per GIF

`<name>.json` has the palette, background index, LZW min code size and per frame:
`x, y, w, h, disposal, delay_cs, transparent` plus CRC-32 of the composited canvas:

- `crc32_index`: palette indices, 1 byte per pixel
- `crc32_rgb565le`: RGB565, little-endian uint16 per pixel
- `crc32_rgb565be`: RGB565, big-endian (`reverse_bytes_in_word=True`)
- `crc32_packed` (teapot files): indices at 1 bit per pixel, MSB first, rows of width/8 bytes

`summary.json` is the table above plus the Pillow and ffmpeg match counts.

## Device scripts (untested, use `videogif.GifDecoder` + `videocore.VideoBuffer`)

- `play_tft.py`: small_rgb.gif into a 64x64 RGB565 bytearray VideoBuffer centered in a
  Group on board.DISPLAY; counts frames by watching the buffer change, prints fps each
  second and over 10 s, and checks each frame's CRC against small_rgb.json
  (`REVERSE` picks the byte order, default True like the docstring example).
- `play_epaper_raw.py`: Feather RP2040 ThinkInk + 4.2" SSD1683. GIF into a 1-bit bytearray,
  changed rows pushed as a full-width window: 0x24, update 0x22 0x0C, BUSY, same window to
  0x26. Balanced 4+4 LUT, WW/BB at VSS, ends with an all-white step and the OTP clean.
  Prints ms per step.
