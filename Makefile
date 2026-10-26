SHELL := /bin/zsh
PROFILE ?= debug
JOBS ?= 6

.PHONY: help configure build test check check-full routing-check routing-fixtures evaluation-check tracking-check engine-check interaction-check architecture-check install-au validate-au reload-au uninstall-au host-check host-kit session-screen session-kit handoff-check handoff-reproduce
help:
	@echo "make check       Debug build/tests (no install or audio device)"
	@echo "make check-full  Debug/Release + focused ASan/TSan (no install)"
	@echo "make build       AU + development Standalone; PROFILE=release for Release"
	@echo "make reload-au   Explicit Release build/install/ad-hoc sign/auval"
	@echo "make host-check  PR08 exact-built-AU bounce and fresh-process checks; no installation/Logic/device"
	@echo "make host-kit    New synthetic Logic checklist/probes; no project/recording/playback opened"
	@echo "make session-screen  Release synthetic full-AU timing/allocation screen; no Logic/audio device"
	@echo "make session-kit     PR09 instructions/status only; no source/Logic access"
	@echo "make uninstall-au    Explicit owned-product quarantine; quit Logic first; no deletion/cache reset"
	@echo "make handoff-check   Offline Release build and local bundle/evidence identity check; not qualification"
	@echo "make handoff-reproduce  Clean local Git clone + cached full-profile checks; no download/install/Logic"
	@echo "make routing-check  Native AU/processor routing checks; no Logic/device/UI"
	@echo "make routing-fixtures  New private WAV/MIDI test kit; no recording"
	@echo "make evaluation-check  PR02 immutable synthetic fixtures/metric calibration"
	@echo "make tracking-check  PR03 compiled causal tracker research; offline, no device"
	@echo "make engine-check  PR04 isolated Debug/Release/ASan/TSan and complete oracle matrix (offline)"
	@echo "make interaction-check  PR05 isolated three-voice profiles, policies and full interaction matrix"
	@echo "make architecture-check  Bounded offline architecture diagnostics and four-profile safety checks"
	@echo "Offline check: python3 scripts/check.py --full --offline"

configure:
	cmake --preset local-$(PROFILE) -DVOXIDE_OFFLINE=ON
build: configure
	cmake --build --preset local-$(PROFILE) --parallel $(JOBS)
test: build
	ctest --preset local-$(PROFILE)
check:
	python3 scripts/check.py --offline --jobs $(JOBS)
check-full:
	python3 scripts/check.py --full --offline --jobs $(JOBS)
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
engine-check:
	python3 scripts/engine_evaluation.py check --full --offline --jobs $(JOBS)
interaction-check:
	python3 scripts/interaction_evaluation.py check --full --offline --jobs $(JOBS)
architecture-check:
	python3 scripts/architecture_evaluation.py --check
install-au:
	$(MAKE) build PROFILE=release
	python3 scripts/au.py install
validate-au:
	python3 scripts/au.py validate
reload-au: install-au
	$(MAKE) validate-au
uninstall-au:
	python3 scripts/au.py uninstall --allow-uninstall
host-check:
	$(MAKE) build PROFILE=release
	python3 scripts/host_integration.py check --build-dir build/local-release
host-kit:
	python3 scripts/host_integration.py kit
session-screen:
	$(MAKE) build PROFILE=release
	python3 scripts/studio_session.py screen --build-dir build/local-release
session-kit:
	python3 scripts/studio_session.py kit
handoff-check:
	$(MAKE) build PROFILE=release
	python3 scripts/local_handoff.py verify --component build/local-release/voxide_artefacts/Release/AU/voxide.component
handoff-reproduce:
	python3 scripts/local_handoff.py reproduce --jobs $(JOBS)
