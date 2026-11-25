# How the data works

Every page in this repository is generated from the files under `data/`. To change a page, change the data and run the generator. Do not edit a generated file by hand: the check on every pull request compares each one with what the data produces.

## The files

| File | What it holds |
|---|---|
| `data/taxonomy.yaml` | The groups, domains, and sections; the list of kinds and costs; the rows of the front page's "Start here" table |
| `data/resources/<domain>.yaml` | One record for each resource in that domain. The file name is the domain id |
| `data/compact.yaml` | The compact bookmark set: folders, subsections, and for each link a resource id and the label to show |
| `data/compact.lock` | The SHA-256 that `LINKS.md` and `bookmarks.html` must have |
| `data/link-check-ignore.yaml` | Addresses the link check skips, each with a reason and the date it was last opened by hand |
| `data/original-292.tsv` | The links this collection began with, kept so that the validator can confirm each one still maps to a record |

## The record

```yaml
- id: epss
  name: "Exploit Prediction Scoring System (EPSS)"
  url: "https://www.first.org/epss/"
  publisher: "FIRST"
  section: prioritization
  kind: standard
  cost: free
  description: "Model that estimates the probability a published CVE will be exploited in the wild in the next 30 days; use it to rank remediation work."
  checked:
    date: "2026-11-25"
    status: 200
    final: "https://www.first.org/epss/"
    how: script
```

| Field | Rule |
|---|---|
| `id` | Lower-case slug, unique in the whole catalog, never reused |
| `name` | The resource's own name as its page states it on the day it is checked |
| `formerly` | An earlier name, when the resource was renamed or changed hands |
| `url` | https, the address after redirects, with no tracking parameters, link shorteners, or affiliate codes |
| `previously` | Earlier addresses of the same resource, so that old links stay accounted for |
| `publisher` | Who runs it, as the page states it. When the page names no operator, the project's own name |
| `section` | A section id of the domain the file belongs to |
| `also_in` | Other places to list the resource, each written `domain/section` |
| `kind` | One id from `kinds` in the taxonomy |
| `cost` | One id from `costs` in the taxonomy, taken from the resource's own pricing or sign-up page |
| `description` | One sentence of at most 25 words: what it is and when you reach for it. Written from the page, in your own words, with no adjectives that sell |
| `checked` | `date` the address was opened; the HTTP `status` and `final` address that came back; `how` it was opened: `script`, `browser`, or `blocked` |
| `status` | Omitted for a shown record. `retired` when the resource has gone; `unverified` when the address could not be read. Both need `notes`, and neither is shown on a domain page |
| `replaced_by` | For a retired record, the id of the record that took its place |
| `notes` | What a maintainer needs to know: a login wall, a frozen repository, what was read when the address itself was blocked |

## Adding or changing an entry

1. Open the address and read the page. Take the name, the operator, and the cost from the page itself.
2. Add or edit the record in `data/resources/<domain>.yaml`, with today's date and what the request returned in `checked`.
3. Run the checks:

   ```
   python -m pip install --require-hashes -r requirements.txt
   python scripts/validate.py
   python scripts/build.py
   python scripts/build.py --check
   python scripts/check_links.py
   ```

4. Commit the data and the regenerated pages together.

`scripts/validate.py --self-test` plants one fault for each rule (a duplicate id, a duplicate address, a 30-word description, an http address, a list of 17 links in the compact set, and others) and confirms that each is rejected. `scripts/check_links.py --self-test` confirms that the checker fails a dead address.

## The compact set

`LINKS.md` is read by another TeamStarWolf project, which builds a menu from it. Its shape is fixed:

- `## ` for a folder, `### ` for a subsection, and one `- [Label](address)` on each line with nothing after the closing parenthesis.
- At most 16 folders, at most 16 subsections in a folder, and at most 16 links in a list.
- https addresses. One entry, `http://flaws.cloud/`, is served over http only.

A link in `data/compact.yaml` normally takes its address from the resource record. A link that carries its own `url` is pinned to that address: this is how the compact set keeps an earlier address until the change is made on purpose. When the compact set changes, update `data/compact.lock` in the same pull request with the two new SHA-256 values (`sha256sum LINKS.md bookmarks.html`).

## Addresses that cannot be read

Some sites refuse automated clients. When an address cannot be opened:

- If the site's own feed, documentation, or repository can be read, the entry is written from that, `checked.how` is `blocked`, and `notes` names what was read.
- If nothing can be read, the record gets `status: unverified` and no description. It stays in the data and off the domain pages until someone can open it.

Either way, the address goes on `data/link-check-ignore.yaml` with the reason.
