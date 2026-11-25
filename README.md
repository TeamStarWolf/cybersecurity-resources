# Cybersecurity Resources

A checked catalog of cybersecurity and enterprise IT resources, organized by domain, with a compact bookmark set that you can import into a browser.

<!-- counts:start (written by scripts/build.py; do not edit) -->
The catalog holds 612 resources in 17 domains, each opened and read before it was described. The compact bookmark set holds 292 bookmarks in 12 folders. The data also keeps 5 records that are not shown, because the address is retired or could not be read at the last check.
<!-- counts:end -->

Each entry gives the resource's own name, who runs it, one sentence on what it is and when you reach for it, what kind of thing it is, and what it costs. For references, how-to guides, and learning paths on the same subjects, see the [TeamStarWolf library](https://github.com/TeamStarWolf/TeamStarWolf).

[Domains](domains/README.md) · [Index, A to Z](INDEX.md) · [Compact bookmark set](LINKS.md) · [How the data works](docs/DATA.md)

## Start here

<!-- start-here:start (written by scripts/build.py; do not edit) -->
| I want to... | Go to |
|---|---|
| Look up a CVE or check for a public exploit | [Vulnerability management: Vulnerability databases](domains/vulnerability-management.md#vulnerability-databases) |
| Decide which vulnerabilities to fix first | [Vulnerability management: Prioritization and scoring](domains/vulnerability-management.md#prioritization-and-scoring) |
| Find a vendor's security advisories | [Vendor advisories and PSIRTs](domains/vendor-advisories.md) |
| Read what CISA and other national centers have published | [Government and CERT alerts](domains/government-and-cert-alerts.md) |
| Check whether an address, domain, URL, or file is known to be bad | [Threat intelligence and adversaries: Indicator lookup and sharing](domains/threat-intelligence.md#indicator-lookup-and-sharing) |
| Identify a threat group or malware family | [Threat intelligence and adversaries: Adversary and malware tracking](domains/threat-intelligence.md#adversary-and-malware-tracking) |
| Find or write a detection | [Detection and response: Rules and analytics](domains/detection-and-response.md#rules-and-analytics) |
| Analyze a suspicious file or investigate a host | [DFIR and malware analysis](domains/dfir-and-malware-analysis.md) |
| Run an authorized penetration test | [Offensive security](domains/offensive-security.md) |
| Assess a cloud account or a Kubernetes cluster | [Cloud and infrastructure: Audit, posture, and runtime tools](domains/cloud-and-infrastructure.md#audit-posture-and-runtime-tools) |
| Find the framework or control catalog an audit asks for | [GRC and security program](domains/grc-and-security-program.md) |
| Practice in a lab or take a course | [Labs and training](domains/labs-and-training.md) |
| Keep up with security news | [News and research](domains/news-and-research.md) |
| Administer Microsoft 365 or Windows | [Microsoft 365 and Windows administration](domains/microsoft-365-and-windows-administration.md) |
| Check whether a Windows update or a Microsoft service has a known problem | [Microsoft 365 and Windows administration: Release health, updates, and roadmap](domains/microsoft-365-and-windows-administration.md#release-health-updates-and-roadmap) |
| Run a directory or debug a sign-in | [Identity and directory services administration](domains/identity-and-directory-administration.md) |
| Deploy, manage, and patch devices | [Endpoint and device management](domains/endpoint-and-device-management.md) |
<!-- start-here:end -->

## What's inside

<!-- domains:start (written by scripts/build.py; do not edit) -->
**Security domains.** These follow the domain pages of the TeamStarWolf library, in the same order.

| Domain | What it covers | Resources |
|---|---|---|
| [Threat-informed defense and ATT&CK](domains/threat-informed-defense.md) | ATT&CK and the related MITRE knowledge bases, the projects built on them, and the tools that emulate adversary behavior to test defenses. | 10 |
| [Detection and response](domains/detection-and-response.md) | Detection rules and analytics, the platforms that run them, and the data and labs used to build and test detections. | 9 |
| [Threat intelligence and adversaries](domains/threat-intelligence.md) | Indicator lookup, internet scan data, adversary and malware tracking, research blogs, annual threat reports, and intelligence platforms. | 111 |
| [Offensive security](domains/offensive-security.md) | Tools and references for authorized penetration testing and red teaming: reconnaissance, web testing, Active Directory, command and control, and payload references. | 39 |
| [Network security](domains/network-security.md) | Capturing, inspecting, and monitoring network traffic, and the references for securing networks and their protocols. | 2 |
| [Cloud and infrastructure](domains/cloud-and-infrastructure.md) | Assessing and attacking cloud accounts, containers, and Kubernetes, and the providers' own security pages. | 13 |
| [Application and supply chain security](domains/application-and-supply-chain.md) | Standards, testing guides, and tools for building and verifying secure software and its supply chain. | 7 |
| [GRC and security program](domains/grc-and-security-program.md) | Frameworks, control catalogs, benchmarks, and the publications a security program is measured against. | 7 |

**Vulnerability, advisory, and practice domains.** The areas this collection started from.

| Domain | What it covers | Resources |
|---|---|---|
| [Vulnerability management](domains/vulnerability-management.md) | Vulnerability databases, prioritization and scoring, public exploits, scanners, product lifecycle dates, and weakness taxonomies. | 94 |
| [Vendor advisories and PSIRTs](domains/vendor-advisories.md) | The security advisory and bulletin pages of the vendors whose products you run, grouped by kind of product. | 101 |
| [Government and CERT alerts](domains/government-and-cert-alerts.md) | Alerts, advisories, and guidance from national cyber security agencies and coordination centers. | 37 |
| [DFIR and malware analysis](domains/dfir-and-malware-analysis.md) | Malware sandboxes, forensic collection and analysis tools, and reverse engineering tools. | 20 |
| [Labs and training](domains/labs-and-training.md) | Practice labs, ranges, courses, and capture-the-flag events for building security skills. | 16 |
| [News and research](domains/news-and-research.md) | Security news sites, commentary, newsletters, podcasts, and communities. | 31 |

**Enterprise IT domains.** The systems an IT department runs and the references needed to run them.

| Domain | What it covers | Resources |
|---|---|---|
| [Identity and directory services administration](domains/identity-and-directory-administration.md) | Running Active Directory, Microsoft Entra ID, and other directories and identity providers: documentation, tools, and troubleshooting references. | 38 |
| [Microsoft 365 and Windows administration](domains/microsoft-365-and-windows-administration.md) | Administering Microsoft 365 tenants, Windows clients, and Windows Server: admin centers, documentation, release health, and message centers. | 37 |
| [Endpoint and device management](domains/endpoint-and-device-management.md) | Managing fleets of Windows, macOS, Linux, and mobile devices: management platforms, packaging, patching, and imaging. | 40 |

The [domain list](domains/README.md) also defines 15 domains that hold no resources yet: Platform hardening; Identity and data protection; AI and emerging tech; ICS, OT, and hardware; Networking and connectivity; Servers, virtualization, and storage; Cloud platform administration; Automation and scripting; Monitoring, logging, and observability; Backup, recovery, and resilience; IT service management and operations; Email, DNS, and collaboration; Databases and data platforms; Product lifecycle, licensing, and support; The troubleshooting toolbox.
<!-- domains:end -->

## How to read an entry

Every domain page is a set of tables, one for each question a practitioner asks. A row looks like this:

| Resource | Run by | What it is and when to use it | Kind | Cost |
|---|---|---|---|---|
| The resource's own name, linked | Who operates it | One sentence, written from the page itself | One of the kinds below | One of the costs below |

<!-- kinds:start (written by scripts/build.py; do not edit) -->
| Kind | What it means |
|---|---|
| Reference | A knowledge base, catalog, or guide that you look things up in. |
| Standard | A published standard, framework, benchmark, scoring system, or specification. |
| Tool | Software that you download and run yourself. |
| Online service | A hosted lookup, scanner, sandbox, calculator, or search that you use in a browser or through an API. |
| Dataset or feed | Data, rules, samples, or templates that you search, download, or subscribe to. |
| Advisory source | Security advisories and bulletins from a vendor, agency, or coordination center. |
| Vendor documentation | A vendor's own documentation, support, or product security pages. |
| Training or lab | Courses, practice labs, challenges, and ranges. |
| Community | A forum, calendar, or other place where practitioners gather. |
| News | News sites, newsletters, podcasts, and commentary. |
| Research blog | A research team's blog of technical findings. |
| Report | A recurring published report, such as an annual threat report. |
| Organization | The home page of an agency, center, or project body, where its guidance and alerts start. |
| Status page | A provider's live service health page. |

| Cost | What it means |
|---|---|
| Free | No payment and no account needed for the main use. |
| Free with account | No payment, but you must sign up or fill in a form. |
| Freemium | A free tier or edition exists, and paid plans add more. |
| Paid | Paid only. A time-limited trial does not change this. |
| Not confirmed | The pricing page could not be opened when the entry was checked. |
<!-- kinds:end -->

Cost comes from the resource's own pricing or sign-up page. A former name appears in parentheses after the current one.

## The compact bookmark set

Three files carry the bookmarks:

- `bookmarks.html`: the compact set as a folder tree, in the bookmark file format that browsers import.
- [`LINKS.md`](LINKS.md): the same compact set as a Markdown list, for reading on GitHub.
- `bookmarks-full.html`: every resource in the catalog as a folder tree by domain and section, in the same import format.

The compact set is the short list to keep on a bookmarks bar. The full catalog is on the [domain pages](domains/README.md).

## Import

### Chrome

1. At the top right, select **⋮**, then **Bookmarks and lists**, then **Import bookmarks and settings**.
2. Select **Choose file**, pick `bookmarks.html`, select **Open**, then **Done**.

If Chrome had no bookmarks, the folders appear on the bookmarks bar. If it already had some, they are in a new folder named **Imported**; drag **Cybersecurity Resources** from there to the bookmarks bar.

Brave has the same import under its main menu: **Bookmarks**, then **Import Bookmarks and Settings**.

### Edge

1. Select **Settings and more**, then **Settings**.
2. In the **Profiles** settings, select **Import browser data**.
3. Under **Other import locations**, select **Import** next to **Import browser data now**.
4. In the **Import from** list, select **Favorites or bookmarks HTML file**, then **Choose file**, and pick `bookmarks.html`.

### Firefox

1. Open the menu, select **Bookmarks**, then **Manage bookmarks**.
2. In the Library window, select **Import and Backup**, then **Import Bookmarks from HTML**, and pick `bookmarks.html`.

The Chrome, Brave, and Edge steps follow each vendor's help page as it read in November 2026: [Chrome](https://support.google.com/chrome/answer/96816), [Brave](https://support.brave.app/hc/en-us/articles/360019782291-How-do-I-import-or-export-browsing-data), [Edge](https://support.microsoft.com/en-us/edge/import-your-favorites-and-passwords-in-microsoft-edge). Menu names change between browser versions. To import the full catalog, pick `bookmarks-full.html` in the same dialog.

## How entries are chosen

An entry goes in only if all of these hold:

1. Its address was opened, and the page that loaded was the resource it names: not a parked domain, a login wall with nothing behind it, a notice that the page has moved, or a different product.
2. It is the primary or official location: the project's own site or repository, not a mirror or an article about it.
3. It is alive. A tool or repository shows activity within about two years, or says that it is complete. A frozen classic that is still the reference stays, and its entry says so.
4. A practitioner would use it, and one sentence can say who opens it and for what task.
5. It does not duplicate an entry under another name.
6. It is safe to link. Collections of unvetted exploit code carry a warning in their description.

The name, the operator, and the description come from the page as it read on the day it was checked, in this catalog's own words. When a product is renamed or changes hands, the entry takes the current name and keeps the former one.

An address that cannot be read is not described from memory. The record stays in the data with the reason, and it appears on a domain page only when the site's own feed, documentation, or repository could be read instead. An address that has gone is marked retired in the data, with the date and what replaced it.

## How it stays right

- **One source.** Every page here is generated from the files under `data/` by `scripts/build.py`. [How the data works](docs/DATA.md) describes the record and the taxonomy.
- **Checks on every pull request.** `scripts/validate.py` checks the record rules, duplicates, address rules, and the limits of the compact set, and runs planted failures to prove each rule rejects what it should. `scripts/build.py --check` fails if any generated file differs from what the data produces. A link check requests the addresses.
- **A weekly link check** requests every address in the catalog.
- **The compact set is locked.** `LINKS.md` is read by another TeamStarWolf project, so its shape is fixed and its SHA-256 is recorded in `data/compact.lock`. A change to the compact set has to update the lock in the same pull request.
- **The original links are accounted for.** `data/original-292.tsv` records the links this collection began with, and the validator checks that each one still maps to a record.

Corrections are welcome through [issues](https://github.com/TeamStarWolf/cybersecurity-resources/issues) and pull requests.

## License

Released into the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). No attribution is required. The links point to third-party sites that belong to their operators; a link here is not an endorsement. Offensive tools are listed for authorized testing, education, and defensive research.

TeamStarWolf: [Library](https://github.com/TeamStarWolf/TeamStarWolf) · [Intelligence Hub](https://github.com/TeamStarWolf/intelligence-hub) · [ATT&CK-Navi](https://github.com/TeamStarWolf/ATTACK-Navi)
