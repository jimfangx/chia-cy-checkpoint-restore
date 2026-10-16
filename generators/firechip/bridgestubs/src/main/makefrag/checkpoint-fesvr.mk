# Use build-local resource overlays. CHECKPOINT_HTIF_SOURCE explicitly selects
# the exact-header lifecycle provider; an empty value keeps installed HTIF.
checkpoint_fesvr_dir := $(chipyard_dir)/generators/firechip/bridgestubs/src/main/cc/fesvr
checkpoint_fesvr_output := $(GENERATED_DIR)/checkpoint-fesvr$(if $(strip $(CHECKPOINT_HTIF_SOURCE)),/lifecycle,)
checkpoint_fesvr_library := $(checkpoint_fesvr_output)/libfesvr-checkpoint.a
checkpoint_fesvr_loader := $(checkpoint_fesvr_output)/owned-elfloader.o
checkpoint_fesvr_context := $(checkpoint_fesvr_output)/owned-context.o
checkpoint_fesvr_inputs := $(checkpoint_fesvr_dir)/owned_elfloader.cc $(checkpoint_fesvr_dir)/owned_context.cc $(checkpoint_fesvr_dir)/elfloader_policy.h $(checkpoint_fesvr_dir)/build_checkpoint_fesvr.py
ifneq ($(strip $(CHECKPOINT_HTIF_SOURCE)),)
checkpoint_fesvr_htif := $(checkpoint_fesvr_output)/owned-htif.o
checkpoint_fesvr_inputs += $(CHECKPOINT_HTIF_SOURCE) $(patsubst %.cc,%.h,$(CHECKPOINT_HTIF_SOURCE)) $(checkpoint_fesvr_dir)/htif_lifecycle.h $(checkpoint_fesvr_dir)/htif_signal.h $(checkpoint_fesvr_dir)/htif_lifecycle_provider.inc
checkpoint_fesvr_inputs += $(checkpoint_fesvr_dir)/htif_signal_threads.h
$(checkpoint_fesvr_htif): $(checkpoint_fesvr_library)
	$(AR) p $< htif.o > $@.tmp && mv $@.tmp $@
endif
ifeq ($(VCS_FORCE_REBUILD),1)
# Copied VCS seed directories retain the old report's absolute output path.
# Rebuild the small overlay as part of each requested native rebuild.
.PHONY: checkpoint-fesvr-rebuild
checkpoint-fesvr-rebuild:
$(checkpoint_fesvr_library): checkpoint-fesvr-rebuild
endif
$(checkpoint_fesvr_library): $(RISCV)/lib/libfesvr.a $(checkpoint_fesvr_inputs) $(wildcard $(RISCV)/include/fesvr/*.h)
	python3 $(checkpoint_fesvr_dir)/build_checkpoint_fesvr.py --library $(RISCV)/lib/libfesvr.a --include $(RISCV)/include --out $@ --cxx "$(CXX)" $(if $(strip $(CHECKPOINT_HTIF_SOURCE)),--htif-source "$(CHECKPOINT_HTIF_SOURCE)",)
$(checkpoint_fesvr_loader): $(checkpoint_fesvr_library)
	$(AR) p $< elfloader.o > $@.tmp && mv $@.tmp $@
$(checkpoint_fesvr_context): $(checkpoint_fesvr_library)
	$(AR) p $< context.o > $@.tmp && mv $@.tmp $@
# libriscv.so also exports load_elf. An ordinary archive reference can be
# satisfied by that shared definition before the replacement is extracted.
# Link the audited member as an object so installed HTIF calls resolve to it.
DRIVER_H += $(checkpoint_fesvr_inputs) $(checkpoint_fesvr_loader) $(checkpoint_fesvr_context) $(checkpoint_fesvr_htif)
# VCS combines inherited and explicit LDFLAGS. Put the object in DRIVER_CC so
# it is a single linker input, rather than duplicating it through those flags.
DRIVER_CC += $(checkpoint_fesvr_loader) $(checkpoint_fesvr_context) $(checkpoint_fesvr_htif)
