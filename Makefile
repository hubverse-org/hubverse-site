default: help
.PHONY: help

help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

community/contributors.md: scripts/contributors.py
	@echo Updating contributors page...
	python scripts/contributors.py

community/_active-hubs.qmd: scripts/update-model-counts.sh
	@echo Updating model counts...
	bash scripts/update-model-counts.sh

.PHONY: preview

preview: community/contributors.md community/_active-hubs.qmd # update contributors file and preview
	quarto preview

.PHONY: contributors

contributors: community/contributors.md # generate contributors page (requires python)

.PHONY: models

models: community/_active-hubs.qmd # generate models page (requires BASH, yq, and gh)



