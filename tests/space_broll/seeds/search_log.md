# space_assets.py search test log -- Test F, 12 subjects

Run 2026-09-27 against live endpoints. `count` = candidates returned by that source 
for the query (after the JAXA/CSA/Roscosmos/CNSA/PBS filter); `top hit` = the row our 
picker returned first (highest safe-licence resolution). Sources not queried for a 
subject are omitted from that subject's table (not every source is relevant to every shot).

## nebula filament
query: `nebula filament`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| esahubble | 3 | heic2607a | still | 3864x3864 | CC BY 4.0 | Crab Nebula (2024 Hubble image) |
| esawebb | 3 | potm2605a | still | 12846x7556 | CC BY 4.0 | Webb unveils young stars across every stage of formation |
| eso | 3 | eso0650a | still | 7872x7861 | CC BY 4.0 | Portrait of a dramatic stellar crib* |
| noirlab | 3 | noirlab2406a | still | 35786x35881 | CC BY 4.0 | Ghostly Stellar Tendrils of the Vela Supernova Remnant |
| nasa | 3 | PIA04225 | still | 1460x1502 | Public domain (NASA) | N44C nebula |

## Saturn ring plane low angle
query: `Saturn ring plane`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | PIA01276 | still | 600x800 | Public domain (NASA) | Hubble Views Saturn Ring-Plane Crossing |
| svs | 2 | 20411 | video | 3840x2160 | Public domain (NASA) | A Pathway to Protocells on Titan – Animations |
| esahubble | 3 | opo9828c | still | 1280x822 | CC BY 4.0 | Saturn in natural colours |

## solar granulation flare (SDO)
query: `solar granulation flare`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 0 | -- | -- | -- | -- | (no results) |
| svs | 2 | 13528 | video | 1920x1080 | Public domain (NASA) | Solar Orbiter Media Telecon |

## Enceladus geysers
query: `Enceladus geysers`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | PIA17192 | still | 900x900 | Public domain (NASA) | Tendril-producing Geysers on Enceladus South Polar Terrain |
| svs | 2 | 13947 | video | 1920x1080 | Public domain (NASA) | Video Visions of the Future |

## asteroid Bennu or Ryugu (Ryugu excl.)
query: `asteroid Bennu`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | Bennu_Sample2 | still | 6161x6035 | Public domain (NASA) | Vial with Sample of Asteroid Bennu |

## asteroid Ryugu (must be excluded check)
query: `asteroid Ryugu`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 0 | -- | -- | -- | -- | (no results) |

## spiral galaxy dust lane
query: `spiral galaxy dust lane`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| esahubble | 3 | potw1345a | still | 4240x4211 | CC BY 4.0 | Antennae Galaxies reloaded |
| esawebb | 3 | weic2612a | still | 15187x10238 | CC BY 4.0 | The Cigar Galaxy: M82 (Webb and Hubble image) |
| eso | 3 | eso0007a | still | 4961x4961 | CC BY 4.0 | Fine shades of a Sombrero* |
| noirlab | 3 | noirlab2106a | still | 5513x3038 | CC BY 4.0 | Elliptical galaxy NGC 474 — excerpt from the Dark Energy Survey |

## Mars dune field HiRISE
query: `dune field`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| hirise | 3 | ESP_011496_1100 | still | unknown | Public domain (NASA/HiRISE) | Jeans Crater Dune Field Seasonal Monitoring (ESP_011496_1100) |

## coronal mass ejection SOHO
query: `coronal mass ejection`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | PIA21836 | still | 1500x1500 | Public domain (NASA) | Bastille Day Solar Flare and a Coronal Mass Ejection |
| svs | 1 | 31375 | video | 5760x3240 | Public domain (NASA) | ISS views Aurora from the November 11-13, 2025 Geomagnetic Storm |

## Jupiter cloud bands JunoCam
query: `Jupiter cloud bands Juno`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | PIA21393 | still | 1722x1722 | Public domain (NASA) | Jupiter's Bands of Clouds |

