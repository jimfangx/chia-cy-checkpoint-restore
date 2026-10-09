// Native public Level-1 container consumer for a compiled, audited profile.
// No VPI/native mutations or file publication occur here. The returned image
// still requires aggregate all-owner prevalidation, readback and bootstrap.
#ifndef FS_DURABLE_RESTORE_H
#define FS_DURABLE_RESTORE_H
#include <string>
std::string read_durable_restore(const std::string &filename);
#endif
