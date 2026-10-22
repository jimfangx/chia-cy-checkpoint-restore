// See LICENSE for license details

#include "blockdev.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <memory>

char blockdev_t::KIND;

/* Block Device Endpoint Driver
 *
 * This works in conjunction with
 * testchipip/src/main/scala/BlockDevice.scala (Block Device RTL)
 * and
 * src/main/scala/bridges/BlockDevWidget.scala
 */

/* Uncomment to get DEBUG printing
 * TODO: better logging mechanism so that we don't need this */
// #define BLKDEV_DEBUG

#ifdef BLKDEV_DEBUG
#define blkdev_printf(...)                                                     \
  if (this->logfile) {                                                         \
    fprintf(this->logfile, __VA_ARGS__);                                       \
    fflush(this->logfile);                                                     \
  }
#else
#define blkdev_printf(...)                                                     \
  {}
#endif

/* Block Dev software driver constructor.
 * Setup software driver state:
 * Check if we have been given a file to use as a disk, record size and
 * number of sectors to pass to widget */
blockdev_t::blockdev_t(simif_t &sim,
                       const BLOCKDEVBRIDGEMODULE_struct &mmio_addrs,
                       int blkdevno,
                       const std::vector<std::string> &args,
                       uint32_t num_trackers,
                       uint32_t latency_bits)
    : bridge_driver_t(sim, &KIND), mmio_addrs(mmio_addrs), latency_bits(latency_bits) {
  this->_file = nullptr;
  this->logfile = nullptr;
  _ntags = num_trackers;
  long size;
  long mem_filesize = 0;

  const char *logname = nullptr;

  // construct arg parsing strings here. We basically append the bridge_driver
  // number to each of these base strings, to get args like +blkdev0 etc.
  std::string num_equals = std::to_string(blkdevno) + std::string("=");

  std::string blkdev_arg = std::string("+blkdev") + num_equals;
  std::string blkdevinmem_arg = std::string("+blkdev-in-mem") + num_equals;
  std::string blkdevwlatency_arg = std::string("+blkdev-wlatency") + num_equals;
  std::string blkdevrlatency_arg = std::string("+blkdev-rlatency") + num_equals;
  std::string blkdevlog_arg = std::string("+blkdev-log") + num_equals;

  for (auto &arg : args) {
    if (arg.find(blkdev_arg) == 0) {
      filename = const_cast<char *>(arg.c_str()) + blkdev_arg.length();
    }
    // Spoofs a file with fmemopen. Useful for testing
    if (arg.find(blkdevinmem_arg) == 0) {
      mem_filesize =
          atoi(const_cast<char *>(arg.c_str()) + blkdevinmem_arg.length());
    }
    if (arg.find(blkdevwlatency_arg) == 0) {
      write_latency =
          atoi(const_cast<char *>(arg.c_str()) + blkdevwlatency_arg.length());
    }
    if (arg.find(blkdevrlatency_arg) == 0) {
      read_latency =
          atoi(const_cast<char *>(arg.c_str()) + blkdevrlatency_arg.length());
    }
    if (arg.find(blkdevlog_arg) == 0) {
      logname = const_cast<char *>(arg.c_str()) + blkdevlog_arg.length();
    }
  }

  uint32_t max_latency = (1UL << latency_bits) - 1;
  if (write_latency > max_latency) {
    fprintf(stderr,
            "Requested blockdev write latency (%u) exceeds HW limit (%u).\n",
            write_latency,
            max_latency);
    abort();
  }

  if (read_latency > max_latency) {
    fprintf(stderr,
            "Requested blockdev read latency (%u) exceeds HW limit (%u).\n",
            read_latency,
            max_latency);
    abort();
  }

  if (logname) {
    logfile = fopen(logname, "w");
    if (logfile == nullptr) {
      fprintf(stderr, "Could not open %s\n", logname);
      abort();
    }
  }

  if (filename) {
    _file = fopen(filename, "r+");
    if (!_file) {
      fprintf(stderr, "Could not open %s\n", filename);
      abort();
    }
    if (fseek(_file, 0, SEEK_END)) {
      perror("fseek");
      abort();
    }
    size = ftell(_file);
    if (size < 0) {
      perror("ftell");
      abort();
    }
  } else if (mem_filesize > 0) {
    size = mem_filesize * long(SECTOR_SIZE);
    memory_disk.resize(size);
    _file = fmemopen(memory_disk.data(), memory_disk.size(), "r+");
    if (!_file) {
      perror("fmemopen");
      abort();
    }
  } else {
    size = 0;
  }
  _nsectors = size >> SECTOR_SHIFT;

  write_trackers.resize(_ntags);
}

