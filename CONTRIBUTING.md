---
title: "Contributing to the hubverse site"
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
 - `logo/` is a special folder that contains the hubverse logo
 - `brand/` contains a directive that allows us to use the logo in the site
    icons and allow us to use partials.
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

To add a hub or organization to the website, you should edit
[\_data/active-hubs.qmd](_data/active-hubs.qmd).

You can read
[\_data/README.md](_data/README.md)
for more information about
formatting.

### Adding an organization

There is a template of the required fields at the top of the file. You can
duplicate this template and update it to match your organization.

The next step is to edit [community/hubs.qmd](community/hubs.qmd) and add your organization to the
list based on the slug you chose.

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
        contact: "hub-info@example.com"
        repo: "org/hub-name"
        license: "License Name (e.g MIT License)"
        # --- OPTIONAL ----
        aws: "aws-bucket-name"
        insights: https://reichlab.io/variant-nowcast-hub-dashboard/
        forecasts: https://reichlab.io/variant-nowcast-hub-dashboard/forecasts.html
        evals: https://reichlab.io/variant-nowcast-hub-dashboard/evals.html
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

 - [Python](https://python.org) >= 3.9 is needed to generate the contributors page
 - BASH is needed to update the model counts
 - [gh](https://cli.github.com) is needed to fetch the data to update the model counts
 - [yq](https://github.com/mikefarah/yq/#install) is needed to update the model counts

### Optional software

 - Make is optional for generating the site via the Makefile.

## Pre-computed content

There are currently two pages that contain pre-computed content, which is 
automatically run on GitHub every time the site is built. **There is no need to
manually run these scripts.** This avoids unnecessary updates to the source code
with data that updates dynamically.

1. `community/contributors.md` is generated by
   [scripts/contributors.py](scripts/contributors.py). This script auto-generates a
   list of contributors to hubverse github repositories. It requires Python
   and was written by Alvaro J. Castro Rivadeneira and modified by Zhian Kamvar
   for this site.
2. `_data/active-hubs.qmd` is updated by
   [scripts/update-model-counts.sh](scripts/update-model-counts.sh). This
   script uses the GitHub API to update model counts for known hubs. It
   requires BASH, [yq](https://github.com/mikefarah/yq/#install), and
   [gh](https://cli.github.com) and was written by Zhian Kamvar.

Both of these are integrated into [`.github/workflows/publish.yml`](.github/workflows/publish.yml).

If this becomes too burdensome, these scripts could be all ported to python an run using [quarto project scripts](https://quarto.org/docs/projects/scripts.html).
