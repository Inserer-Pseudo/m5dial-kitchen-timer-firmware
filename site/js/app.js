// Minuteur M5Dial installer page: shows the version published on this site (manifest.json, written
// by tools/release/make_manifests.py) and hides the install button when it cannot be loaded.
// No external request: the manifest and the firmware parts are served by this site.

const REPO = "https://github.com/Inserer-Pseudo/m5dial-kitchen-timer-firmware";
// vX.Y.Z, or a release candidate vX.Y.Z-rc.N (shown as a "préversion").
const RELEASE_TAG = /^v\d+\.\d+\.\d+(-rc\.\d+)?$/;

function setState(state) {
  document.documentElement.dataset.manifest = state;
}

async function showVersion() {
  const fields = document.querySelectorAll("[data-version]");
  const prerelease = document.querySelector("[data-prerelease]");
  try {
    const response = await fetch("manifest.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const manifest = await response.json();
    const version = typeof manifest.version === "string" ? manifest.version : "";
    const parts = manifest.builds?.[0]?.parts;
    const tag = RELEASE_TAG.exec(version);
    if (!tag || !Array.isArray(parts) || parts.length === 0) {
      throw new Error("unexpected manifest");
    }
    fields.forEach((el) => {
      el.textContent = version;
    });
    if (prerelease) {
      prerelease.hidden = !tag[1];
    }
    const link = document.querySelector("[data-release-link]");
    if (link) {
      link.href = `${REPO}/releases/tag/${encodeURIComponent(version)}`;
    }
    setState("ok");
  } catch (err) {
    fields.forEach((el) => {
      el.textContent = "indisponible";
    });
    setState("error");
    console.warn("manifest.json:", err);
  }
}

showVersion();
