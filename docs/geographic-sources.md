# Geographic context provenance

## Natural Earth coastline

Publisher: Natural Earth / contributors, supported by NACIS. Original: `geojson/ne_110m_coastline.geojson` in `nvkelso/natural-earth-vector`, inspected revision `ca96624a56bd078437bca8184e78163e5039ad19`.

- [Pinned GeoJSON](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/ca96624a56bd078437bca8184e78163e5039ad19/geojson/ne_110m_coastline.geojson)
- [Pinned source README and dedication evidence](https://github.com/nvkelso/natural-earth-vector/blob/ca96624a56bd078437bca8184e78163e5039ad19/README.md)
- Source SHA-256: `851f581ff5ffb844deed8ae1a9ce22e3c4bb3d74fa342cadb5d8e39b41ae7c3c`.
- README SHA-256: `28b7c031e45c88d7ce20b7782373aaac378f459e9460001dadc8cfd824c3173b`.

The inspected README describes Natural Earth as a “public domain map dataset” and “free for use in any type of project.” Both downloaded source and README were verified byte-for-byte against this pinned revision. The source-specific license evidence is the pinned repository statement; separate website terms remain unverified. This source-specific statement supports inclusion of this coastline context; it does not license BTS data, proprietary mapping services or other sources.

Processing: retain the 134 coastline coordinate lines; discard feature attributes; round geographic coordinates to three decimal places; emit compact JSON. No airports, routes or freight observations are inferred from coastline geometry. Output `assets/coastlines-110m.json`, **85,769 bytes**, SHA-256 `71e4ecd3dc5f2ee60b401440992fa3f49eef16ce98c3bb47b1a87c4dd1109e1b`. Optional builder `scripts/build_coastline.py` downloads the pinned original, verifies its hash and verifies the exact output hash. The application reads the committed compact file without downloads.

Map attribution: **Coastline and land: Natural Earth 1:110m (public domain). Airport references: OurAirports.** Generalized coastlines are for orientation, not navigation or detailed airport location validation. The map uses no political boundary dataset, remote basemap service, remote font or paid dependency.

## Airport references and observations

OurAirports supplies airport references; BTS supplies segment observations. Their source-specific conditions are documented in [data provenance](data-provenance.md), and package and reference checksums are recorded in the [manifest](../data/processed/manifest.json).

## Natural Earth land fill

The matching `ne_110m_land.geojson` comes from the same Natural Earth revision and public-domain statement as the coastline above. [Pinned source](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/ca96624a56bd078437bca8184e78163e5039ad19/geojson/ne_110m_land.geojson).

- Source SHA-256: `9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9`.
- Compact `assets/land-110m.json`: 85,182 bytes; SHA-256 `4f6e9a66f41aaefb0d2693b4d112abdb440b26186c92727e70abee7cdfc7d566`.
- `python scripts/build_land.py` verifies the pinned source and output. It keeps exterior polygon rings, omits attributes and interior holes, rounds coordinates to three decimals and writes compact JSON. Land fill is generalized visual context, not a political boundary or navigational dataset.

The application reads both geographic assets locally. No remote tiles, source downloads or API credentials are required during use.
