# Use build-local ELF-loader/context overlays. Other installed archive members are
# checked byte-for-byte, including the actual HTIF expected_xlen implementation.
checkpoint_fesvr_dir := $(chipyard_dir)/generators/firechip/bridgestubs/src/main/cc/fesvr
checkpoint_fesvr_library := $(GENERATED_DIR)/checkpoint-fesvr/libfesvr-checkpoint.a
checkpoint_fesvr_loader := $(GENERATED_DIR)/checkpoint-fesvr/owned-elfloader.o
checkpoint_fesvr_context := $(GENERATED_DIR)/checkpoint-fesvr/owned-context.o
checkpoint_fesvr_inputs := $(checkpoint_fesvr_dir)/owned_elfloader.cc $(checkpoint_fesvr_dir)/owned_context.cc $(checkpoint_fesvr_dir)/elfloader_policy.h $(checkpoint_fesvr_dir)/build_checkpoint_fesvr.py
ifeq ($(VCS_FORCE_REBUILD),1)
# Copied VCS seed directories retain the old report's absolute output path.
# Rebuild the small overlay as part of each requested native rebuild.
.PHONY: checkpoint-fesvr-rebuild
checkpoint-fesvr-rebuild:
$(checkpoint_fesvr_library): checkpoint-fesvr-rebuild
endif
$(checkpoint_fesvr_library): $(RISCV)/lib/libfesvr.a $(checkpoint_fesvr_inputs) $(wildcard $(RISCV)/include/fesvr/*.h)
	python3 $(checkpoint_fesvr_dir)/build_checkpoint_fesvr.py --library $(RISCV)/lib/libfesvr.a --include $(RISCV)/include --out $@ --cxx "$(CXX)"
$(checkpoint_fesvr_loader): $(checkpoint_fesvr_library)
	$(AR) p $< elfloader.o > $@.tmp && mv $@.tmp $@
$(checkpoint_fesvr_context): $(checkpoint_fesvr_library)
	$(AR) p $< context.o > $@.tmp && mv $@.tmp $@
# libriscv.so also exports load_elf. An ordinary archive reference can be
# satisfied by that shared definition before the replacement is extracted.
# Link the audited member as an object so installed HTIF calls resolve to it.
DRIVER_H += $(checkpoint_fesvr_inputs) $(checkpoint_fesvr_loader) $(checkpoint_fesvr_context)
# VCS combines inherited and explicit LDFLAGS. Put the object in DRIVER_CC so
# it is a single linker input, rather than duplicating it through those flags.
DRIVER_CC += $(checkpoint_fesvr_loader) $(checkpoint_fesvr_context)
