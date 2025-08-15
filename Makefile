default: help
.PHONY: help

help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

community/contributors.md: scripts/update-contributors.py
	@echo Updating contributors page...
	python scripts/update-contributors.py

_data/active-hubs.qmd: scripts/update-model-counts.sh
	@echo Updating model counts...
	bash scripts/update-model-counts.sh

terminology.qmd: scripts/update_terminology.py
	@echo Updating terminology page...
	python scripts/update_terminology.py

.PHONY: render

render: community/contributors.md _data/active-hubs.qmd terminology.qmd # update files and render to HTML 
	quarto render

.PHONY: preview

preview: community/contributors.md _data/active-hubs.qmd terminology.qmd # update files and preview
	quarto preview

.PHONY: contributors

contributors: community/contributors.md # generate contributors page (requires python)

.PHONY: models

models: _data/active-hubs.qmd # generate models page (requires BASH, yq, and gh)

.PHONY: terminology

terminology: terminology.qmd # generate terminology page (requires python)

