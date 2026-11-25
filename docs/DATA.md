# How the data works

Every page in this repository is generated from the files under `data/`. To change a page, change the data and run the generator. Do not edit a generated file by hand: the check on every pull request compares each one with what the data produces.

## The files

| File | What it holds |
|---|---|
| `data/taxonomy.yaml` | The groups, domains, and sections; the list of kinds and costs; the rows of the front page's "Start here" table |
| `data/resources/<domain>.yaml` | One record for each resource in that domain. The file name is the domain id |
| `data/compact.yaml` | The compact bookmark set: folders, subsections, and for each link a resource id and the label to show |
| `data/compact.lock` | The SHA-256 that `LINKS.md` and `bookmarks.html` must have |
| `data/link-check-ignore.yaml` | Addresses the link check skips, each with a reason and the date it was last opened by hand, and the largest share of the catalog the list may cover |
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
| `url` | The address after redirects. It follows the address rules below |
| `previously` | Earlier addresses of the same resource, so that old links stay accounted for. They follow the same address rules |
| `publisher` | The organization that runs the resource today, as the page's footer or about page states it. See Publisher below |
| `section` | A section id of the domain the file belongs to |
| `also_in` | Other places to list the resource, each written `domain/section` |
| `kind` | One id from `kinds` in the taxonomy |
| `cost` | One id from `costs` in the taxonomy, taken from the resource's own pricing or sign-up page. See Cost below |
| `maintenance` | Only for a resource that is no longer developed: a `state` and, where known, the date `since`. See Maintenance below |
| `description` | One sentence of at most 25 words: what it is and when you reach for it. Written from the page, in your own words, with no adjectives that sell |
| `checked` | `date` the address was opened; the HTTP `status` and `final` address that came back; `how` it was opened: `script`, `browser`, or `blocked` |
| `status` | Omitted for a shown record. `retired` when the resource has gone; `unverified` when the address could not be read. Both need `notes`, and neither is shown on a domain page |
| `replaced_by` | For a retired record, the id of the record that took its place |
| `notes` | What a maintainer needs to know: a login wall, the date of the last commit, what was read when the address itself was blocked. Notes stay in the data and are not shown on a page |

### Publisher

The publisher is the organization that runs the resource today, as the page's footer or about page states it. After an acquisition, that is the current owner in the form the page gives, such as "Wiz (part of Google Cloud)". Use the project's own name only when the page names no organization. For a repository under a personal account, give the person's display name with the account name in parentheses, such as "Ronnie Flathers (ropnop)", both read from the account's profile.

### Cost

Cost covers everything the description names, not only the first page.

| Cost | When to use it |
|---|---|
| `free` | No payment, account, API key, or sign-up form for anything the description names |
| `free-with-account` | No payment, but something the description names needs an account, an API key, or a sign-up form |
| `freemium` | A free tier or edition exists, with or without an account, and paid plans add more |
| `paid` | Paid only. A time-limited trial does not change this |
| `unconfirmed` | The pricing page could not be opened. Allowed only with `checked.how: blocked` |

If a description says a service can be searched in a browser and queried through an API, and the API needs a free key, the cost is `free-with-account`. When that cannot be said in the sentence, put the detail in `notes`.

### Maintenance

A resource that is still developed has no `maintenance` field. One that is not carries a state, and its row on the domain page then ends with a sentence in italics.

| `state` | When to use it | Sentence on the page |
|---|---|---|
| `archived` | The repository is marked archived by its owner | Archived on February 20, 2026. |
| `maintenance-mode` | The maintainers say it receives fixes only | In maintenance mode. |
| `unmaintained` | The maintainers say it is no longer maintained or developed | No longer actively maintained, as of January 1, 2023. |
| `dormant` | No such statement, but no update for about two years | Last updated in November 2020. |

`since` is written `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`, as precisely as the source gives it. It is required for `dormant` and optional otherwise.

Measure activity by the last commit on the repository's default branch, not by the date of the last push: a push to any branch, including an automated one, moves the push date. `gh api "repos/OWNER/REPO/commits?per_page=1"` returns that commit. For a site, use the newest dated item it lists. Put the date and where it was read in `notes`.

## Address rules

Every address in the data follows these rules: a record's `url`, each address under `previously`, and each pinned `url` in the compact set. They are at least as strict as the rule of the TeamStarWolf project that builds a menu from `LINKS.md`, so an address accepted here cannot break that build.

