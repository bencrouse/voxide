SHELL := /bin/zsh
PROFILE ?= debug
JOBS ?= 6

.PHONY: help configure build test check check-full routing-check routing-fixtures evaluation-check tracking-check install-au validate-au reload-au
help:
	@echo "make check       Debug build/tests (no install or audio device)"
	@echo "make check-full  Debug/Release + focused ASan/TSan (no install)"
	@echo "make build       AU + development Standalone; PROFILE=release for Release"
	@echo "make reload-au   Explicit Release build/install/ad-hoc sign/auval"
	@echo "make routing-check  Native AU/processor routing checks; no Logic/device/UI"
	@echo "make routing-fixtures  New private WAV/MIDI test kit; no recording"
	@echo "make evaluation-check  PR02 immutable synthetic fixtures/metric calibration"
	@echo "make tracking-check  PR03 compiled causal tracker research; offline, no device"
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
routing-check:
	python3 scripts/routing.py check --profile $(PROFILE)
routing-fixtures:
	python3 scripts/routing.py prepare
evaluation-check:
	python3 scripts/evaluation.py check
tracking-check:
	cmake --preset local-release -DVOXIDE_OFFLINE=ON
	cmake --build --preset local-release --parallel $(JOBS) --target voxide_tracking_probe
	python3 scripts/tracking_evaluation.py
install-au:
	$(MAKE) build PROFILE=release
	python3 scripts/au.py install
validate-au:
	python3 scripts/au.py validate
reload-au: install-au
	$(MAKE) validate-au
