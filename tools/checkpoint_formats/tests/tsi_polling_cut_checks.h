// Actual installed-FESVR cut admission, with no simulator/CPU claim.
#pragma once
#include "fesvr/firesim_tsi.h"
#include <filesystem>
#include <fstream>
#include <iostream>

static void polling_cut_check(firesim_tsi_t &tsi, const std::filesystem::path &out,
                              const std::string &name, bool supported) {
  const std::vector<std::pair<std::string, const checkpoint_owner_t *>> owners{
    {"poll", supported ? &tsi.htif_poll_owner() : nullptr},
    {"program", &tsi.program_loader_owner()}, {"init", &tsi.init_accesses_owner()},
    {"host", &tsi.host_control_owner()}, {"read", &tsi.serial_read_owner()},
    {"serial", &tsi.serial_queue_owner()}, {"loadmem-read", &tsi.loadmem_read_owner()},
    {"loadmem-queues", &tsi.loadmem_queue_owner()}};
  firesim_tsi_t::polling_cut_t before;
  for (const auto &[id, owner] : owners)
    if (owner) before.emplace_back(id, owner->save_checkpoint());
  firesim_tsi_t::polling_cut_t images;
  std::string rejection;
  try { images = tsi.inspect_polling_cut(); }
  catch (const std::runtime_error &error) { rejection = error.what(); }
  if (supported != rejection.empty() || (supported && images != before))
    throw std::runtime_error("wrong production polling cut admission/readback");
  for (size_t i = 0, n = 0; i < owners.size(); ++i)
    if (owners[i].second && owners[i].second->save_checkpoint() != before[n++].second)
      throw std::runtime_error("polling inspection mutated a component");
  if (supported && tsi.inspect_polling_cut() != images)
    throw std::runtime_error("polling inspection is not stable");
  for (const auto &[id, bytes] : images) {
    std::ofstream file(out/(name+".audit-"+id),std::ios::binary);
    file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
    if (!file) throw std::runtime_error("cannot save audited polling component");
  }
  std::cout << "POLLING_CUT_ADMISSION cut=" << name << " supported=" << supported
            << " complete_components=" << images.size() << " inspection_services=0\n";
}

static void polling_cross_owner_checks(firesim_tsi_t &tsi) {
  const auto original = tsi.inspect_polling_cut();
  auto put = [](std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
    for (unsigned i = 0; i < 8; ++i) bytes.at(offset+i) = uint8_t(value >> (8*i));
  };
  size_t rejected = 0;
  auto check = [&](const checkpoint_owner_t &constant, std::vector<uint8_t> candidate) {
    auto &owner = const_cast<checkpoint_owner_t &>(constant);
    const auto old = owner.save_checkpoint();
    owner.load_checkpoint(candidate); // Component-valid, cross-owner-invalid.
    if (owner.save_checkpoint() != candidate) throw std::runtime_error("invalid guard setup");
    bool failed = false;
    try { tsi.inspect_polling_cut(); } catch (const std::runtime_error &) { failed = true; }
    if (!failed || owner.save_checkpoint() != candidate)
      throw std::runtime_error("incoherent production cut admitted or mutated");
    owner.load_checkpoint(old);
    if (tsi.inspect_polling_cut() != original) throw std::runtime_error("peer changed after rejected cut");
    ++rejected;
  };
  auto program = tsi.program_loader_owner().save_checkpoint();
  put(program,program.size()-8,2); check(tsi.program_loader_owner(),program);
  auto init = tsi.init_accesses_owner().save_checkpoint();
  put(init,init.size()-24,0); put(init,init.size()-16,0); check(tsi.init_accesses_owner(),init);
  auto host = tsi.host_control_owner().save_checkpoint();
  put(host,host.size()-24,2); check(tsi.host_control_owner(),host);
  host = tsi.host_control_owner().save_checkpoint();
  put(host,host.size()-8,2); check(tsi.host_control_owner(),host);
  for (auto field : {size_t(72),size_t(80)}) {
    auto reader = tsi.serial_read_owner().save_checkpoint();
    put(reader,field,field==72 ? 0x80002008 : 16); check(tsi.serial_read_owner(),reader);
  }
  auto poll = tsi.htif_poll_owner().save_checkpoint();
  put(poll,56,4); check(tsi.htif_poll_owner(),poll);
  firesim_loadmem_read_t loadread; loadread.begin(0x80000000,8);
  check(tsi.loadmem_read_owner(),loadread.save_checkpoint());
  firesim_loadmem_queues_t queues; queues.push_response(0x12345678);
  check(tsi.loadmem_queue_owner(),queues.save_checkpoint());
  std::cout << "POLLING_CROSS_OWNER_REJECTIONS count=" << rejected
            << " unchanged_peers=8 target_edges=0 context_entries=0\n";
}
