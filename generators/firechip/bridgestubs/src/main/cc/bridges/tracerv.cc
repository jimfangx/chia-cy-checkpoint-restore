// See LICENSE for license details

#include "tracerv.h"
#include "bridges/tracerv/trace_tracker.h"
#include "bridges/tracerv/tracerv_processing.h"

#include <cassert>
#include <cinttypes>
#include <climits>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <memory>

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <sys/mman.h>

char tracerv_t::KIND;

// put FIREPERF in a mode that writes a simple log for processing later.
// useful for iterating on software side only without re-running on FPGA.
// #define FIREPERF_LOGGER

tracerv_t::tracerv_t(simif_t &sim,
                     StreamEngine &stream,
                     const TRACERVBRIDGEMODULE_struct &mmio_addrs,
                     int tracerno,
                     const std::vector<std::string> &args,
                     int stream_idx,
                     int stream_depth,
                     unsigned int max_core_ipc,
                     const ClockInfo &clock_info)
    : streaming_bridge_driver_t(sim, stream, &KIND), mmio_addrs(mmio_addrs),
      stream_idx(stream_idx), stream_depth(stream_depth),
      max_core_ipc(max_core_ipc), clock_info(clock_info) {
  const char *tracefilename = nullptr;
  const char *dwarf_file_name = nullptr;
  this->tracefile = nullptr;

  this->trace_trigger_start = 0;
  this->trace_trigger_end = ULONG_MAX;
  this->trigger_selector = 0;
  this->tracefilename = "";
  this->dwarf_file_name = "";

  long outputfmtselect = 0;

  const std::string tracefile_arg = "+tracefile=";
  const std::string tracestart_arg = "+trace-start=";
  const std::string traceend_arg = "+trace-end=";
  const std::string traceselect_arg = "+trace-select=";
  // Testing: provides a reference file to diff the collected trace against
  const std::string testoutput_arg = "+trace-test-output";
  // Formats the output before dumping the trace to file
  const std::string humanreadable_arg = "+trace-humanreadable";
  const std::string trace_output_format_arg = "+trace-output-format=";
  const std::string dwarf_file_arg = "+dwarf-file-name=";

  for (auto &arg : args) {
    if (arg == "+tracerv-checkpoint-buffered")
      buffered = true;
    if (arg.find(tracefile_arg) == 0) {
      tracefilename = const_cast<char *>(arg.c_str()) + tracefile_arg.length();
      this->tracefilename = std::string(tracefilename);
    }
    if (arg.find(traceselect_arg) == 0) {
      char *str = const_cast<char *>(arg.c_str()) + traceselect_arg.length();
      this->trigger_selector = atol(str);
    }
    // These next two arguments are overloaded to provide trigger start and
    // stop condition information based on setting of the +trace-select
    if (arg.find(tracestart_arg) == 0) {
      // Start and end cycles are given in decimal
      char *str = const_cast<char *>(arg.c_str()) + tracestart_arg.length();
      this->trace_trigger_start = this->clock_info.to_local_cycles(atol(str));
      // PCs values, and instruction and mask encodings are given in hex
      uint64_t mask_and_insn = strtoul(str, NULL, 16);
      this->trigger_start_insn = (uint32_t)mask_and_insn;
      this->trigger_start_insn_mask = mask_and_insn >> 32;
      this->trigger_start_pc = mask_and_insn;
    }
    if (arg.find(traceend_arg) == 0) {
      char *str = const_cast<char *>(arg.c_str()) + traceend_arg.length();
      this->trace_trigger_end = this->clock_info.to_local_cycles(atol(str));

      uint64_t mask_and_insn = strtoul(str, NULL, 16);
      this->trigger_stop_insn = (uint32_t)mask_and_insn;
      this->trigger_stop_insn_mask = mask_and_insn >> 32;
      this->trigger_stop_pc = mask_and_insn;
    }
    if (arg.find(testoutput_arg) == 0) {
      this->test_output = true;
    }
    if (arg.find(trace_output_format_arg) == 0) {
      char *str =
          const_cast<char *>(arg.c_str()) + trace_output_format_arg.length();
      outputfmtselect = atol(str);
    }
    if (arg.find(dwarf_file_arg) == 0) {
      dwarf_file_name =
          const_cast<char *>(arg.c_str()) + dwarf_file_arg.length();
      this->dwarf_file_name = std::string(dwarf_file_name);
    }
  }

  if (buffered && (outputfmtselect < 0 || outputfmtselect > 1 || dwarf_file_name))
    throw std::runtime_error("unsupported buffered TracerV fireperf/format/tracker");
  if (stream_idx < 0 || stream_depth <= 0 || max_core_ipc == 0 ||
      !clock_info.domain_name || clock_info.multiplier == 0 || clock_info.divisor == 0)
    throw std::runtime_error("invalid TracerV stream/clock configuration");

  if (tracefilename) {
    // giving no tracefilename means we will create NO tracefiles
    std::string tfname = std::string(tracefilename) + std::string("-C") +
                         std::to_string(tracerno);
    output_path = tfname;
    if (buffered) {
      const auto header = this->clock_info.file_header();
      output_bytes.assign(header.begin(), header.end());
    } else {
      this->tracefile = fopen(tfname.c_str(), "w");
      if (!this->tracefile) {
        fprintf(stderr, "Could not open Trace log file: %s\n", tracefilename);
        abort();
      }
      write_header(tracefile);
    }

    // This must be kept consistent with config_runtime.yaml's output_format.
    // That file's comments are the single source of truth for this.
    if (outputfmtselect == 0) {
      this->human_readable = true;
      this->fireperf = false;
    } else if (outputfmtselect == 1) {
      this->human_readable = false;
      this->fireperf = false;
    } else if (outputfmtselect == 2) {
      this->human_readable = false;
      this->fireperf = true;
    } else {
      fprintf(stderr, "Invalid trace format arg\n");
    }
  } else {
    fprintf(
        stderr,
        "TraceRV %d: Tracing disabled, since +tracefile was not provided.\n",
        tracerno);
    this->trace_enabled = false;
  }

  if (fireperf) {
    if (this->dwarf_file_name.compare("") == 0) {
      fprintf(stderr, "+fireperf specified but no +dwarf-file-name given\n");
      abort();
    }
    this->trace_tracker =
        new TraceTracker(this->dwarf_file_name, this->tracefile);
  }
}

