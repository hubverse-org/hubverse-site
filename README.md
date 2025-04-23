## hubverse Website

This is the hubverse website. The goals for this website are to
provide signposts for users who are new to the hubverse.

It is built with [quarto](https://quarto.org) and styled with
Bootstrap 5.

To render this locally, you can use:

```
quarto render
```

> [!NOTE]
>
> Some community pages have pre-computed content that you will not see in
> the site preview. If you are interested in pre-computing these pages, you
> can visit the [Makefile](#makefile) section

This is the first iteration of the website and there are a few conventions I'm
using heavily:

0. Everything that starts with an underscore is a utility and not intended to be
   actively rendered.
   1. **partial templates live in [`_partials/`](/_partials)**; I am using
      [quarto partials](http://pkg.garrickadenbuie.com/quarto-partials/) to
      give me templating. All of the templates live in `_partials/`. Examples
      of pages that use partials are `index.qmd` and `community/hubs.qmd`
   2. **data for partials live in [`_data`](/_data)**; To provide data for the
      partials, I am using [quarto
      includes](https://quarto.org/docs/authoring/includes.html). Because
      partials use the metadata (stuff at the top of the qmd file), but not
      variables, I am using a bit of a hack and saving complex metadata in
      separate, content-less files that live in `_data/`. For example, both
      `community/hubs.qmd` and `index.qmd` use `_data/active-hubs.qmd` to
      populate the community list.
   3. **reusable snippets live in [`_snippets/`](includes/_snippets)**;
      Information relevant to software is also relevant to data, so I am
      writing shared piecies of markdown in `_snippets` and re-using them with
      the `{{< include /_snippets/snippet-to-include.qmd >}}` directive.
4. To avoid a further overly complex setup, I am not using computations inside
   the quarto documents.
5. Images live in `includes/img/`


## Makefile

This repository can be built locally with `make`:

```bash
make render
```

This will generate the [pre-computed content](#pre-computed-content) and run
`quarto render` to generate the static site. Note, that it does require Python,
bash, yq, and gh to work.

If you are using this, know that the changes to `community/contributors.md` are
temporary and you should not commit that file