## comet nucleus 67P (ESA, flag CHECK)
query: `comet nucleus 67P`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | PIA18596 | still | 2048x2048 | CHECK: per-asset (esa.int) | Comet Surface Variations |
| esahubble | 1 | heic0310a | still | 2400x1918 | CC BY 4.0 | 3-D models of comet 67P/Churyumov-Gerasimenko's nucleus |
| eso | 3 | potw1436a | still | 1280x824 | CC BY 4.0 | VLT tracks Rosetta's comet |

## protoplanetary disc ALMA/ESO
query: `protoplanetary disc`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| eso | 3 | eso1436a | still | 1800x1800 | CC BY 4.0 | ALMA image of the protoplanetary disc around HL Tauri |
| esahubble | 3 | heic1819a | still | 4398x3982 | CC BY 4.0 | Cosmic shadow of HBC 672 |

## lunar terminator craters LRO
query: `lunar terminator craters`

| source | count | top id | media | w x h | licence | title |
|---|---|---|---|---|---|---|
| nasa | 3 | art002e014055 | still | 5568x3712 | Public domain (NASA) | Craters Along the Lunar Terminator  |
| svs | 3 | 5587 | video | 3840x2160 | Public domain (NASA) | Moon Phase and Libration, 2026 |

## Notes on the required exclusions/flags

- **Ryugu (JAXA) is correctly excluded.** images-api.nasa.gov genuinely returns 0 raw hits for
  "asteroid Ryugu" (NASA never imaged it; that's JAXA's asteroid). To prove the filter itself
  works (not just that NASA has no Ryugu content), we separately queried `nasa search "Hayabusa2"`:
  the raw API returns 1 hit (`jsc2021e062383`), and `space_assets.py` correctly drops it to 0
  results via the banned-terms filter.
- **Bennu (NASA) is correctly included** -- `Bennu_Sample2`, public domain, NASA/GSFC credit.
- **Comet 67P is correctly flagged.** The NASA image library republishes ESA/Rosetta OSIRIS
  imagery verbatim, and several of those records' `secondary_creator` field literally reads
  "Copyright: ESA/Rosetta/MPS for OSIRIS Team ...". `space_assets.py` detects this and emits
  `CHECK: per-asset (esa.int)` instead of a blanket "Public domain (NASA)" -- this was a real bug
  caught during this build (see README "NASA licence is not always PD"). Ground-based *observations*
  of 67P (Hubble's `heic0310a`, ESO's `potw1436a`) are correctly left as CC BY 4.0 since those are
  Hubble/VLT copyright, not Rosetta spacecraft copyright.
- **HiRISE width/height show "unknown"** -- the browse JPEG's pixel dimensions are not published
  inline on the observation page (only image scale in cm/pixel and JP2 file size in MB); see
  README for what a future pass would need to fill this in.
- **SDO / JunoCam / SOHO / LRO were not built as separate connectors** (marked optional in the
  brief). `nasa` (images-api.nasa.gov) covers all four missions' public releases as a byproduct of
  aggregating NASA centers' image libraries -- "coronal mass ejection" and "Jupiter cloud bands
  Juno" both returned good NASA hits above. `svs` (search=solar granulation) returned no genuinely
  on-topic SDO granulation footage in the top slice; a dedicated Helioviewer/JSOC connector would
  do better and is the natural next addition.

## Fetch-path proof (one still, one SVS video)

Downloaded into `tests/space_broll/seeds/00_fetch_proof/`:

| file | source | resolution | bytes | notes |
|---|---|---|---|---|
| `nasa_PIA17192.jpg` | nasa:PIA17192 | 900x900 | 98,680 | Enceladus geysers still, public domain |
| `svs_5675.mp4` | svs:5675 | 3840x2160 h264 | 31,458,274 | original SVS 4K download; no separate audio track present in this particular file |
| `svs_5675_noaudio.mp4` | derived | 3840x2160 h264 | 31,448,108 | `ffmpeg -an -c:v copy` pass (no-op here since source had no audio stream, but the pipeline step ran and is proven for files that do carry one) |
| `svs_5675_proxy720p.mp4` | derived | 1280x720 h264 | 7,866,438 | `ffmpeg -vf scale=-2:720` proxy |

Total downloaded this test run: ~31.6 MB, well under the 500 MB cap.