tracerv_t::~tracerv_t() {
  if (this->tracefile) {
    fclose(this->tracefile);
  }
}

void tracerv_t::init() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (finished || (buffered && initialized))
    throw std::runtime_error("unsupported TracerV init lifecycle");
  if (!this->trace_enabled) {
    // Explicitly disable token collection in the bridge if no tracefile was
    // provided to improve FMR
    write(mmio_addrs.traceEnable, 0);
  }

  // Configure the trigger even if tracing is disabled, as other
  // instrumentation, like autocounter, may use tracerv-hosted trigger sources.
  if (this->trigger_selector == 1) {
    write(mmio_addrs.triggerSelector, this->trigger_selector);
    write(mmio_addrs.hostTriggerCycleCountStartHigh,
          this->trace_trigger_start >> 32);
    write(mmio_addrs.hostTriggerCycleCountStartLow,
          this->trace_trigger_start & ((1ULL << 32) - 1));
    write(mmio_addrs.hostTriggerCycleCountEndHigh,
          this->trace_trigger_end >> 32);
    write(mmio_addrs.hostTriggerCycleCountEndLow,
          this->trace_trigger_end & ((1ULL << 32) - 1));
    printf("TracerV: Trigger enabled from %lu to %lu cycles\n",
           trace_trigger_start,
           trace_trigger_end);
  } else if (this->trigger_selector == 2) {
    write(mmio_addrs.triggerSelector, this->trigger_selector);
    write(mmio_addrs.hostTriggerPCStartHigh, this->trigger_start_pc >> 32);
    write(mmio_addrs.hostTriggerPCStartLow,
          this->trigger_start_pc & ((1ULL << 32) - 1));
    write(mmio_addrs.hostTriggerPCEndHigh, this->trigger_stop_pc >> 32);
    write(mmio_addrs.hostTriggerPCEndLow,
          this->trigger_stop_pc & ((1ULL << 32) - 1));
    printf("TracerV: Trigger enabled from instruction address %lx to %lx\n",
           trigger_start_pc,
           trigger_stop_pc);
  } else if (this->trigger_selector == 3) {
    write(mmio_addrs.triggerSelector, this->trigger_selector);
    write(mmio_addrs.hostTriggerStartInst, this->trigger_start_insn);
    write(mmio_addrs.hostTriggerStartInstMask, this->trigger_start_insn_mask);
    write(mmio_addrs.hostTriggerEndInst, this->trigger_stop_insn);
    write(mmio_addrs.hostTriggerEndInstMask, this->trigger_stop_insn_mask);
    printf("TracerV: Trigger enabled from start trigger instruction %x masked "
           "with %x, to end trigger instruction %x masked with %x\n",
           this->trigger_start_insn,
           this->trigger_start_insn_mask,
           this->trigger_stop_insn,
           this->trigger_stop_insn_mask);
  } else {
    // Writing 0 to triggerSelector permanently enables the trigger
    write(mmio_addrs.triggerSelector, this->trigger_selector);
    printf("TracerV: No trigger selected. Trigger enabled from %lu to %lu "
           "cycles\n",
           0ul,
           ULONG_MAX);
  }
  write(mmio_addrs.initDone, true);
  initialized = true;
}

