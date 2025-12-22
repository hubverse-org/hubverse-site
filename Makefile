default: help

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: contributors
contributors: # generate contributors page (requires python)
	@echo Updating contributors page...
	python scripts/update-contributors.py

.PHONY: models
models: # generate models page (requires BASH, yq, and gh)
	@echo Updating model counts...
	bash scripts/update-model-counts.sh

.PHONY: terminology
terminology: # generate terminology page (requires python)
	@echo Updating terminology page...
	python scripts/update-terminology.py

.PHONY: cite
cite: # generate cite page (requires python)
	@echo Updating cite page...
	python scripts/update-cite.py

.PHONY: render
render: contributors models terminology cite # update files and render to HTML 
	quarto render

.PHONY: preview
preview: contributors models terminology cite # update files and preview
	quarto preview

