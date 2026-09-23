---
name: terms-recheck
description: Re-read the licence and terms pages behind the claim registers, and record what changed, because vendors amend them without notice. Use when asked to re-check, refresh or audit the licences in research/claims, before a release, or when a vendor announces new terms.
---

# Terms recheck: re-read the dated terms the registers rest on

Vendors amend their terms. Reallusion's Content EULA reserves "the right to
make changes to the Terms from time to time without notice", and its Software
EULA says "The most current
version of these Terms supersedes all previous versions"
(`research/claims/character-tools.json`, CHT-006). A licence claim is only as
current as its `checked` date. This skill re-reads the pages. It never adds a
new licence: that is `licence-audit`.

## 1. List what to re-read

```sh
python3 - <<'EOF'
import json, glob
seen = {}
for f in sorted(glob.glob("research/claims/*.json")):
    d = json.load(open(f))
    for c in d["claims"]:
        if c["kind"] == "licence":
            for u in c["sources"]:
                seen.setdefault(u, []).append(c["id"])
for u, ids in sorted(seen.items()):
    print(",".join(ids[:4]) + ("..." if len(ids) > 4 else ""), u)
EOF
```

Start with vendor terms pages, which change most: Reallusion, Autodesk, Maxon,
Poser and Renderosity, Adobe and Epic. Licence files in a GitHub repository
change least.

**Never fetch daz3d.com with any tool.** Daz's Terms of Service forbid
automated access. Ask the owner to read the Daz pages in a browser.

## 2. Re-read each page with the two lenses

For each claim, follow `.claude/skills/licence-audit/` and the "How claims were
checked" section of `research/README.md`:

- **`text`**: every quoted clause must still appear on the live page as
  quoted, and the claim must say no more than the page does.
- **`drift`**: compare with the claim's date. Use Wayback captures
  (`https://web.archive.org/web/<timestamp>id_/<url>`) to find when the page
  changed.

`www.autodesk.com` and `forums.autodesk.com` return HTTP 403 to curl. Read them
in a browser tool instead. `support.maxon.net` sits behind Cloudflare, and its
Zendesk API returns the article body.

## 3. Do not trust a shortcut

Two automatic signals were tried on 2026-09-23, across every register's
licence sources, and both failed:

- **Server dates.** Most pages sent no `Last-Modified` header. A dynamic page
  reported the day of the request, so it always looked changed.
- **Matching the quoted date stamp.** The Content EULA prints its date as
  `1<sup>st</sup>`, so the text "Updated August 1st, 2025" never matches the
  raw page. Several Autodesk pages returned no body to curl at all.

A third trap: **raw HTML is not what a reader sees.** Reallusion's Content
License Policy page still carries an old FAQ inside a block styled
`display: none`, and its FAQ data marks those answers `"disabled": true`. Two
checks that read the page with curl took the hidden answers as live
(`research/claims/character-tools.json`, CHT-023, and DAZ-105). Render the page
in a browser, or read its FAQ data file and skip disabled entries.

Only a read of the text settles it.

## 4. Record it

Update the register first and the page second:

- Add one entry to the claim's `checks`, with `lens`, `verdict`, `read`,
  `evidence` and `notes`. Keep the old entries.
- Set `status` by the rule in `research/README.md`. Put corrected wording in
  `claim`, and leave `as_first_reported` untouched.
- Update the register's `checked` and `statuses`, then run the status check at
  the end of `research/README.md`.
- Change every page, skill and table that states the claim, as
  `licence-audit` step 5 lists.

Report each page as unchanged, changed with the claims affected, or
unreadable. A page that could not be read stays at its old date. Say so, and
never mark it re-checked.