size_t tracerv_t::process_tokens(int num_beats, int minimum_batch_beats) {
  size_t maximum_batch_bytes = num_beats * STREAM_WIDTH_BYTES;
  size_t minimum_batch_bytes = minimum_batch_beats * STREAM_WIDTH_BYTES;
  // TODO. as opt can mmap file and just load directly into it.
  page_aligned_sized_array(OUTBUF, this->stream_depth * STREAM_WIDTH_BYTES);
  auto bytes_received =
      pull(this->stream_idx, OUTBUF, maximum_batch_bytes, minimum_batch_bytes);
  if (bytes_received > maximum_batch_bytes || bytes_received % STREAM_WIDTH_BYTES)
    throw std::runtime_error("invalid TracerV token batch");
  // check that a tracefile exists (one is enough) since the manager
  // does not create a tracefile when trace_enable is disabled, but the
  // TracerV bridge still exists, and no tracefile is created by default.
  if (buffered && trace_enabled && bytes_received) {
    // A FILE exists only on this guarded call's stack. The complete persisted
    // history is bytes, never a libc pointer, file offset or unflushed buffer.
    char *data = nullptr;
    size_t length = 0;
    FILE *memory = open_memstream(&data, &length);
    if (!memory)
      throw std::runtime_error("TracerV memory stream allocation failed");
    serialize((uint64_t *)OUTBUF, bytes_received, memory, nullptr,
              max_core_ipc, human_readable, test_output, false);
    const bool failed = ferror(memory);
    const int closed = fclose(memory);
    std::unique_ptr<char, decltype(&std::free)> allocation(data, &std::free);
    if (failed || closed)
      throw std::runtime_error("TracerV buffered serialization failed");
    output_bytes.insert(output_bytes.end(), data, data + length);
  } else if (this->tracefile) {
    std::function<void(uint64_t, uint64_t)> addInstruction = NULL;

    if (fireperf) {
      addInstruction = std::bind(&TraceTracker::addInstruction,
                                 this->trace_tracker,
                                 std::placeholders::_1,
                                 std::placeholders::_2);
    }
    serialize((uint64_t *)OUTBUF,
              bytes_received,
              tracefile,
              addInstruction,
              max_core_ipc,
              human_readable,
              test_output,
              fireperf);
  }
  return bytes_received;
}