blockdev_t::~blockdev_t() {
  if (_file) {
    fclose(_file);
  }
  if (logfile)
    fclose(logfile);
}

/* "init" for blockdev widget that gets called right before target_reset.
 * Here, we set control regs e.g. for # sectors, allowed request length
 * at boot */
void blockdev_t::init() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (initialized)
    throw std::runtime_error("blockdev already initialized");
  // setup blk dev widget
  write(mmio_addrs.bdev_nsectors, nsectors());
  write(mmio_addrs.bdev_max_req_len, max_request_length());
  write(mmio_addrs.read_latency, read_latency);
  write(mmio_addrs.write_latency, write_latency);
  initialized = true;
}

/* Take a read request, get data from the disk file, and fill the beats
 * into the response queue from which data will be written to the block device
 * widget on the FPGA */
void blockdev_t::do_read(struct blkdev_request &req) {
  uint64_t offset, nbeats;
  uint64_t blk_data[MAX_REQ_LEN * SECTOR_BEATS];

  offset = req.offset;
  offset <<= SECTOR_SHIFT;
  nbeats = req.len;
  nbeats *= SECTOR_BEATS;

  /* Check that the request is valid. */
  if ((req.offset + req.len) > nsectors()) {
    fprintf(stderr,
            "Read range %u - %u out of bounds\n",
            req.offset,
            req.offset + req.len);
    abort();
  }
  if (req.len == 0) {
    fprintf(stderr, "Read request cannot have 0 length\n");
    abort();
  }
  if (req.len > MAX_REQ_LEN) {
    fprintf(stderr,
            "Read request length too large: %u > %u\n",
            req.len,
            MAX_REQ_LEN);
    abort();
  }
  if (req.tag >= _ntags) {
    fprintf(stderr, "Read request tag %d too large.\n", req.tag);
    abort();
  }

  /* Seek to correct place in the file. */
  if (fseek(_file, offset, SEEK_SET)) {
    fprintf(stderr, "Could not seek to %" PRIx64 "\n", offset);
    abort();
  }

  /* Perform the read from file. */
  if (fread(blk_data, SECTOR_SIZE, req.len, _file) < req.len) {
    fprintf(stderr, "Cannot read data at %" PRIx64 "\n", offset);
    abort();
  }

  /* Populate response queue from data that has been read from file. Response
   * queue will be consumed when writing to FPGA. */
  for (uint64_t i = 0; i < nbeats; i++) {
    struct blkdev_data resp;
    resp.data = blk_data[i];
    resp.tag = req.tag;
    read_responses.push(resp);
  }
}

/* Take a write request and set up a write_tracker to process it.
 * Later, handle_data will be called to actually perform the writes
 * to file. */
void blockdev_t::do_write(struct blkdev_request &req) {
  if (req.tag >= _ntags) {
    /* Check that req.tag is in range.
     * This check must happen before we index into write_trackers */
    fprintf(stderr, "Write request tag %d too large.\n", req.tag);
    abort();
  }

  struct blkdev_write_tracker &tracker = write_trackers[req.tag];

  /* Check request sanity */
  if ((req.offset + req.len) > nsectors()) {
    fprintf(stderr,
            "Write range %u - %u out of bounds\n",
            req.offset,
            req.offset + req.len);
    abort();
  }
  if (req.len == 0) {
    fprintf(stderr, "Write request cannot have 0 length\n");
    abort();
  }
  if (req.len > MAX_REQ_LEN) {
    fprintf(stderr, "Write request too large: %u > %u\n", req.len, MAX_REQ_LEN);
    abort();
  }

  /* Setup tracker state */
  tracker.offset = req.offset;
  tracker.offset *= SECTOR_SIZE;
  tracker.count = 0;
  tracker.size = req.len;
  tracker.size *= SECTOR_BEATS;
}

/* Confirm that a write_tracker has been setup for a chunk of data that
 * we have received from the block device widget, to be written to file */
