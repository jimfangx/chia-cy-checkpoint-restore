// See LICENSE for license details.
#ifndef FIRESIM_TSI_CONTEXT_IMAGE_H
#define FIRESIM_TSI_CONTEXT_IMAGE_H
#include "tsi_context_group.h"
#include <array>

// Immutable transport for the restricted sixteen-owner host aggregate. This
// deliberately is not a checkpoint_owner_t or complete TSI/bridge admission.
// The coordinator supplies the exact build SHA-256, prepares startup metadata
// separately, and exclusively suspends provider/signal access throughout use.
// Only bytes cross threads; preparation and publication stay on the TSI creator.
class firesim_tsi_context_image_t {
public:
  using build_t = std::array<uint8_t, 32>;
  explicit firesim_tsi_context_image_t(firesim_tsi_t &tsi, build_t build)
      : tsi(tsi), build(build) {}

  std::vector<uint8_t> capture() const {
    const auto owners = firesim_tsi_context_group_t(tsi).inspect();
    const auto metadata = firesim_tsi_context_group_t(tsi).inspect_startup_metadata();
    widget_checkpoint_config_t out(37, {1, 16});
    out.bytes.insert(out.bytes.end(), build.begin(), build.end());
    blob(out, metadata);
    for (const auto &[name, payload] : owners) {
      out.text(name); blob(out, payload);
    }
    if (firesim_tsi_context_group_t(tsi).inspect() != owners ||
        firesim_tsi_context_group_t(tsi).inspect_startup_metadata() != metadata)
      throw std::runtime_error("TSI context changed during image capture");
    return std::move(out.bytes);
  }

  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    void commit() {
      // Also performs the creator check before candidate/provider access.
      if (tsi.save_startup_metadata() != decoded.metadata)
        throw std::runtime_error("TSI context destination metadata changed");
      parent.commit();
    }
  private:
    friend class firesim_tsi_context_image_t;
    struct decoded_t {
      std::vector<uint8_t> metadata;
      firesim_tsi_context_group_t::images_t owners;
    };
    prepared_t(firesim_tsi_t &tsi, const build_t &build, const std::vector<uint8_t> &image)
        : tsi(tsi), decoded(decode(tsi, build, image)),
          parent(firesim_tsi_context_group_t(tsi).prepare(decoded.owners)) {}
    firesim_tsi_t &tsi;
    decoded_t decoded;
    firesim_tsi_context_group_t::prepared_t parent;

    static decoded_t decode(firesim_tsi_t &tsi, const build_t &build,
                            const std::vector<uint8_t> &image) {
      // No candidate or image parsing on a foreign/expired creator thread.
      const auto expected_metadata = tsi.save_startup_metadata();
      const widget_checkpoint_config_t config(37, {1, 16});
      if (image.size() < config.bytes.size() + build.size() ||
          !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()) ||
          !std::equal(build.begin(), build.end(), image.begin() + config.bytes.size()))
        throw std::runtime_error("TSI context image format/build mismatch");
      size_t position = config.bytes.size() + build.size();
      auto word = [&]() {
        if (image.size() - position < 8)
          throw std::runtime_error("truncated TSI context image length");
        uint64_t value = 0;
        for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[position++]) << (8*i);
        return value;
      };
      auto read_blob = [&]() {
        const auto count = word();
        if (count > image.size() - position)
          throw std::runtime_error("truncated TSI context image record");
        std::vector<uint8_t> result(image.begin()+position, image.begin()+position+count);
        position += count;
        return result;
      };
      decoded_t result;
      result.metadata = read_blob();
      if (result.metadata != expected_metadata)
        throw std::runtime_error("TSI context image startup metadata mismatch");
      for (const char *name : {"poll", "program", "init", "host", "read", "serial",
              "loadmem-read", "loadmem-queues", "bcd", "terminal", "identity",
              "write", "syscall", "lifecycle", "outer", "wrapper"}) {
        const auto id = read_blob();
        if (std::string(id.begin(), id.end()) != name)
          throw std::runtime_error("TSI context image owner membership mismatch");
        result.owners.emplace_back(name, read_blob());
      }
      if (position != image.size())
        throw std::runtime_error("trailing TSI context image records");
      return result;
    }
  };

  prepared_t prepare(const std::vector<uint8_t> &image) const {
    return prepared_t(tsi, build, image);
  }
private:
  firesim_tsi_t &tsi;
  const build_t build;
  static void blob(widget_checkpoint_config_t &out, const std::vector<uint8_t> &bytes) {
    out.word(bytes.size()); out.bytes.insert(out.bytes.end(), bytes.begin(), bytes.end());
  }
};
#endif