void tracerv_t::serialize(
    const uint64_t *const OUTBUF,
    const size_t bytes_received,
    FILE *tracefile,
    std::function<void(uint64_t, uint64_t)> addInstruction,
    const int max_core_ipc,
    const bool human_readable,
    const bool test_output,
    const bool fireperf) {
  const int max_consider = std::min(max_core_ipc, 7);
  if (human_readable || test_output) {
    for (size_t i = 0; i < (bytes_received / sizeof(uint64_t)); i += 8) {
      if (test_output) {
        fprintf(tracefile, "%016lx", OUTBUF[i + 7]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 6]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 5]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 4]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 3]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 2]);
        fprintf(tracefile, "%016lx", OUTBUF[i + 1]);
        fprintf(tracefile, "%016lx\n", OUTBUF[i + 0]);
        // At least one valid instruction
      } else {
        for (int q = 0; q < max_consider; q++) {
          if (OUTBUF[i + q + 1] & valid_mask) {
            fprintf(tracefile,
                    "Cycle: %016" PRId64 " I%d: %016" PRIx64 "\n",
                    OUTBUF[i + 0],
                    q,
                    OUTBUF[i + q + 1] & (~valid_mask));
          }
        }
      }
    }
  } else if (fireperf) {

    for (size_t i = 0; i < (bytes_received / sizeof(uint64_t)); i += 8) {
      uint64_t cycle_internal = OUTBUF[i + 0];

      for (int q = 0; q < max_consider; q++) {
        if (OUTBUF[i + 1 + q] & valid_mask) {
          uint64_t iaddr =
              (uint64_t)((((int64_t)(OUTBUF[i + 1 + q])) << 24) >> 24);
          addInstruction(iaddr, cycle_internal);
#ifdef FIREPERF_LOGGER
          fprintf(tracefile, "%016llx", iaddr);
          fprintf(tracefile, "%016llx\n", cycle_internal);
#endif // FIREPERF_LOGGER
        }
      }
    }
  } else {
    for (size_t i = 0; i < (bytes_received / sizeof(uint64_t)); i += 8) {
      // this stores as raw binary. stored as little endian.
      // e.g. to get the same thing as the human readable above,
      // flip all the bytes in each 512-bit line.
      for (int q = 0; q < 1 + max_consider; q++) {
        fwrite(OUTBUF + (i + q), sizeof(uint64_t), 1, tracefile);
      }
    }
  }
}

void tracerv_t::write_header(FILE *file) {
  fputs(this->clock_info.file_header().c_str(), file);
}

void tracerv_t::tick() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (buffered && (!initialized || finished))
    throw std::runtime_error("unsupported TracerV tick lifecycle");
  if (this->trace_enabled) {
    process_tokens(this->stream_depth, this->stream_depth);
  }
}

// Pull in any remaining tokens and flush them to file
void tracerv_t::flush() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (buffered && (!initialized || finished))
    throw std::runtime_error("unsupported TracerV flush lifecycle");
  flush_tokens();
}

void tracerv_t::flush_tokens() {
  pull_flush(stream_idx);
  while (this->trace_enabled && (process_tokens(this->stream_depth, 0) > 0))
    ;
}

void tracerv_t::finish() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (buffered && (!initialized || finished))
    throw std::runtime_error("unsupported TracerV finish lifecycle");
  flush_tokens();
  if (buffered && trace_enabled) {
    std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
    output.write(reinterpret_cast<const char *>(output_bytes.data()), output_bytes.size());
    output.flush();
    if (!output)
      throw std::runtime_error("TracerV buffered output publish failed");
  }
  finished = true;
}

void tracerv_t::require_checkpointable() const {
  checkpoint_state.require_idle();
  if (!buffered || finished || fireperf || tracefile || trace_tracker || linuxbin || dma_addr)
    throw std::runtime_error("unsupported TracerV live-file/tracker/finished lifecycle");
}