bool blockdev_t::can_accept(struct blkdev_data &data) {
  if (data.tag >= _ntags)
    throw std::runtime_error("blockdev data tag out of range");
  return write_trackers[data.tag].size > 0;
}

void blockdev_t::handle_data(struct blkdev_data &data) {
  if (data.tag >= _ntags) {
    /* Check that data.tag is in range.
     * This check must happen before we index into write_trackers */
    fprintf(stderr, "Data tag %d too large.\n", data.tag);
    abort();
  }

  struct blkdev_write_tracker &tracker = write_trackers[data.tag];

  /* Copy data into the write tracker */
  tracker.data[tracker.count] = data.data;
  tracker.count++;

  if (tracker.count < tracker.size) {
    /* We are still waiting to receive all the data for this write
     * request, so return. */
    return;
  }

  /* Seek to the right place to begin the write to file. */
  if (fseek(_file, tracker.offset, SEEK_SET)) {
    fprintf(stderr, "Could not seek to %" PRIx64 "\n", tracker.offset);
    abort();
  }

  /* Perform the write to file. */
  if (fwrite(tracker.data, sizeof(uint64_t), tracker.count, _file) <
      tracker.count) {
    fprintf(stderr, "Cannot write data at %" PRIx64 "\n", tracker.offset);
    abort();
  }

  /* Clear the tracker state */
  tracker.offset = 0;
  tracker.count = 0;
  tracker.size = 0;

  /* Send an ack to the block device.
   * TODO: should a block device do this?  Biancolin: Yes.*/
  write_acks.push(data.tag);
}

/* Read all pending request data from the widget */
void blockdev_t::recv() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (!initialized) throw std::runtime_error("blockdev not initialized");
  recv_impl();
}

void blockdev_t::recv_impl() {
  /* Read all pending requests from the widget */
  while (read(mmio_addrs.bdev_req_valid)) {
    /* Take a request from the FPGA and put it in SW processing queues */
    struct blkdev_request req;
    req.write = read(mmio_addrs.bdev_req_write);
    req.offset = read(mmio_addrs.bdev_req_offset);
    req.len = read(mmio_addrs.bdev_req_len);
    req.tag = read(mmio_addrs.bdev_req_tag);
    write(mmio_addrs.bdev_req_ready, true);
    requests.push(req);
    blkdev_printf("[disk] got req. write %x, offset %x, len %x, tag %x\n",
                  req.write,
                  req.offset,
                  req.len,
                  req.tag);
  }

  /* Read all pending data beats from the widget */
  while (read(mmio_addrs.bdev_data_valid)) {
    /* Take a data chunk from the FPGA and put it in SW processing queues */
    struct blkdev_data data;
    data.data = (((uint64_t)read(mmio_addrs.bdev_data_data_upper)) << 32) |
                (read(mmio_addrs.bdev_data_data_lower) & 0xFFFFFFFF);
    data.tag = read(mmio_addrs.bdev_data_tag);
    write(mmio_addrs.bdev_data_ready, true);
    req_data.push(data);
    blkdev_printf("[disk] got data. data %llx, tag %x\n", data.data, data.tag);
  }
}

/* This dumps as much read_response and write_ack data onto the widget as
 * possible In the event the widget buffers fill up; set resp_data_pending,
 * indicating that we must try again on the next tick() invocation */
void blockdev_t::send() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (!initialized) throw std::runtime_error("blockdev not initialized");
  send_impl();
}

void blockdev_t::send_impl() {
  /* Return as many write acknowledgements as the blockdev widget can accept */
  while (!write_acks.empty() && read(mmio_addrs.bdev_wack_ready)) {
    uint32_t tag = write_acks.front();
    write(mmio_addrs.bdev_wack_tag, tag);
    write(mmio_addrs.bdev_wack_valid, true);
    blkdev_printf("[disk] sending W ack. tag %x\n", tag);
    write_acks.pop();
  }

  /* Send as much read reponse data as as the blockdev widget will accept */
  while (!read_responses.empty() && read(mmio_addrs.bdev_rresp_ready)) {
    struct blkdev_data resp;
    resp = read_responses.front();
    write(mmio_addrs.bdev_rresp_data_upper, (resp.data >> 32) & 0xFFFFFFFF);
    write(mmio_addrs.bdev_rresp_data_lower, resp.data & 0xFFFFFFFF);
    write(mmio_addrs.bdev_rresp_tag, resp.tag);
    write(mmio_addrs.bdev_rresp_valid, true);
    blkdev_printf(
        "[disk] sending R resp. data %llx, tag %x\n", resp.data, resp.tag);
    read_responses.pop();
  }

  /* Mark if finished */
  resp_data_pending = !read_responses.empty() || !write_acks.empty();
}

