<a href="https://lnbits.com" target="_blank" rel="noopener noreferrer">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://i.imgur.com/QE6SIrs.png">
    <img src="https://i.imgur.com/fyKPgVT.png" alt="LNbits" style="width:280px">
  </picture>
</a>

[![OpenSats Supported](https://img.shields.io/badge/OpenSats-Supported-orange?logo=bitcoin&logoColor=white)](https://opensats.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-success?logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Built for LNbits](https://img.shields.io/badge/Built%20for-LNbits-4D4DFF?logo=lightning&logoColor=white)](https://github.com/lnbits/lnbits)
[![DIY MakerBits](https://img.shields.io/badge/DIY-MakerBits-f5ab48?logo=arduino&logoColor=white)](https://t.me/makerbits)  
`Author: Ben Arc` `Author: DNI` 

# LNURLDevice (Legacy Extension)
<small>is replaced by [LNPoS](https://github.com/lnbits/lnpos_extension), [FOSSA](https://github.com/lnbits/fossa_extension), [Bitcoin Switch](https://github.com/lnbits/bitcoinswitch_extension)

**LNURLDevice** is an older LNbits extension that originally bundled several hardware-related features into a single package — including LNURL-based point-of-sale devices, switch/relay controls, and various automation functions.

For a long period, the extension was enhanced and became **hard unmaintainable**. Thats why we seperated each functionality.
Due to strong user demand and many existing setups relying on it, LNURLDevice has been made **compatible again** within LNBits >v1.3, but it will **not** receive active development or new features.

This extension remains available **solely for legacy compatibility**.

## Extension Status

* **Compatibility:** Maintained
* **Active development:** No
* **Bugfixes:** Only if strictly necessary
* **New features:** None planned
* **Recommended for new projects:** No

LNURLDevice is kept online to avoid breaking existing installations but is no longer part of the future LNbits roadmap.

## Background: Split in LNBits v1.0

Starting from **LNBits v1.0**, LNURLDevice was split into three dedicated extensions for better **maintainability**, clearer scopes, and improved long-term development.

### New Extensions

* **LNPoS** – Modern successor for the LNPoS device
  → [https://extensions.lnbits.com/lnpos](https://extensions.lnbits.com/lnpos)

* **BitcoinSwitch** – Switch/relay and automation controls
  → [https://github.com/lnbits/bitcoinswitch_extension](https://github.com/lnbits/bitcoinswitch_extension)

* **FOSSA** – Advanced Bitcoin ATM
  → [https://github.com/lnbits/fossa_extension](https://github.com/lnbits/fossa_extension)

All new setups should use these extensions instead of LNURLDevice.

## Using LNURLDevice (Legacy)

LNURLDevice still works and provides the legacy functionality required by older devices, including:

* early LNPoS hardware
* old BitcoinSwitch flashes
* historic DIY projects
* environments that cannot yet migrate

For new deployments or modern hardware, LNURLDevice is **not recommended**.

## Migration to LNPoS / BitcoinSwitch / FOSSA

> [!IMPORTANT]
> If you want to upgrade an existing LNURLDevice setup, a **manual migration** is required.
#### 1) Install the new extensions

Choose the appropriate one(s): LNPoS, BitcoinSwitch, FOSSA.

#### 2) Create new devices within the corresponding extension

Each device must be recreated inside its proper replacement extension.

#### 3) Re-flash the hardware

Flash the firmware corresponding to the new extension you are moving to.

#### 4) Reconfigure the device

Set up WiFi, wallet, API endpoints, and device-specific settings again.

Once completed, your hardware runs fully under the new extension.

> [!IMPORTANT]
> LNPoS & BitcoinSwitch working with LNURLDevice while FOSSA is not compatible!
# Repositories & Hardware Installers

| Project                   | Repository Link                                                      | Hardware Installer                |
|--------------------------|-----------------------------------------------------------------------|-----------------------------------|
| **LNPoS (new)**          | https://extensions.lnbits.com/lnpos                                   | https://lnpos.lnbits.com          |
| **BitcoinSwitch (new)**  | https://github.com/lnbits/bitcoinswitch_extension                     | https://bitcoinswitch.lnbits.com  |
| **FOSSA (new)**          | https://github.com/lnbits/fossa_extension                             | https://fossa.lnbits.com          |
| **LNURLDevice (legacy)** | https://github.com/lnbits/lnurldevice                                 | *tba*                             |

> **Note:**  
> LNURLDevice is not actively supported. Some of the hardware installers above *may* still work for flashing,  
> but this must be tested individually.
# Note

LNURLDevice will remain available for compatibility but will **not** receive further updates.
For stable and future-proof setups, please use the three new extensions introduced with LNBits v1.0. 

---

## Powered by LNbits

LNbits empowers developers and merchants with modular, open-source tools for building Bitcoin-based systems — fast, free, and extendable.

[![Visit LNbits Shop](https://img.shields.io/badge/Visit-LNbits%20Shop-7C3AED?logo=shopping-cart&logoColor=white&labelColor=5B21B6)](https://shop.lnbits.com/)
[![Try myLNbits SaaS](https://img.shields.io/badge/Try-myLNbits%20SaaS-2563EB?logo=lightning&logoColor=white&labelColor=1E40AF)](https://my.lnbits.com/login)
[![Read LNbits News](https://img.shields.io/badge/Read-LNbits%20News-F97316?logo=rss&logoColor=white&labelColor=C2410C)](https://news.lnbits.com/)
[![Explore LNbits Extensions](https://img.shields.io/badge/Explore-LNbits%20Extensions-10B981?logo=puzzle-piece&logoColor=white&labelColor=065F46)](https://extensions.lnbits.com/)
[![DIY MakerBits](https://img.shields.io/badge/DIY-MakerBits-f5ab48?logo=arduino&logoColor=white)](https://t.me/makerbits)
