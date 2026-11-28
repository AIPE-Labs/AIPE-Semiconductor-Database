# AIPE Semiconductor Data Explorer (GitHub Pages)

Static, read-only frontend intended for <https://aipe-labs.github.io/AIPE-Semiconductor-Database/>. Plain HTML, CSS
and JavaScript: no framework, no build step, no third-party scripts. `assets/app.css`, `assets/plot.js`, the logo and
the favicon are taken from the AIPE Magnetics Data Explorer (same organisation, MIT) so that both explorers look the
same; `assets/app.js` holds this explorer's views (overview, devices, device page, sources and rights) with hash
routing, so the site works under the `/AIPE-Semiconductor-Database/` sub-path.

The data are generated, never edited by hand. `scripts/build_site.py` reads the committed records through
`aipe_devices.api.Database` (the same queries as the MCP server) and writes `_site/`:

| File | Content |
| --- | --- |
| `data/summary.json` | counts per collection and data class, measured and reviewed counts, build commit |
| `data/sources.json` | data owners with rights status and number of archived original files |
| `data/devices.json` | index for client-side search |
| `data/contributions.json` | contributed data with contributor, licence, status and values (empty until the first contribution) |
| `data/devices/<device_id>.json` | identity, sources with rights, every record in full (loaded on demand) |

What every device page states:

- the source of the data: the archived original file with its SHA-256, or the datasheet with its URL;
- that the redistribution rights are not established, with a link to `LICENSING.md` and to the issue tracker for
  correction or removal requests;
- the data class of every value (manufacturer model, datasheet transcription, measurement) and that no person has
  reviewed the record;
- the conditions the source stated; a condition that is absent is shown as "not stated by the source".

Charts draw the stored grid points joined by straight lines and convert units for display only (°C, mJ, mΩ); the
table under each chart lists the stored SI values. Model guard points at or above 500 °C are hidden unless the reader
ticks the box. Nothing is interpolated.

Local preview:

```sh
python scripts/build_site.py --out _site/AIPE-Semiconductor-Database
python -m http.server 8000 --directory _site   # open http://localhost:8000/AIPE-Semiconductor-Database/
```

## Deployment is manual

`.github/workflows/pages.yml` runs only when started by hand (Actions → "Data Explorer (GitHub Pages)" → Run
workflow). It is not triggered by pushes: publishing the page makes the manufacturer-derived values more visible than
they are in the repository, so each deployment is a decision of the repository owner. One-time setting before the
first run: repository Settings → Pages → Build and deployment → Source: **GitHub Actions**.
