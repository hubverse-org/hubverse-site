## Hubverse Website

This is the hubverse website. The goals for this website are to
provide signposts for users who are new to the hubverse.

It is built with [quarto](https://quarto.org) and styled with
Bootstrap 5.

To render this locally, you can use:

```
quarto preview
```

This is the first iteration of the website and there are a few conventions I'm
using heavily:

0. Everything that starts with an underscore is a utility and not intended to be
   actively rendered
1. I am using [quarto partials](http://pkg.garrickadenbuie.com/quarto-partials/)
   to give me templating. All of the templates live in `_partials/`. Examples
   of pages that use partials are `index.qmd`, `community/team.qmd`, and 
   `community/hubs.qmd`
2. Because partials use the metadata (stuff at the top of the qmd file), but not
   variables, I am using a bit of a hack and saving complex metadata in
   separate, content-less files that start with an underscore. For example,
   both `community/hubs.qmd` and `index.qmd` use `community/_active-hubs.qmd`
   to populate the community list.


