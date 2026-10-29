#include "xr/steam_link.h"
#include "xr/host_xr.h"
#include "core/process.h"
#include "common/environment.h"

namespace venture::xr {
bool steam_link_passthrough_configured() {
#ifdef _WIN32
  const auto setting = environment::getenv("VENTURE_STEAM_LINK_PASSTHROUGH");
  return setting && std::string_view(setting) == "1" && process_config().isa() == GuestIsa::a64 &&
         host_xr().runtime_name.find("SteamVR") != std::string::npos;
#else
  return false;
#endif
}
#ifndef _WIN32
struct SteamLinkSource::Impl {};
SteamLinkSource::SteamLinkSource() : impl_(std::make_unique<Impl>()) {}
SteamLinkSource::~SteamLinkSource() = default;
void SteamLinkSource::request(bool) {}
std::uint64_t SteamLinkSource::permission() const { return 0; }
#endif
} // namespace venture::xr
