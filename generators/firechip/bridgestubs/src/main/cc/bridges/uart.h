// See LICENSE for license details

#ifndef __UART_H
#define __UART_H

#include "bridges/serial_data.h"
#include "core/bridge_driver.h"
#include "core/widget_checkpoint.h"

#include <cstdint>
#include <memory>
#include <optional>
#include <signal.h>
#include <string>
#include <vector>

/**
 * Structure carrying the addresses of all fixed MMIO ports.
 *
 * This structure is instantiated when all bridges are populated based on
 * the target configuration.
 */
struct UARTBRIDGEMODULE_struct {
  uint64_t out_bits;
  uint64_t out_valid;
  uint64_t out_ready;
  uint64_t in_bits;
  uint64_t in_valid;
  uint64_t in_ready;
};

/**
 * Base class for callbacks handling data coming in and out a UART stream.
 */
class uart_handler : public checkpoint_owner_t {
public:
  virtual ~uart_handler() = default;

  virtual std::optional<char> get() = 0;
  virtual void put(char data) = 0;
  virtual void finish() {}
};

class uart_t final : public bridge_driver_t {
public:
  /// The identifier for the bridge type used for casts.
  static char KIND;

  /// Creates a bridge which interacts with standard streams or PTY.
  uart_t(simif_t &simif,
         const UARTBRIDGEMODULE_struct &mmio_addrs,
         int uartno,
         const std::vector<std::string> &args);

  ~uart_t() override;

  void tick() override;
  void finish() override;

  // Completed-call ownership requires an explicitly bound input/output
  // handler. Live stdin, signal input, PTYs and ordinary file descriptors
  // remain unsupported; generated UART/MMIO state has separate owners.
  std::string checkpoint_schema() const override { return "firesim.widget.uart.v1"; }
  std::vector<uint8_t> save_checkpoint() const override;
  void validate_checkpoint(const std::vector<uint8_t> &) const override;
  void load_checkpoint(const std::vector<uint8_t> &) override;

private:
  const UARTBRIDGEMODULE_struct mmio_addrs;
  const int uartno;
  std::unique_ptr<uart_handler> handler;
  widget_checkpoint_state_t checkpoint_state;
  bool finished = false;

  serial_data_t<char> data{};

  struct decoded_checkpoint_t {
    serial_data_t<char> data;
    std::vector<uint8_t> handler;
  };
  widget_checkpoint_config_t checkpoint_config() const;
  decoded_checkpoint_t decode_checkpoint(const std::vector<uint8_t> &) const;
  void require_checkpointable() const;

  void send();
  void recv();
};

#endif // __UART_H
