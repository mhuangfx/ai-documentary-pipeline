# The Ledger — direction mockups

Demo content used in all three: title "THE TOILET PAPER TARIFF", line items "3 governments /
1 pulp mill / 1 tariff schedule", stamped key number "14%". All 1920×1080, house palette
(#12161f / #e8e4da / #e0a458 / #5b7a8c).

**Note on method:** nano-banana's configured API key was invalid/expired at generation time
(confirmed via three failed calls, $0 spent — see cost line below), so all three directions
were built procedurally with PIL/numpy instead of AI image generation. This was already the
suggested approach for direction C, and turned out to be the right call for A and B too: it
guarantees the exact demo text renders crisply at 1080p (no AI text-garbling risk) and produces
files that are directly parameterizable as render templates, which is the actual production
goal per the shot breakdown ("LEDGER template … template render", $0/episode).

## A — Thermal receipt (`A_thermal_receipt.png`)
A tall off-white receipt strip sits right-of-center on the dark field with a torn/perforated
top and bottom edge, subtle dot-matrix grain, and a soft curl shadow; monospace line items lead
into a rotated amber-outlined stamp box holding "14%". It reads instantly because the paper is
the only bright shape in the frame and the copy block is a single left-aligned column, receipt-style.
**Animation plan:** the strip "prints" upward out of a slot at the bottom of frame (fast ease-out,
~10–14 frames), each line item stamps/types in top-to-bottom with a soft impact thud per line, then
the amber box slams down with a slight paper-flex and a stamp-thump sound/shake on "14%"; act breaks
reuse just the stamp box slamming onto an otherwise-static, already-printed receipt.
**Template status:** fully generatable as a template. The receipt geometry, grain, and barcode are
static per-series assets; only the two title lines, the item list, and the stamp number are string
inputs to the render function — no per-episode image generation needed.

## B — Accountant's ledger (`B_accountants_ledger.png`)
A top-down open double-column ledger book with hand-ruled (deliberately wobbly) lines, foxed page
edges, and a fountain-pen-blue italic hand for the title/line items on the left page, closed out by
a distressed amber ink-stamp ring reading "14% RECOVERED" on the right page. It's the most "physical
object" of the three, trading a little instant-readability for warmth and craft.
**Animation plan:** open on the book cover closed or off-frame, a quick page-turn/settle into the
top-down flat-lay (the wobble in the ruled lines masks any turn-motion imperfections), then each line
item "writes on" left-to-right with a pen-nib cursor trailing a thin ink-wet highlight; the stamp
drops in with an ink-thump, a faint radial ink-bleed pulse, and the tally column on the right ticks
up in sync. Act breaks can reuse just the stamp-thump on an already-written page.
**Template status:** generatable as a template but with more moving parts — the hand-ruled wobble,
foxing, and stamp grunge are randomized per render (seeded noise), so each episode can get a
slightly different, "more handwritten" page for free; only the title, three items, and stamp number
are per-episode inputs. Slightly heavier to render than A/C (procedural texture generation) but still
$0 and fully scriptable, no per-episode AI generation needed.

## C — Terminal ledger (`C_terminal_ledger.png`)
A flat, minimal graphic ledger: a thin amber kicker rule, a bold sans-serif title, three tabular-numeral
line items separated by hairline vertical dividers, and an amber rounded-rect badge for "14%" that
splits the difference between a rubber stamp (slight rotation, inset border) and a UI badge (crisp
edges, tabular digits). This is the fastest-reading and most broadcast-graphics-package direction —
built and rendered directly in PIL, not through image generation, per the brief's suggestion; a
matplotlib version would look identical since there's no photographic texture to justify it.
**Animation plan:** rules draw on left-to-right (~6–8 frames), title wipes/fades up, the three line
items count/pop in sequence with a subtle amber flash on the numeral, and the badge scales in from
0.8x→1x with a quick overshoot ("stamp" snap) rather than an ink-thump — reads more like a lower-third
sting than a paper prop. Act breaks are just the badge re-punching in on an otherwise static frame.
**Template status:** the most template-friendly of the three by far — pure vector/text layout, zero
randomized texture, trivially parameterized (title, 3×(qty,label), stamp number) and cheapest/fastest
to re-render every episode.

## Cost
$0.00 spent. Three nano-banana calls were attempted for photographic paper/ink textures (thermal
receipt background, ledger book background, grunge stamp ring) but all three failed with an invalid
API key error before any image was generated, so nothing was billed. No GPU was used; no sub-agents were spawned.

## Recommendation
Ship **C, "Terminal ledger,"** as the production direction — it reads fastest at 1080p, costs the
least to render every episode (pure vector, no procedural texture or grain), and its stamp badge
already looks native to a broadcast-graphics package rather than a borrowed prop; keep A ("Thermal
receipt") in reserve as a warmer alternate if the channel wants more physical/tactile texture later.
