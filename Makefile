SHELL := /bin/zsh
PROFILE ?= debug
JOBS ?= 6

.PHONY: help configure build test check check-full install-au validate-au reload-au
help:
	@echo "make check       Debug build/tests (no install or audio device)"
	@echo "make check-full  Debug/Release + focused ASan/TSan (no install)"
	@echo "make build       AU + development Standalone; PROFILE=release for Release"
	@echo "make reload-au   Explicit Release build/install/ad-hoc sign/auval"
	@echo "Offline check: python3 scripts/check.py --full --offline"

configure:
	cmake --preset local-$(PROFILE)
build: configure
	cmake --build --preset local-$(PROFILE) --parallel $(JOBS)
test: build
	ctest --preset local-$(PROFILE)
check:
	python3 scripts/check.py --jobs $(JOBS)
check-full:
	python3 scripts/check.py --full --jobs $(JOBS)
install-au:
	$(MAKE) build PROFILE=release
	python3 scripts/au.py install
validate-au:
	python3 scripts/au.py validate
reload-au: install-au
	$(MAKE) validate-au
