default: help
.PHONY: help

help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

community/contributors.md: scripts/contributors.py # update contributors file
	python scripts/contributors.py

.PHONY: preview

preview: community/contributors.md # update contributors file and preview
	quarto preview

.PHONY: contributors

contributors: community/contributors.md # generate contributors page



