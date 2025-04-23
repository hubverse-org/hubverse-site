## Data Pages

These pages are here to serve as a janky way to provide data for the content in
`_partials`. They do not contain any visible content. If you were to render
them as-is, nothing would appear. Instead, we use [quarto
includes](https://quarto.org/docs/authoring/includes.html) to source the yaml
data from these pages into the current page so that we can use the partials
without cluttering or duplicating YAML content.

Note that this is likely off-label usage in quarto, as they mention from their
maunual (linked above):

> It also means that if the included file has a metadata block, that block will
> take effect in all included files. In most cases, having metadata blocks in
> an included file will cause unexpected behavior.


### Usage

This is intended to be used with partials.

Let's assume that you have a partial that prints someone's name:

```markdown
Hello, {{.name}}
```

You can keep a separate data file called `_data/names.qmd` that contains a yaml
header with good names:

```markdown
---
anna:
  name: "Anna Pavlovna Scherer"
  nick: Annette
pierre:
  name: "Count Pyotr Kirillovich Bezukhov"
  nick: Pierre
rostov:
  name: "Count Nikolai Ilyich Rostov"
  nick: Nikolushka
---
```


````markdown
---
title: "Some page"
---

{{< include _data/my-data-page.qmd >}}

## heading

content
content
content

## Greetings, friends

{{< partial _partials/my-partial.qmd anna >}}
{{< partial _partials/my-partial.qmd rostov >}}

````

