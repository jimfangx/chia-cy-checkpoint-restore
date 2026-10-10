// Native public Level-1 container consumer for a compiled, audited profile.
// No VPI/native mutations or file publication occur here. The returned image
// still requires aggregate all-owner prevalidation, readback and bootstrap.
#ifndef FS_DURABLE_RESTORE_H
#define FS_DURABLE_RESTORE_H
#include <string>
#include <stdexcept>
std::string read_durable_restore(const std::string &filename);
// The complete immutable image is checked against this executable's compiled
// inventory. Validation does not load owners or publish output.
std::string validate_durable_restore(std::string bytes);
// Encode a complete canonical FSAGG1 settled-cut snapshot. This does not itself
// establish a cut: the caller must collect every owner while clocks are held.
std::string encode_durable_capture(const std::string &snapshot);
// Canonical complete build identity for binding native retained history.
std::string durable_build_identity_json();
class durable_publication_error_t : public std::runtime_error {
public:
  const bool published;
  durable_publication_error_t(bool published, const std::string &message);
};
// Validate and encode before creating any output. A successful return confirms
// both file and directory sync. A post-rename error reports published=true.
void publish_durable_capture(const std::string &destination, const std::string &snapshot);
#endif