bool blockdev_t::idle() {
  return !resp_data_pending && !read(mmio_addrs.bdev_reqs_pending);
}

/* This method is called to service functional requests made by the widget.
 * No target time is modelled here; the widget will stall stimulation if
 * we have not yet serviced a transaction that is scheduled to be released. */
void blockdev_t::tick() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (!initialized) throw std::runtime_error("blockdev not initialized");

  /* If there's nothing to do, early out and save a bunch of MMIO */
  if (idle()) {
    return;
  }

  /* If there's pending response data from the last invocation of tick(),
   * write that back first as it might be locking up the simulator */
  if (resp_data_pending) {
    send_impl();
  }

  /* Collect all of the requests sitting in the widget queues */
  recv_impl();

  /* Do software processing of request queues. (requests coming from the
   * block dev widget) */
  while (!requests.empty()) {
    struct blkdev_request &req = requests.front();
    if (req.write) {
      /* if write request, setup a write tracker */
      do_write(req);
    } else {
      /* if read request, perform read from file and put data into
       * read_responses queue. */
      do_read(req);
    }
    requests.pop();
  }

  /* Do software processing of write data queues. (data coming from the
   * block dev widget).
   *
   * If there is data in req_data (from the FPGA) and a tracker has been
   * properly setup for this write, then call handle_data for this beat
   * of the write. */
  while (!req_data.empty() && can_accept(req_data.front())) {
    handle_data(req_data.front());
    req_data.pop();
  }

  /* Write state back to block device widget */
  send_impl();
}

void blockdev_t::require_checkpointable() const {
  checkpoint_state.require_idle();
  if (filename || logfile)
    throw std::runtime_error("blockdev external disk/log checkpoint unsupported");
  if (bool(_file) != !memory_disk.empty() ||
      memory_disk.size() != uint64_t(_nsectors) * SECTOR_SIZE ||
      write_trackers.size() != _ntags)
    throw std::runtime_error("blockdev backing/tracker ownership mismatch");
  if (_file && (ferror(_file) || feof(_file)))
    throw std::runtime_error("blockdev failed/EOF backing stream unsupported");
}

widget_checkpoint_config_t blockdev_t::checkpoint_config() const {
  widget_checkpoint_config_t c(8, {_ntags, _nsectors, latency_bits,
                                  read_latency, write_latency, SECTOR_SIZE,
                                  MAX_REQ_LEN, memory_disk.size()});
  // List fields explicitly: object layout/padding is never a wire format.
#define BDEV_ADDRESS(field) c.word(mmio_addrs.field)
  BDEV_ADDRESS(read_latency); BDEV_ADDRESS(write_latency);
  BDEV_ADDRESS(bdev_nsectors); BDEV_ADDRESS(bdev_max_req_len);
  BDEV_ADDRESS(bdev_req_valid); BDEV_ADDRESS(bdev_req_write);
  BDEV_ADDRESS(bdev_req_offset); BDEV_ADDRESS(bdev_req_len);
  BDEV_ADDRESS(bdev_req_tag); BDEV_ADDRESS(bdev_req_ready);
  BDEV_ADDRESS(bdev_data_valid); BDEV_ADDRESS(bdev_data_data_upper);
  BDEV_ADDRESS(bdev_data_data_lower); BDEV_ADDRESS(bdev_data_tag);
  BDEV_ADDRESS(bdev_data_ready); BDEV_ADDRESS(bdev_rresp_data_upper);
  BDEV_ADDRESS(bdev_rresp_data_lower); BDEV_ADDRESS(bdev_rresp_tag);
  BDEV_ADDRESS(bdev_rresp_valid); BDEV_ADDRESS(bdev_rresp_ready);
  BDEV_ADDRESS(bdev_wack_tag); BDEV_ADDRESS(bdev_wack_valid);
  BDEV_ADDRESS(bdev_wack_ready); BDEV_ADDRESS(bdev_reqs_pending);
  BDEV_ADDRESS(bdev_wack_stalled); BDEV_ADDRESS(bdev_rresp_stalled);
#undef BDEV_ADDRESS
  return c;
}