- It starts with `https://`. One entry, `http://flaws.cloud/`, is served over http only and is allowed by name.
- It is at most 512 characters of printable ASCII, with no space.
- It has none of these characters, which would end a Markdown link, a table cell, or an HTML attribute: `"` `<` `>` `|` `` ` `` `(` `)` `[` `]` `{` `}` `^` `\`. Percent-encode them, as in `%5B` for `[`. It has no HTML entity such as `&amp;` either: write the plain `&`.
- Its host is a DNS name with at least one dot. An IP address in any form, a single-label host, an invalid label, and a punycode (`xn--`) label are rejected.
- It has no credentials before the host and no port.
- Its path has no `.` or `..` segment, plain or percent-encoded, and no encoded slash or backslash.
- It is not a TeamStarWolf address, a link shortener, or an address with a tracking or affiliate parameter.
- It belongs to one record. Two records cannot share an address, whether as `url` or under `previously`.

## Text rules

`name`, `publisher`, `description`, and `formerly` are written into Markdown tables and HTML, so they are plain text:

- Nothing that Markdown or HTML would read as markup: none of the characters `[` `]` `<` `>` `` ` `` `*` `\`, no HTML entity such as `&amp;`, no address (`https://...` or `www....`), no `~~`, no word or phrase wrapped in underscores, and at most one dollar sign.
- No line break, tab, control character, zero-width character, or space other than the ordinary one.
- No emoji, pictograph, arrow, or other symbol outside ASCII, and no dash other than the hyphen.

Letters of any script are allowed. `notes` follow the same rules except the first, because notes are not written into a page. The titles and labels of the compact set are frozen and carry emoji and arrows, so they follow the first two rules and not the third.

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

`scripts/validate.py --self-test` plants one fault at a time and confirms that each is rejected, printing one line per fault. It covers each data rule (a duplicate id, a duplicate address, a 30-word description, a list of 17 links in the compact set, and others), each kind of bad address in each place an address can enter (a record, an earlier address, a pin in the compact set), and each kind of bad text in each field that reaches a page. `scripts/check_links.py --self-test` confirms that the checker fails a dead address and applies the ignore list as written.

## The compact set

`LINKS.md` is read by another TeamStarWolf project, which builds a menu from it. Its shape is fixed:

- `## ` for a folder, `### ` for a subsection, and one `- [Label](address)` on each line with nothing after the closing parenthesis.
- At most 16 folders, at most 16 subsections in a folder, and at most 16 links in a list.
- https addresses. One entry, `http://flaws.cloud/`, is served over http only.

A link in `data/compact.yaml` normally takes its address from the resource record. A link that carries its own `url` is pinned to that address: this is how the compact set keeps an earlier address until the change is made on purpose. When the compact set changes, update `data/compact.lock` in the same pull request with the two new SHA-256 values (`sha256sum LINKS.md bookmarks.html`).

## Addresses that cannot be read

Some sites refuse automated clients. When an address cannot be opened by the script or in a browser:

- If another page of the same publisher can be read (its feed, its documentation, its vendor site, or its repository), the entry is written from that, `checked.how` is `blocked`, and `notes` names what was read. The row on the domain page is marked \*, and the page's last line counts those rows.
- If nothing can be read, the record gets `status: unverified` and no description. It stays in the data and off the domain pages until someone can open it.

Either way, the address goes on the ignore list with the reason.

## The link-check ignore list

`data/link-check-ignore.yaml` names the addresses that the link checks skip. The link check on a pull request and the weekly one both read it, so passing either says nothing about the addresses on it.

```yaml
max_share_percent: 10

entries:
  - url: "https://www.reddit.com/r/"
    match: prefix
    only: ci
    reason: "Returns 403 to GitHub-hosted runners; a desktop network receives a page shell with status 200."
    opened: "2026-11-25"
```

| Field | Rule |
|---|---|
| `max_share_percent` | The largest share of the catalog's published addresses the list may cover. `scripts/validate.py` prints the current share and fails above this number. Raise it only on purpose, in a pull request that says why |
| `url` | The address to skip. It follows the address rules, and it must match at least one address in the catalog or the README |
| `match` | `exact` skips that one address. `prefix` skips every address that starts with `url`, which must then end with a slash so that it cannot match another host or page |
| `only` | Omitted, or `ci`. An entry marked `ci` covers an address that answers a person and `scripts/check_links.py` but refuses requests from GitHub's runners. It is excluded from the CI link check and nothing else |
| `reason` | Why an automated client cannot read the address, as observed |
| `opened` | The date the address was last opened by hand |

Add an entry only after a failure has been observed, and prefer `exact`. `scripts/build.py` writes `.lycheeignore` from this list for the CI link check, anchoring an exact entry at both ends.
