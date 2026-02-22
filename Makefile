
NONGENERABLE=non-generable

all:
	@echo "clean - remove build directories"
	@echo "build - build the new site based markdown, and non-generable content"
	@echo "serve - serve the build directory locally"
	@echo "publish - show diffs against stage"

clean:
	rm -rf build
	rm -rf auto-site
	rm -rf to-deploy
	mkdir -p auto-site
	echo > auto-site/.keep
	mkdir -p to-deploy
	echo > to-deploy/.keep

build:
	./mkAutoSite.py

serve:
	python3 -m http.server -d auto-site/