std::vector<uint8_t> blockdev_t::save_checkpoint() const {
  require_checkpointable();
  // Flush the fmemopen write buffer into its owned bytes without seeking or
  // advancing target time. No restore payload is accepted during a host call.
  if (_file && fflush(_file))
    throw std::runtime_error("blockdev checkpoint backing flush failed");
  const auto position = _file ? ftello(_file) : 0;
  if (position < 0)
    throw std::runtime_error("blockdev checkpoint backing position failed");
  auto c = checkpoint_config();
  c.word(initialized); c.word(resp_data_pending); c.word(position);
  auto reqs = requests;
  c.word(reqs.size());
  while (!reqs.empty()) {
    const auto &r = reqs.front();
    c.word(r.write); c.word(r.offset); c.word(r.len); c.word(r.tag);
    reqs.pop();
  }
  auto beats = [&](std::queue<blkdev_data> q) {
    c.word(q.size());
    while (!q.empty()) { c.word(q.front().data); c.word(q.front().tag); q.pop(); }
  };
  beats(req_data); beats(read_responses);
  auto acks = write_acks;
  c.word(acks.size());
  while (!acks.empty()) { c.word(acks.front()); acks.pop(); }
  // Retain even stale tracker words: the independent owner readback is full,
  // rather than assuming that currently inactive storage is irrelevant.
  for (const auto &t : write_trackers) {
    c.word(t.offset); c.word(t.count); c.word(t.size);
    for (auto word : t.data) c.word(word);
  }
  c.bytes.insert(c.bytes.end(), memory_disk.begin(), memory_disk.end());
  (void)decode_checkpoint(c.bytes);
  return std::move(c.bytes);
}

blockdev_t::decoded_checkpoint_t
blockdev_t::decode_checkpoint(const std::vector<uint8_t> &payload) const {
  require_checkpointable();
  const auto config = checkpoint_config();
  if (payload.size() < config.bytes.size() ||
      !std::equal(config.bytes.begin(), config.bytes.end(), payload.begin()))
    throw std::runtime_error("blockdev checkpoint configuration mismatch");
  size_t offset = config.bytes.size();
  auto word = [&]() {
    if (payload.size() - offset < 8)
      throw std::runtime_error("blockdev truncated checkpoint");
    uint64_t v = 0;
    for (unsigned i = 0; i < 8; ++i) v |= uint64_t(payload[offset++]) << (8 * i);
    return v;
  };
  auto boolean = [&]() {
    const auto v = word();
    if (v > 1) throw std::runtime_error("blockdev invalid boolean");
    return bool(v);
  };
  auto count = [&](size_t row_bytes) {
    const auto n = word();
    if (n > (payload.size() - offset) / row_bytes)
      throw std::runtime_error("blockdev invalid queue length");
    return n;
  };
  auto tag = [&]() {
    const auto t = word();
    if (t >= _ntags) throw std::runtime_error("blockdev invalid tag");
    return uint32_t(t);
  };
  decoded_checkpoint_t d;
  d.initialized = boolean(); d.resp_data_pending = boolean(); d.position = word();
  if (d.position > memory_disk.size())
    throw std::runtime_error("blockdev invalid backing position");
  auto n = count(32);
  for (uint64_t i = 0; i < n; ++i) {
    const bool write = boolean();
    const auto start = word(), len = word();
    if (len == 0 || len > MAX_REQ_LEN || start > _nsectors || len > _nsectors - start)
      throw std::runtime_error("blockdev invalid request range");
    d.requests.push({write, uint32_t(start), uint32_t(len), tag()});
  }
  auto beats = [&](std::queue<blkdev_data> &q) {
    const auto n = count(16);
    for (uint64_t i = 0; i < n; ++i) { const auto data = word(); q.push({data, tag()}); }
  };
  beats(d.req_data); beats(d.read_responses);
  n = count(8);
  for (uint64_t i = 0; i < n; ++i) d.write_acks.push(tag());
  // Size-check before allocating tracker arrays, including their full buffers.
  if (_ntags > (payload.size() - offset) / (8 * (3 + MAX_REQ_LEN * SECTOR_BEATS)))
    throw std::runtime_error("blockdev truncated trackers");
  d.trackers.resize(_ntags);
  for (auto &t : d.trackers) {
    t.offset = word(); t.count = word(); t.size = word();
    if ((t.size == 0 && (t.offset || t.count)) ||
        (t.size && (t.size > MAX_REQ_LEN * SECTOR_BEATS || t.size % SECTOR_BEATS ||
                    t.count >= t.size || t.offset % SECTOR_SIZE ||
                    t.offset > memory_disk.size() || t.size * 8 > memory_disk.size() - t.offset)))
      throw std::runtime_error("blockdev invalid write tracker");
    for (auto &v : t.data) v = word();
  }
  if (payload.size() - offset != memory_disk.size())
    throw std::runtime_error("blockdev incomplete/trailing backing bytes");
  d.disk.assign(payload.begin() + offset, payload.end());
  if (d.resp_data_pending != (!d.read_responses.empty() || !d.write_acks.empty()))
    throw std::runtime_error("blockdev response-pending flag mismatch");
  if (!d.initialized && (d.resp_data_pending || d.position || !d.requests.empty() ||
      !d.req_data.empty() || std::any_of(d.trackers.begin(), d.trackers.end(), [](const auto &t) {
        return t.offset || t.count || t.size ||
               std::any_of(std::begin(t.data), std::end(t.data), [](auto v) { return v != 0; });
      }) || std::any_of(d.disk.begin(), d.disk.end(), [](auto v) { return v != 0; })))
    throw std::runtime_error("blockdev uninitialized checkpoint has active state");
  return d;
}