widget_checkpoint_config_t tracerv_t::checkpoint_configuration() const {
  widget_checkpoint_config_t c(12, {
      mmio_addrs.initDone, mmio_addrs.traceEnable,
      mmio_addrs.hostTriggerPCStartHigh, mmio_addrs.hostTriggerPCStartLow,
      mmio_addrs.hostTriggerPCEndHigh, mmio_addrs.hostTriggerPCEndLow,
      mmio_addrs.hostTriggerCycleCountStartHigh, mmio_addrs.hostTriggerCycleCountStartLow,
      mmio_addrs.hostTriggerCycleCountEndHigh, mmio_addrs.hostTriggerCycleCountEndLow,
      mmio_addrs.hostTriggerStartInst, mmio_addrs.hostTriggerStartInstMask,
      mmio_addrs.hostTriggerEndInst, mmio_addrs.hostTriggerEndInstMask,
      mmio_addrs.triggerSelector, uint64_t(stream_idx), uint64_t(stream_depth),
      uint64_t(max_core_ipc), clock_info.multiplier, clock_info.divisor,
      uint64_t(trace_enabled), uint64_t(human_readable), uint64_t(test_output),
      trace_trigger_start, trace_trigger_end, trigger_start_insn,
      trigger_start_insn_mask, trigger_stop_insn, trigger_stop_insn_mask,
      trigger_selector, trigger_start_pc, trigger_stop_pc});
  c.text(clock_info.domain_name);
  // The output path is a fresh-process destination, not captured history.
  // The complete prefix below replaces all FILE position/buffer ownership.
  return c;
}

std::vector<uint8_t> tracerv_t::save_checkpoint() const {
  require_checkpointable();
  auto c = checkpoint_configuration();
  c.word(initialized);
  c.word(cur_cycle);
  c.word(output_bytes.size());
  c.bytes.insert(c.bytes.end(), output_bytes.begin(), output_bytes.end());
  (void)decode_checkpoint(c.bytes);
  return std::move(c.bytes);
}

tracerv_t::decoded_checkpoint_t tracerv_t::decode_checkpoint(
    const std::vector<uint8_t> &payload) const {
  require_checkpointable();
  const auto config = checkpoint_configuration();
  size_t pos = config.bytes.size();
  if (payload.size() < pos || !std::equal(config.bytes.begin(), config.bytes.end(), payload.begin()))
    throw std::runtime_error("TracerV checkpoint configuration mismatch");
  auto word = [&]() {
    if (payload.size() - pos < 8)
      throw std::runtime_error("truncated TracerV checkpoint");
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i)
      value |= uint64_t(payload[pos++]) << (8 * i);
    return value;
  };
  const auto init = word(), cycle = word(), length = word();
  if (init > 1 || length != payload.size() - pos)
    throw std::runtime_error("invalid TracerV checkpoint lifecycle/length");
  auto clock = clock_info;
  const auto header = clock.file_header();
  if ((!trace_enabled && length != 0) ||
      (trace_enabled && (length < header.size() ||
       !std::equal(header.begin(), header.end(), payload.begin() + pos))) ||
      (!init && length != (trace_enabled ? header.size() : 0)) ||
      (trace_enabled && !human_readable && !test_output &&
       (length - header.size()) % (sizeof(uint64_t) * (1 + std::min(max_core_ipc, 7)))))
    throw std::runtime_error("invalid TracerV checkpoint output prefix");
  return {bool(init), cycle, {payload.begin() + pos, payload.end()}};
}

void tracerv_t::validate_checkpoint(const std::vector<uint8_t> &payload) const {
  (void)decode_checkpoint(payload);
}

void tracerv_t::load_checkpoint(const std::vector<uint8_t> &payload) {
  auto decoded = decode_checkpoint(payload); // Validate and allocate before any mutation.
  output_bytes.swap(decoded.output);
  initialized = decoded.initialized;
  cur_cycle = decoded.cur_cycle;
}
