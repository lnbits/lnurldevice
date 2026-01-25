<a href="https://lnbits.com" target="_blank" rel="noopener noreferrer">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://i.imgur.com/QE6SIrs.png">
    <img src="https://i.imgur.com/fyKPgVT.png" alt="LNbits" style="width:280px">
  </picture>
</a>

[![License: MIT](https://img.shields.io/badge/License-MIT-success?logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Built for LNbits](https://img.shields.io/badge/Built%20for-LNbits-4D4DFF?logo=lightning&logoColor=white)](https://github.com/lnbits/lnbits)

# LNURLDevice - [LNbits](https://lnbits.com) extension

Hardware-focused LNURL helper for offline devices. Generate LNURL endpoints that work with ESP32 and other microcontrollers for building payment-enabled hardware.

Note: This extension is deprecated. Consider using LNPoS or Bitcoin Switch for new projects.

## How it works

The extension creates LNURL-pay and LNURL-withdraw endpoints optimized for hardware devices. These endpoints can be called by microcontrollers to create invoices or process withdrawals without maintaining a constant connection.

## Features

- LNURL-pay endpoint generation
- LNURL-withdraw support
- Optimized for low-power devices
- Works offline after initial setup

## Usage

1. Enable the extension in LNbits
2. Create a new device configuration
3. Copy the LNURL endpoints to your hardware
4. Device can now create invoices and verify payments

## Powered by LNbits

[LNbits](https://lnbits.com) is a free and open-source lightning accounts system.

[![Visit LNbits Shop](https://img.shields.io/badge/Visit-LNbits%20Shop-7C3AED?logo=shopping-cart&logoColor=white&labelColor=5B21B6)](https://shop.lnbits.com/)
[![Try myLNbits SaaS](https://img.shields.io/badge/Try-myLNbits%20SaaS-2563EB?logo=lightning&logoColor=white&labelColor=1E40AF)](https://my.lnbits.com/login)