void blockdev_t::validate_checkpoint(const std::vector<uint8_t> &payload) const {
  (void)decode_checkpoint(payload);
}

void blockdev_t::load_checkpoint(const std::vector<uint8_t> &payload) {
  auto candidate = prepare_checkpoint_publication(payload);
  candidate->seal();
  candidate->publish();
}

// Completed-call in-memory/disconnected owner only. Preparation owns the new
// stream and every decoded byte. After publication it owns the retired stream
// and backing until destruction; closing a stream is never part of publication.
class blockdev_t::restore_t final : public prepared_checkpoint_t {
  blockdev_t &owner;
  checkpoint_publication_t::guard_t guard;
  const std::vector<uint8_t> expected;
  decoded_checkpoint_t replacement;
  // Destroy the stream BEFORE its backing vector (reverse declaration order).
  using file_ptr = std::unique_ptr<FILE, int (*)(FILE *)>;
  file_ptr file{nullptr, fclose};
public:
  restore_t(blockdev_t &owner, const std::vector<uint8_t> &payload)
      : owner(owner), guard(owner.publication), expected(owner.save_checkpoint()),
        replacement(owner.decode_checkpoint(payload)) {
    if (!replacement.disk.empty()) {
      file.reset(fmemopen(replacement.disk.data(), replacement.disk.size(), "r+"));
      if (!file || fseeko(file.get(), replacement.position, SEEK_SET))
        throw std::runtime_error("blockdev restore backing preparation failed");
    }
  }
  void seal() override {
    guard.require_unsealed(); // Lifetime/thread/generation before owner access.
    if (owner.save_checkpoint() != expected)
      throw std::runtime_error("blockdev checkpoint destination changed");
    guard.seal();
  }
  void publish() noexcept override {
    guard.publish();
    auto *retired = owner._file;
    owner._file = file.release();
    file.reset(retired); // Empty after release: no fclose or libc I/O here.
    owner.memory_disk.swap(replacement.disk);
    owner.requests.swap(replacement.requests);
    owner.req_data.swap(replacement.req_data);
    owner.read_responses.swap(replacement.read_responses);
    owner.write_acks.swap(replacement.write_acks);
    owner.write_trackers.swap(replacement.trackers);
    owner.initialized = replacement.initialized;
    owner.resp_data_pending = replacement.resp_data_pending;
  }
};

std::unique_ptr<prepared_checkpoint_t>
blockdev_t::prepare_checkpoint_publication(const std::vector<uint8_t> &payload) {
  return std::make_unique<restore_t>(*this, payload);
}
