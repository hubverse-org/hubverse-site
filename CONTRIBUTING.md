---
title: '<i class="bi bi-github"></i> Contributing to the hubverse site'
pagetitle: "Contributing to the hubverse site"
---

:::{.callout-important}

It is best to [view this page on GitHub](https://github.com/hubverse-org/hubverse-site/blob/HEAD/CONTRIBUTING.md) so that the links point to the correct pages.

:::

The goal of this website is to provide general, high-level information about the hubverse and to point to existing resources such as documentaiton and vignettes.

This website is built on GitHub with [quarto](https://quarto.org) and uses an
extended version of Pandoc's [markdown
syntax](https://quarto.org/docs/authoring/markdown-basics.html). 
All pages will have links to edit the page, view source, and report an issue
on the side bar or the footer of the page. If you see a problem with a page, 
please click **Report an issue** and describe what should be fixed.

## Concepts to know for editing these documents

There are superstructures in this site that are useful to know. Here are
links to different concepts that are used to generate this site.

 - [quarto markdown syntax](https://quarto.org/docs/authoring/markdown-basics.html)
 - [quarto callout blocks](https://quarto.org/docs/authoring/callouts) (used like admonitions in myst)
 - [quarto article layout](https://quarto.org/docs/authoring/article-layout)
 - [quarto variables](https://quarto.org/docs/authoring/variables.html) (`{{{< var ... >}}}` and `{{{< meta ... >}}}`)
 - [quarto includes directive](https://quarto.org/docs/authoring/includes.html) (`{{{< include ... >}}}`)
 - [quarto partials extension](https://pkg.garrickadenbuie.com/quarto-partials/) (`{{{< partial ... >}}}`)
 - [quarto font awesome extension](https://quarto-ext.github.io/fontawesome/) (`{{{< fa ... >}}}`)
 - Defining a grid with [bootstrap CSS grid](https://getbootstrap.com/docs/5.3/layout/css-grid/)
 - Working with [bootstrap cards](https://getbootstrap.com/docs/5.3/components/card/)

## Structure of the repository

The structure of the website is dictated by `_quarto.yml`.

The repository contains three major content folders that represent sections of
the website:

 - `community/` for all pages related to community information
 - `tools/` for general information about open source tools
 - `quickstart/` for task-based wayfinding and information

All markdown and quarto documents at the root of the repository are included in
the site.

These are supported by _auxiliary content_ folders:

 - `includes/img` contains images that are used in the pages. These images are
   always referenced with a leading slash like so `/includes/img/showcase.png`
 - `brand/` contains a directive that allows us to use the logo in the site
    icons and allow us to use partials.
 - `brand/logo/` is a special folder that contains the hubverse logo
 - `_partials/` contains HTML templates that are used for formatting the more
   complex parts of the site including testimonials and hub layouts. These are
   controlled by the quarto paritals extension
 - `_snippets/` contains shared markdown content that can be used with the quarto
  includes directive
 - `_data/` contains yaml-only quarto documents that serve as as data for the
   `_partials`. Examples are in the readme for that folder.

Finally, there are _build process_ files and folders:

 - `scripts/` are scripts that are run on GitHub actions before the site is built
 - `_extensions` contain quarto extensions that provide shortcuts for writing
   content. We use the font awesome and partials extensions. 
 - `Makefile` is a helper that allows us to port the build process anywhere
 - `.github/workflows/publish.yml` runs all the scripts and publishes the quarto
   site to gh pages.
 - `netlify.toml` and `netlify-build.sh` configure Netlify deploy previews.

## Where the site is hosted

The live site at [hubverse.io](https://hubverse.io) is **served by GitHub
Pages**, published by [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
whenever changes land on `main`.

**Netlify is only used to build deploy previews for pull requests** (see
`netlify.toml` and `netlify-build.sh`), so reviewers can preview changes before
merging. It does not serve the production site. Changes that affect the live
site should target the GitHub Pages build process; Netlify config only needs to
change if the PR-preview build itself needs to change.


## How to add a testimonial

If you want to add a testimonial, thank you! There are two steps to adding a
testimonial:

1. add a 300x300 or larger image to the `includes/img` folder
1. add your information to [\_data/testimonials.qmd](_data/testimonials.qmd) and
   link your image with `/includes/img/name-of-img.png` (the first slash is
   important!)
2. update [index.qmd](index.qmd) with your testimonial.

You can read
[\_data/README.md](_data/README.md)
for more information about
formatting.

## How to add a hub or organization

[\_data/active-hubs.qmd](_data/active-hubs.qmd) is the **single canonical source
of truth for every hub and organization that uses the hubverse.** Everything
else on the site is derived from it — the [list of hubs page](community/hubs.qmd)
(both the cards and the sortable table), the "Organizations using the hubverse"
grid on the landing page, the model- and row-count statistics, and the generated
`output/` data files. To add or update a hub or organization, edit this one file;
the derived content is regenerated automatically at build time.

You can read
[\_data/README.md](_data/README.md)
for more information about
formatting.

### Adding an organization

There is a template of the required fields at the top of the file. You can
duplicate this template and update it to match your organization.

The next step is to add your organization's slug to the `CATEGORIES` dictionary
in [scripts/hub_table.py](scripts/hub_table.py) with the appropriate category
(`"Active"`, `"Archival"`, `"Training"`, or `"Model Development"`). Without
this, the hub will appear under the "Other" category in the table.

You do **not** need to touch the "Organizations using the hubverse" list on the
landing page — it is generated automatically from `_data/active-hubs.qmd` by
[scripts/print_org_list.py](scripts/print_org_list.py) (deduplicated by
organization name), so a new organization appears there on the next build.

### Adding a hub to your organization

To add a hub, find your organization in the list and then add a hub with the
following fields:

```yaml
org:
  [...]
  hubs:
      - [...]
      - name: "Name of Hub"
        description: |
          A description that
          can span
          multiple lines
        contact:
          - name: "hub-info-person"
            email: "hub-info@example.com"
        license: "License Name (e.g MIT License)"
        # --- OPTIONAL ----
        repo: "example-org/hub-name" # must be slug, not URL
        aws: "aws-bucket-name"
        insights: https://reichlab.io/variant-nowcast-hub-dashboard/
        forecasts: https://reichlab.io/variant-nowcast-hub-dashboard/forecasts.html
        evals: https://reichlab.io/variant-nowcast-hub-dashboard/evals.html
        count: 5 # number of models submitted (this is automatically updated if your hub is public)
```

#### Notes

1. the `repo` key must be a slug, not a URL.
1. the `forecasts` key points to a forecast visualization. If you do not have this, omit it.
1. the `evals` key points to a evaluations visualization. If you do not have this, omit it.
1. the `insights` key points to a page that contains insights that are not reflected in `forecasts` or `evals`
1. other hubs will have a `count` key that indicates the number of models that
   have been submitted. These counts are automatically udpated, so you may omit
   it if you wish.

## Software used

### Required software

The following software is required to work on this website

 - [quarto](https://quarto.org) builds the site
 - [git](https://git-scm.com) tracks changes

### Used in production

The following software is used in production for the [pre-computed
content](#pre-computed-content), but is not absolutely necessary to build the
website.

 - [Python](https://python.org) >= 3.9 is needed to generate the contributors, terminology, and cite pages
 - BASH is needed to update the model counts
 - [gh](https://cli.github.com) is needed to fetch the data to update the model counts
 - [yq](https://github.com/mikefarah/yq/#install) is needed to update the model counts

### Optional software

 - Make is optional for generating the site via the Makefile.

## Pre-computed content

Pre-computed content is generated automatically by two GitHub Actions workflows.
**There is no need to manually run these scripts.**

### Publish workflow ([`.github/workflows/publish.yml`](.github/workflows/publish.yml))

Runs every time a commit is pushed to `main` (and on a weekly schedule).
Generates the following content before rendering and publishing the site:

1. `community/contributors.md` is generated by
   [scripts/update_contributors.py](scripts/update_contributors.py). This script auto-generates a
   list of contributors to hubverse GitHub repositories. It requires Python
   and was written by Alvaro J. Castro Rivadeneira and modified by Zhian Kamvar and Matthew Cornell
   for this site.
2. Model counts in `_data/active-hubs.qmd` are updated by the **Update Hub
   Stats** workflow (see below) and committed before publish runs. Running
   `make models` again here would trigger redundant GitHub API calls and
   risk rate-limiting, so it has been removed from this workflow.
3. `terminology.qmd` is generated by
   [scripts/update_terminology.py](scripts/update_terminology.py). This script auto-generates a page with
   [terminology](https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/terminology.md)
   and [abbreviations](https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/abbreviations.md)
   pulled from the [hubDocs site](https://docs.hubverse.io/en/latest/).
   It requires Python and was written by Alvaro J. Castro Rivadeneira for this site.
4. `cite.qmd` is generated by
   [scripts/update_cite.py](scripts/update_cite.py). This script auto-generates a page with
   [cite](https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/cite.md)
   pulled from the [hubDocs site](https://docs.hubverse.io/en/latest/).
   It requires Python and was written by Alvaro J. Castro Rivadeneira for this site.
5. `_data/orgs.qmd` is generated by
   [scripts/print_org_list.py](scripts/print_org_list.py). This script builds the
   "Organizations using the hubverse" list on the landing page from
   `_data/active-hubs.qmd`, deduplicated by organization name so that multiple
   slugs for one organization (e.g. `ecdc` and `ecdc-archival`) appear only once.
   It requires Python.

### Update Hub Stats workflow ([`.github/workflows/update-hub-stats.yml`](.github/workflows/update-hub-stats.yml))

Runs on a weekly schedule (every Monday) and can also be triggered manually.
Fetches row counts and model counts from all hub repositories and opens a pull
request with the updated data files. The workflow:

1. Regenerates `output/hubs.json` and `output/active-hubs-table.csv` from
   `_data/active-hubs.qmd` using [scripts/print_hub_list.py](scripts/print_hub_list.py).
2. Updates model counts in `_data/active-hubs.qmd` using
   [scripts/update_model_counts.sh](scripts/update_model_counts.sh). If a count
   cannot be determined (e.g. a private repository), the existing value is preserved.
3. Fetches row counts for all hub `model-output` and `target-data` directories
   using [scripts/get_hub_stats.py](scripts/get_hub_stats.py). Results are cached
   as parquet files in `output/hub_stats/` and summarised in
   `output/hub_stats_summary.csv`. A `fetch_cache.json` records the last-seen
   `pushed_at` timestamp for each hub so that unchanged hubs are skipped on
   subsequent runs.
4. Checks for regressions using [scripts/check_hub_stats.py](scripts/check_hub_stats.py)
   and [scripts/check_model_counts.sh](scripts/check_model_counts.sh). If any
   row counts or model counts have decreased, a warning comment is posted on the
   pull request.

If this becomes too burdensome, these scripts could be all ported to python and run using [quarto project scripts](https://quarto.org/docs/projects/scripts.html).

:::: {.page-nav}
::: {.prev-page}
[‹](/cite.qmd){.prev-arrow}

[Previous](/cite.qmd){.prev-label}

[**How to cite**](/cite.qmd){.prev-title}
:::

::: {.next-page}
[Next](/quickstart/support-consulting.md){.next-label}

[›](/quickstart/support-consulting.md){.next-arrow}

[**Consulting support**](/quickstart/support-consulting.md){.next-title}
:::
::::
