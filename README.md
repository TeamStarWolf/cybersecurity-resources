# Cybersecurity Resources

A bookmark collection weighted toward vulnerability management and threat intelligence: 292 bookmarks in a folder tree that you can import into a browser. Some links sit in more than one folder, so the tree holds 265 distinct addresses.

It covers CVE and vulnerability databases, exploit prediction and prioritization (KEV, EPSS, CVSS, SSVC), vendor advisories and PSIRTs, threat intelligence feeds and CTI research, government and CERT alerts, frameworks and standards (MITRE, NIST, CIS, OWASP), offensive and DFIR tooling, cloud and container security, detection engineering, labs, and news.

For references, how-to guides, and learning paths on the same topics, see the [TeamStarWolf library](https://github.com/TeamStarWolf/TeamStarWolf).

## Contents

- `bookmarks.html`: the folder tree, in the bookmark file format that browsers import.
- `LINKS.md`: the same links as a Markdown list, for reading on GitHub.

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

The Chrome, Brave, and Edge steps follow each vendor's help page as it read in November 2026: [Chrome](https://support.google.com/chrome/answer/96816), [Brave](https://support.brave.com/hc/en-us/articles/360019782291-How-do-I-import-or-export-browsing-data), [Edge](https://support.microsoft.com/en-us/edge/import-your-favorites-and-passwords-in-microsoft-edge). Menu names change between browser versions.

## Structure

The top-level folders, in order:

- **⭐ Daily Driver**
- **🔎 Vulnerability Management**
- **🏢 Vendor Advisories & PSIRTs**
- **🧠 Threat Intelligence**
- **🚨 Gov / CERT / Alerts**
- **🧰 Frameworks & Standards**
- **🛠️ Offensive & Tooling**
- **🔬 DFIR & Malware Analysis**
- **☁️ Cloud & Container**
- **🧪 Detection Engineering & Blue Team**
- **🎓 Labs & Training**
- **📰 News & Research**

## License

Released into the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). No attribution is required. The links point to third-party sites that belong to their operators; a link here is not an endorsement. Offensive tools are listed for authorized testing, education, and defensive research.
