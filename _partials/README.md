## Partials

I am using [quarto partials](http://pkg.garrickadenbuie.com/quarto-partials/)
to give me templating. All of the templates live in `_partials/`. Examples of
pages that use partials are `index.qmd` and `community/hubs.qmd`.

### Usage

Typical usage for these partials is a two-step process

1. define a yaml key (this can be nested) in the header of a markdown file
2. use `{{< partial /_partials/partial-file.qmd >}}` in your document where you
   want the partial to be.

The data source for these partials are in the YAML header, but instead of
shoving all the pieces we need into the yaml header for a single pages or
multiple pages, we store files that _just_ contain data in the `_data/`
directory and use [the quarto include
directive](https://quarto.org/docs/authoring/includes.html) to automatically
include that file with its yaml data.

### Format


The partials all have the `qmd` extension and are expected to work like regular
quarto documents. In order to allow HTML to be used in these documents, it must
be wrapped in a block that looks like this:

````markdown
```{=html}
<div class="card">
  ...
</div>
```
````

### Templating

These partials use mustache logic-less templating. [The mustache(5) manual](https://mustache.github.io/mustache.5.html) provides good examples of how it works.


### Bootstrap cards

The partials are nearly all in HTML form and use [Bootstrap Cards](https://getbootstrap.com/docs/5.3/components/card/). This provides styling for self-contained bits of
information that require very little styling.


